#!/usr/bin/env bash
# 只发布 / 刷新公网 Skill 静态包，不重建 Docker。
# Workbench 一行一行执行：
#   curl -fL -o /tmp/publish-skill.sh \
#     https://ghfast.top/https://raw.githubusercontent.com/SenryLee/LegalAIMS-skills/main/lawhot/deploy/publish-skill.sh
#   bash /tmp/publish-skill.sh
set -euo pipefail

INSTALL_ROOT="${LAWHOT_INSTALL_ROOT:-/opt/lawhot}"
REPO_DIR="${INSTALL_ROOT}/repo"
LAWHOT_DIR="${REPO_DIR}/lawhot"
SKILL_DIR="${INSTALL_ROOT}/lawhot-skill"
REPO_URL="${LAWHOT_REPO_URL:-https://ghfast.top/https://github.com/SenryLee/LegalAIMS-skills.git}"
REPO_BRANCH="${LAWHOT_REPO_BRANCH:-main}"

log() { echo "[lawhot-publish-skill] $*"; }

if [[ ! -d "${REPO_DIR}/.git" ]]; then
  log "ERROR: 未找到 ${REPO_DIR}，请先 one-click 部署"
  exit 1
fi

log "pull ${REPO_BRANCH}"
cd "${REPO_DIR}"
git remote set-url origin "${REPO_URL}" || true
git fetch --depth 1 origin "${REPO_BRANCH}"
git checkout -B "${REPO_BRANCH}" "FETCH_HEAD"
git reset --hard "FETCH_HEAD"
log "now at $(git rev-parse --short HEAD)"

mkdir -p "${SKILL_DIR}/references" "${SKILL_DIR}/agents"
cp "${LAWHOT_DIR}/SKILL.md" "${SKILL_DIR}/SKILL.md"
cp "${LAWHOT_DIR}/LICENSE" "${SKILL_DIR}/LICENSE"
cp "${LAWHOT_DIR}/README.md" "${SKILL_DIR}/README.md"
cp "${LAWHOT_DIR}/install.sh" "${SKILL_DIR}/install.sh"
chmod +x "${SKILL_DIR}/install.sh"
cp "${LAWHOT_DIR}/manifest.sha256" "${SKILL_DIR}/manifest.sha256"
cp "${LAWHOT_DIR}/agents/openai.yaml" "${SKILL_DIR}/agents/openai.yaml"
cp "${LAWHOT_DIR}/references/api.md" "${SKILL_DIR}/references/api.md"
cp "${LAWHOT_DIR}/references/errors.md" "${SKILL_DIR}/references/errors.md"
cp "${LAWHOT_DIR}/references/sources.md" "${SKILL_DIR}/references/sources.md" 2>/dev/null || true
if [[ -f "${LAWHOT_DIR}/lawhot-skill-index.html" ]]; then
  cp "${LAWHOT_DIR}/lawhot-skill-index.html" "${SKILL_DIR}/index.html"
fi

log "published files:"
ls -la "${SKILL_DIR}"
log "验收: curl -sI https://hot.fachuiai.com/lawhot-skill/install.sh | head -5"
log "验收: curl -s https://hot.fachuiai.com/lawhot-skill/manifest.sha256"
