#!/usr/bin/env bash
# LawHOT 小升级：拉 main + 重建容器 + seed 信源 + 触发 ingest
# 专为阿里云 2G + Workbench 设计：不重启 docker、不 apt update、不交互登录。
#
# 用法（Workbench 终端里逐条执行，不要一次粘贴十几行）：
#   1) screen -S lawhot
#   2) 下面「下载脚本」那一行
#   3) bash /tmp/lawhot-upgrade.sh
#
set -e

echo "[lawhot-upgrade] start $(date -Is)"

if [[ "${EUID}" -ne 0 ]]; then
  echo "[lawhot-upgrade] ERROR: 请用 root（Workbench 默认一般是 root）" >&2
  exit 1
fi

REPO_BRANCH="${LAWHOT_REPO_BRANCH:-main}"
# 国内镜像拉 GitHub；不要改成需要账号密码的地址
REPO_URL="${LAWHOT_REPO_URL:-https://ghfast.top/https://github.com/SenryLee/LegalAIMS-skills.git}"
INSTALL_ROOT="${LAWHOT_INSTALL_ROOT:-/opt/lawhot}"
REPO_DIR="${INSTALL_ROOT}/repo"
DEPLOY_DIR="${REPO_DIR}/lawhot/deploy"
BASE_IMAGE="${LAWHOT_BASE_IMAGE:-docker.m.daocloud.io/library/python:3.12-slim}"

log() { echo "[lawhot-upgrade] $*"; }

if [[ ! -d "${REPO_DIR}/.git" ]]; then
  log "未找到 ${REPO_DIR}，请先完成首次 one-click 部署"
  exit 1
fi

if [[ ! -d "${DEPLOY_DIR}" ]]; then
  log "未找到 ${DEPLOY_DIR}"
  exit 1
fi

log "pull ${REPO_BRANCH} from mirror"
cd "${REPO_DIR}"
git remote set-url origin "${REPO_URL}" || true
# 不用交互式 pull；depth 1 省内存
git fetch --depth 1 origin "${REPO_BRANCH}"
git checkout -B "${REPO_BRANCH}" "FETCH_HEAD"
git reset --hard "FETCH_HEAD"
log "now at $(git rev-parse --short HEAD) $(git log -1 --oneline)"

cd "${DEPLOY_DIR}"
if [[ ! -f .env ]]; then
  log "ERROR: 缺少 ${DEPLOY_DIR}/.env（首次部署时由 one-click 生成）"
  exit 1
fi

# 只导出需要的变量，避免 source .env 触发奇怪副作用
set -a
# shellcheck disable=SC1091
. ./.env
set +a

export LAWHOT_BASE_IMAGE="${BASE_IMAGE}"
log "docker compose build (base=${LAWHOT_BASE_IMAGE})"
# 不 --pull，减少对 docker hub 的请求；2G 机器上构建会慢，属正常
docker compose --env-file .env build --pull=false --build-arg "BASE_IMAGE=${LAWHOT_BASE_IMAGE}"
log "docker compose up -d"
docker compose --env-file .env up -d

# 等健康
sleep 5
if curl -fsS --connect-timeout 5 --max-time 15 http://127.0.0.1:18080/healthz >/tmp/lawhot-health.json; then
  log "local healthz ok"
  head -c 400 /tmp/lawhot-health.json || true
  echo
else
  log "WARN: local healthz not ready yet, continue"
fi

TOKEN="${LAWHOT_ADMIN_TOKEN:-}"
if [[ -z "${TOKEN}" ]]; then
  log "WARN: .env 无 LAWHOT_ADMIN_TOKEN，跳过 seed/ingest（可稍后手动 curl）"
else
  log "seed sources"
  curl -fsS -X POST -H "x-admin-token: ${TOKEN}" \
    http://127.0.0.1:18080/admin/seed-sources || log "WARN: seed-sources failed"
  echo
  log "ingest (may take several minutes)"
  curl -fsS -X POST -H "x-admin-token: ${TOKEN}" \
    http://127.0.0.1:18080/admin/ingest || log "WARN: ingest failed"
  echo
fi

log "final healthz"
curl -fsS http://127.0.0.1:18080/healthz || true
echo
log "done $(date -Is)"
log "公网验收: curl -sS https://hot.fachuiai.com/healthz"
