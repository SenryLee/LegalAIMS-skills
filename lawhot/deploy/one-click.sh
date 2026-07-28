#!/usr/bin/env bash
# LawHOT 一键部署（建议在阿里云 Workbench 以 root 执行）
#
# 国内若 raw.githubusercontent.com 卡住，请先下载再执行（推荐）：
#   curl -fL --connect-timeout 10 --max-time 60 \
#     -o /tmp/lawhot-one-click.sh \
#     "https://cdn.jsdelivr.net/gh/SenryLee/LegalAIMS-skills@main/lawhot/deploy/one-click.sh"
#   bash /tmp/lawhot-one-click.sh
#
set -euo pipefail

echo "[lawhot] one-click starting at $(date -Is)"

REPO_URL="${LAWHOT_REPO_URL:-https://github.com/SenryLee/LegalAIMS-skills.git}"
# 国内可改为：
#   export LAWHOT_REPO_URL="https://ghfast.top/https://github.com/SenryLee/LegalAIMS-skills.git"
REPO_BRANCH="${LAWHOT_REPO_BRANCH:-main}"
INSTALL_ROOT="${LAWHOT_INSTALL_ROOT:-/opt/lawhot}"
REPO_DIR="${INSTALL_ROOT}/repo"
LAWHOT_DIR="${REPO_DIR}/lawhot"
DOMAIN="${LAWHOT_DOMAIN:-hot.fachuiai.com}"
PUBLIC_BASE_URL="${LAWHOT_PUBLIC_BASE_URL:-https://${DOMAIN}}"

log() { echo "[lawhot] $*"; }
die() { echo "[lawhot] ERROR: $*" >&2; exit 1; }

need_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    die "请用 root 执行（阿里云 Workbench 免密登录后默认是 root）"
  fi
}

configure_docker_mirror() {
  mkdir -p /etc/docker
  # 重要：阿里云 Workbench 会话里不要随意 systemctl restart docker
  # （2G 机器上重启/构建容易 OOM，表现为“突然退出登录”）
  if [[ -f /etc/docker/daemon.json ]] && grep -q registry-mirrors /etc/docker/daemon.json; then
    log "已有 registry-mirrors，保留 /etc/docker/daemon.json（不重启 docker）"
    return
  fi
  cat > /etc/docker/daemon.json <<'JSON'
{
  "registry-mirrors": [
    "https://docker.m.daocloud.io",
    "https://docker.1ms.run"
  ]
}
JSON
  log "已写入 /etc/docker/daemon.json（本次不重启 docker；我们改用完整镜像路径拉取，无需重启）"
}

ensure_base_image() {
  # 不依赖 docker.io 匿名拉取；直接从国内可访问的完整路径拉基础镜像
  local candidates=(
    "${LAWHOT_BASE_IMAGE:-}"
    "docker.m.daocloud.io/library/python:3.12-slim"
    "docker.1ms.run/library/python:3.12-slim"
    "dockerproxy.net/library/python:3.12-slim"
  )
  local img
  for img in "${candidates[@]}"; do
    [[ -n "${img}" ]] || continue
    # 已有本地镜像则跳过 pull，减少 2G 机器压力
    if docker image inspect "${img}" >/dev/null 2>&1; then
      export LAWHOT_BASE_IMAGE="${img}"
      log "本地已有基础镜像: ${LAWHOT_BASE_IMAGE}"
      return 0
    fi
    log "尝试拉取基础镜像: ${img}"
    if docker pull "${img}"; then
      export LAWHOT_BASE_IMAGE="${img}"
      log "基础镜像就绪: ${LAWHOT_BASE_IMAGE}"
      return 0
    fi
  done
  die "无法拉取 python:3.12-slim 基础镜像。请检查网络，或手动 docker pull 后设置 LAWHOT_BASE_IMAGE"
}

install_docker() {
  if command -v docker >/dev/null 2>&1; then
    log "docker 已存在: $(docker --version)"
    configure_docker_mirror
    return
  fi
  log "安装 Docker..."
  apt-get update -y
  apt-get install -y ca-certificates curl gnupg
  # 优先用系统包，避免 download.docker.com 在国内超时
  if apt-get install -y docker.io docker-compose-v2; then
    systemctl enable --now docker
    configure_docker_mirror
    log "已通过 Ubuntu 源安装 docker.io"
    return
  fi
  install -m 0755 -d /etc/apt/keyrings
  if [[ ! -f /etc/apt/keyrings/docker.gpg ]]; then
    curl -fL --connect-timeout 10 --max-time 60 https://download.docker.com/linux/ubuntu/gpg \
      | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
  fi
  . /etc/os-release
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
  systemctl enable --now docker
  configure_docker_mirror
}

ensure_swap() {
  if swapon --show | grep -q .; then
    log "swap 已启用"
    return
  fi
  if [[ -f /swapfile ]]; then
    swapon /swapfile || true
    return
  fi
  log "创建 2G swap（2G 内存机器建议）..."
  fallocate -l 2G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
}

