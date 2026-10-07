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
cp "${LAWHOT_DIR}/references/quality.md" "${SKILL_DIR}/references/quality.md"
# selection-score.md 是运行包必需文件：客户端评分靠它，manifest 里有它。
# 漏拷会让安装器在 SHA-256 校验阶段直接失败（manifest 列了但文件不存在）。
cp "${LAWHOT_DIR}/references/selection-score.md" "${SKILL_DIR}/references/selection-score.md"
cp "${LAWHOT_DIR}/references/sources.md" "${SKILL_DIR}/references/sources.md" 2>/dev/null || true
if [[ -f "${LAWHOT_DIR}/lawhot-skill-index.html" ]]; then
  cp "${LAWHOT_DIR}/lawhot-skill-index.html" "${SKILL_DIR}/index.html"
fi

# 自检：manifest 列出的每个文件都必须实际存在于发布目录。
# 这个检查是必要的——cp 漏文件不会报错，但安装器会在用户机器上才失败。
log "verifying published files against manifest..."
missing=0
while read -r hash path; do
  [[ -z "${hash}" || "${hash}" == \#* ]] && continue
  if [[ ! -f "${SKILL_DIR}/${path}" ]]; then
    log "MISSING: ${path}"
    missing=1
  fi
done < "${SKILL_DIR}/manifest.sha256"
[[ "${missing}" -eq 0 ]] || { log "ERROR: 发布目录缺文件，安装器会拒装"; exit 1; }
log "manifest check passed"

log "published files:"
ls -la "${SKILL_DIR}"
log "验收: curl -sI https://hot.fachuiai.com/lawhot-skill/install.sh | head -5"
log "验收: curl -s https://hot.fachuiai.com/lawhot-skill/manifest.sha256"
