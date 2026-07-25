#!/usr/bin/env bash
# LawHOT 一键部署（建议在阿里云 Workbench 以 root 执行）
#
# 国内若 raw.githubusercontent.com 卡住，请先下载再执行（推荐）：
#   curl -fL --connect-timeout 10 --max-time 60 \
#     -o /tmp/lawhot-one-click.sh \
#     "https://cdn.jsdelivr.net/gh/SenryLee/LegalAIMS-skills@cursor/lawhot-sources-plan-e591/lawhot/deploy/one-click.sh"
#   bash /tmp/lawhot-one-click.sh
#
set -euo pipefail

echo "[lawhot] one-click starting at $(date -Is)"

REPO_URL="${LAWHOT_REPO_URL:-https://github.com/SenryLee/LegalAIMS-skills.git}"
# 国内可改为：
#   export LAWHOT_REPO_URL="https://ghfast.top/https://github.com/SenryLee/LegalAIMS-skills.git"
# PR 合并前请显式指定功能分支
REPO_BRANCH="${LAWHOT_REPO_BRANCH:-cursor/lawhot-sources-plan-e591}"
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
  if [[ -f /etc/docker/daemon.json ]]; then
    log "保留已有 /etc/docker/daemon.json"
    return
  fi
  # 国内拉 python 基础镜像更稳（可按你账号改成阿里云个人镜像加速器）
  cat > /etc/docker/daemon.json <<'JSON'
{
  "registry-mirrors": [
    "https://docker.1ms.run",
    "https://docker.m.daocloud.io"
  ]
}
JSON
  systemctl restart docker || true
  log "已写入 Docker registry mirrors"
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

prepare_env() {
  mkdir -p "${INSTALL_ROOT}"
  local env_file="${LAWHOT_DIR}/deploy/.env"
  if [[ ! -f "${env_file}" ]]; then
    cp "${LAWHOT_DIR}/deploy/.env.example" "${env_file}"
    local token
    token="$(openssl rand -hex 16 2>/dev/null || head -c 16 /dev/urandom | xxd -p)"
    sed -i "s/^LAWHOT_ADMIN_TOKEN=.*/LAWHOT_ADMIN_TOKEN=${token}/" "${env_file}"
    sed -i "s|^LAWHOT_PUBLIC_BASE_URL=.*|LAWHOT_PUBLIC_BASE_URL=${PUBLIC_BASE_URL}|" "${env_file}"
    log "已生成 ${env_file}（请按需填入 OPENAI_API_KEY）"
  else
    log "保留已有 ${env_file}"
  fi
  # 方便找数据与日志
  ln -sfn "${LAWHOT_DIR}" "${INSTALL_ROOT}/lawhot-src"
  ln -sfn "${LAWHOT_DIR}/deploy" "${INSTALL_ROOT}/deploy"
}

export_skill_static() {
  local skill_dir="${INSTALL_ROOT}/lawhot-skill"
  mkdir -p "${skill_dir}/references" "${skill_dir}/agents"
  cp "${LAWHOT_DIR}/SKILL.md" "${skill_dir}/SKILL.md"
  cp "${LAWHOT_DIR}/README.md" "${skill_dir}/README.md"
  cp "${LAWHOT_DIR}/agents/openai.yaml" "${skill_dir}/agents/openai.yaml"
  cp "${LAWHOT_DIR}/references/api.md" "${skill_dir}/references/api.md"
  cp "${LAWHOT_DIR}/references/errors.md" "${skill_dir}/references/errors.md"
  cp "${LAWHOT_DIR}/references/sources.md" "${skill_dir}/references/sources.md"
  log "Skill 静态文件 -> ${skill_dir}"
}

start_stack() {
  log "构建并启动容器..."
  cd "${LAWHOT_DIR}/deploy"
  docker compose --env-file .env up -d --build
  # 等待健康
  for i in 1 2 3 4 5 6 7 8 9 10; do
    if curl -fsS "http://127.0.0.1:18080/healthz" >/tmp/lawhot-health.json 2>/dev/null; then
      head -c 400 /tmp/lawhot-health.json; echo
      log "容器健康检查通过"
      return
    fi
    sleep 3
  done
  docker compose -f "${LAWHOT_DIR}/deploy/docker-compose.yml" logs --tail=80 || true
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

环境变量: ${INSTALL_ROOT}/deploy/.env 与 ${LAWHOT_DIR}/deploy/.env
升级重跑本脚本即可。
========================================
EOF
}

main() {
  need_root
  install_docker
  ensure_swap
  sync_repo
  prepare_env
  export_skill_static
  start_stack
  configure_nginx
  trigger_ingest
  print_next
}

main "$@"