sync_repo() {
  mkdir -p "${INSTALL_ROOT}"
  apt-get update -y
  apt-get install -y git curl ca-certificates

  # 候选仓库地址：直连 GitHub → ghfast 镜像
  local candidates=("${REPO_URL}")
  if [[ "${REPO_URL}" == https://github.com/* ]]; then
    candidates+=("https://ghfast.top/${REPO_URL}")
    candidates+=("https://gitclone.com/${REPO_URL#https://}")
  fi

  if [[ -d "${REPO_DIR}/.git" ]]; then
    log "更新仓库 ${REPO_DIR} @ ${REPO_BRANCH}"
    local ok=0
    for url in "${candidates[@]}"; do
      log "尝试 fetch: ${url}"
      if git -C "${REPO_DIR}" fetch --depth 1 "${url}" "${REPO_BRANCH}"; then
        git -C "${REPO_DIR}" checkout "${REPO_BRANCH}" || git -C "${REPO_DIR}" checkout -B "${REPO_BRANCH}" FETCH_HEAD
        git -C "${REPO_DIR}" reset --hard FETCH_HEAD
        ok=1
        break
      fi
    done
    [[ "${ok}" -eq 1 ]] || die "git fetch 失败：国内访问 GitHub 可能不通，请设置 LAWHOT_REPO_URL 镜像后重试"
  else
    log "克隆仓库到 ${REPO_DIR}"
    rm -rf "${REPO_DIR}"
    local ok=0
    for url in "${candidates[@]}"; do
      log "尝试 clone: ${url}"
      if git clone --depth 1 --branch "${REPO_BRANCH}" "${url}" "${REPO_DIR}"; then
        ok=1
        break
      fi
      rm -rf "${REPO_DIR}"
    done
    [[ "${ok}" -eq 1 ]] || die "git clone 失败：请改用镜像后重试，例如 export LAWHOT_REPO_URL=https://ghfast.top/https://github.com/SenryLee/LegalAIMS-skills.git"
  fi
  [[ -d "${LAWHOT_DIR}" ]] || die "仓库中未找到 lawhot/ 目录"
}

upsert_env() {
  local file="$1" key="$2" value="$3"
  if grep -q "^${key}=" "${file}" 2>/dev/null; then
    # 用 | 分隔避免代理 URL 里的 /
    sed -i "s|^${key}=.*|${key}=${value}|" "${file}"
  else
    echo "${key}=${value}" >> "${file}"
  fi
}

prepare_env() {
  mkdir -p "${INSTALL_ROOT}"
  local env_file="${LAWHOT_DIR}/deploy/.env"
  if [[ ! -f "${env_file}" ]]; then
    cp "${LAWHOT_DIR}/deploy/.env.example" "${env_file}"
    local token
    token="$(openssl rand -hex 16 2>/dev/null || head -c 16 /dev/urandom | xxd -p)"
    upsert_env "${env_file}" "LAWHOT_ADMIN_TOKEN" "${token}"
    log "已生成 ${env_file}"
  else
    log "更新已有 ${env_file}（保留 ADMIN_TOKEN，覆盖代理/镜像等部署变量）"
  fi
  upsert_env "${env_file}" "LAWHOT_PUBLIC_BASE_URL" "${PUBLIC_BASE_URL}"
  if [[ -n "${LAWHOT_HTTP_PROXY:-}" ]]; then
    upsert_env "${env_file}" "LAWHOT_HTTP_PROXY" "${LAWHOT_HTTP_PROXY}"
    upsert_env "${env_file}" "LAWHOT_HTTPS_PROXY" "${LAWHOT_HTTPS_PROXY:-$LAWHOT_HTTP_PROXY}"
    log "已写入境外抓取代理到 .env"
  fi
  if [[ -n "${LAWHOT_BASE_IMAGE:-}" ]]; then
    upsert_env "${env_file}" "LAWHOT_BASE_IMAGE" "${LAWHOT_BASE_IMAGE}"
  fi
  ln -sfn "${LAWHOT_DIR}" "${INSTALL_ROOT}/lawhot-src"
  ln -sfn "${LAWHOT_DIR}/deploy" "${INSTALL_ROOT}/deploy"
}

export_skill_static() {
  # 对齐 aihot-skill：运行时包 + 人类可读 README + 校验清单
  local skill_dir="${INSTALL_ROOT}/lawhot-skill"
  mkdir -p "${skill_dir}/references" "${skill_dir}/agents"
  cp "${LAWHOT_DIR}/SKILL.md" "${skill_dir}/SKILL.md"
  cp "${LAWHOT_DIR}/LICENSE" "${skill_dir}/LICENSE"
  cp "${LAWHOT_DIR}/README.md" "${skill_dir}/README.md"
  cp "${LAWHOT_DIR}/install.sh" "${skill_dir}/install.sh"
  chmod +x "${skill_dir}/install.sh"
  cp "${LAWHOT_DIR}/manifest.sha256" "${skill_dir}/manifest.sha256"
  cp "${LAWHOT_DIR}/agents/openai.yaml" "${skill_dir}/agents/openai.yaml"
  cp "${LAWHOT_DIR}/references/api.md" "${skill_dir}/references/api.md"
  cp "${LAWHOT_DIR}/references/errors.md" "${skill_dir}/references/errors.md"
  # 信源表仅供人看，不进 Agent 运行时目录；放在 skill 站目录便于运维下载
  cp "${LAWHOT_DIR}/references/sources.md" "${skill_dir}/references/sources.md" 2>/dev/null || true
  if [[ -f "${LAWHOT_DIR}/lawhot-skill-index.html" ]]; then
    cp "${LAWHOT_DIR}/lawhot-skill-index.html" "${skill_dir}/index.html"
  fi
  log "Skill 静态包 -> ${skill_dir}（含 install.sh + manifest）"
}

start_stack() {
  ensure_base_image
  upsert_env "${LAWHOT_DIR}/deploy/.env" "LAWHOT_BASE_IMAGE" "${LAWHOT_BASE_IMAGE}"
  log "构建并启动容器（BASE_IMAGE=${LAWHOT_BASE_IMAGE}）..."
  cd "${LAWHOT_DIR}/deploy"
  # 限制构建并行，降低 2G 内存 OOM 风险
  export DOCKER_BUILDKIT=1
  export COMPOSE_DOCKER_CLI_BUILD=1
  docker compose --env-file .env build --pull=false --build-arg "BASE_IMAGE=${LAWHOT_BASE_IMAGE}" \
    || die "docker build 失败（若刚掉线，多半是内存不足；请用 screen 重跑并先确认 swap）"
  docker compose --env-file .env up -d
  for i in 1 2 3 4 5 6 7 8 9 10 11 12; do
    if curl -fsS "http://127.0.0.1:18080/healthz" >/tmp/lawhot-health.json 2>/dev/null; then
      head -c 500 /tmp/lawhot-health.json; echo
      log "容器健康检查通过"
      return
    fi
    sleep 5
  done
  docker compose -f "${LAWHOT_DIR}/deploy/docker-compose.yml" logs --tail=100 || true
  die "容器健康检查失败"
}

configure_nginx() {
  if ! command -v nginx >/dev/null 2>&1; then
    log "未检测到 nginx，跳过站点配置（容器仍在 127.0.0.1:18080）"
    return
  fi
  local conf_src="${LAWHOT_DIR}/deploy/nginx-hot.fachuiai.com.conf"
  local conf_dst="/etc/nginx/sites-available/${DOMAIN}"
  cp "${conf_src}" "${conf_dst}"
  # 修正 skill alias 路径
  sed -i "s|/opt/lawhot/lawhot-skill/|${INSTALL_ROOT}/lawhot-skill/|g" "${conf_dst}"
  ln -sfn "${conf_dst}" "/etc/nginx/sites-enabled/${DOMAIN}"
  nginx -t
  systemctl reload nginx
  log "nginx 已加载 ${DOMAIN}"

  if command -v certbot >/dev/null 2>&1; then
    log "尝试申请/更新 Let's Encrypt 证书..."
    certbot --nginx -d "${DOMAIN}" --non-interactive --agree-tos -m "admin@${DOMAIN#*.}" --redirect \
      || log "certbot 未成功（可稍后手动：certbot --nginx -d ${DOMAIN}）"
  else
    log "未安装 certbot。可执行: apt-get install -y certbot python3-certbot-nginx && certbot --nginx -d ${DOMAIN}"
  fi
}

trigger_ingest() {
  local token
  token="$(grep '^LAWHOT_ADMIN_TOKEN=' "${LAWHOT_DIR}/deploy/.env" 2>/dev/null | cut -d= -f2- || true)"
  if [[ -n "${token}" ]]; then
    log "触发首次抓取..."
    curl -fsS -X POST -H "x-admin-token: ${token}" "http://127.0.0.1:18080/admin/ingest" || true
  fi
}

print_next() {
  cat <<EOF

========================================
LawHOT 部署完成（MVP）
----------------------------------------
本机健康检查:  curl -s http://127.0.0.1:18080/healthz
公网（证书就绪后）:
  ${PUBLIC_BASE_URL}/
  ${PUBLIC_BASE_URL}/api/v1/items?mode=selected&window=7d&limit=5
  ${PUBLIC_BASE_URL}/feed.xml
  ${PUBLIC_BASE_URL}/lawhot-skill/SKILL.md
  ${PUBLIC_BASE_URL}/lawhot-skill/install.sh
  ${PUBLIC_BASE_URL}/lawhot-skill/README.md

本机装 Skill（给用户复制）:
  bash <(curl -fsSL ${PUBLIC_BASE_URL}/lawhot-skill/install.sh) --target claude

环境变量: ${INSTALL_ROOT}/deploy/.env 与 ${LAWHOT_DIR}/deploy/.env
升级重跑本脚本即可。
========================================
EOF
}

main() {
  need_root
  # 先加 swap，再做任何重活，降低 Workbench 掉线概率
  ensure_swap
  install_docker
  sync_repo
  prepare_env
  export_skill_static
  start_stack
  configure_nginx
  trigger_ingest
  print_next
}

main "$@"
