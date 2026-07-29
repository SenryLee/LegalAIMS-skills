#!/usr/bin/env bash
# LegalAIMS-skills 通用 Skill 安装器
# 从 GitHub / jsDelivr 拉取某个 skill 目录，装到 Claude / agents 标准路径。
#
# 用法：
#   bash <(curl -fsSL https://cdn.jsdelivr.net/gh/SenryLee/LegalAIMS-skills@main/install-skill.sh) \
#     --skill lawhot --target claude
#   bash install-skill.sh --skill neat-freak --target agents
#   bash install-skill.sh --skill hv-analysis --dir ~/.claude/skills/hv-analysis
#
# lawhot 优先建议走专用安装器（含 SHA 校验）：
#   bash <(curl -fsSL https://hot.fachuiai.com/lawhot-skill/install.sh) --target claude

set -euo pipefail

SKILL_NAME=""
TARGET=""
INSTALL_DIR=""
REPO_SLUG="SenryLee/LegalAIMS-skills"
REF="${LAWHOT_REPO_BRANCH:-main}"

MIRRORS=(
  "https://cdn.jsdelivr.net/gh/${REPO_SLUG}@${REF}"
  "https://ghfast.top/https://raw.githubusercontent.com/${REPO_SLUG}/${REF}"
  "https://raw.githubusercontent.com/${REPO_SLUG}/${REF}"
)

usage() {
  cat <<'EOF'
Usage:
  install-skill.sh --skill <name> --target <claude|agents|codex|gemini|copilot|opencode|grok>
  install-skill.sh --skill <name> --dir <path>

Known skills in this repo:
  lawhot  aihot  neat-freak  hv-analysis  khazix-writer  storage-analyzer

Examples:
  bash install-skill.sh --skill lawhot --target claude
  bash install-skill.sh --skill neat-freak --target agents
EOF
}

fail() { echo "[ERR] $*" >&2; exit 1; }

expand_home_path() {
  case "$1" in
    "~") printf '%s\n' "$HOME" ;;
    \~/*) printf '%s/%s\n' "$HOME" "${1#\~/}" ;;
    *) printf '%s\n' "$1" ;;
  esac
}

hash_cmd() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256
  else
    sha256sum
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skill) SKILL_NAME="${2:-}"; shift 2 ;;
    --target) TARGET="${2:-}"; shift 2 ;;
    --dir) INSTALL_DIR="$(expand_home_path "${2:-}")"; TARGET="custom"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) fail "unknown argument: $1" ;;
  esac
done

[[ -n "$SKILL_NAME" ]] || { usage >&2; fail "--skill is required"; }
[[ "$SKILL_NAME" =~ ^[a-zA-Z0-9][a-zA-Z0-9_-]*$ ]] || fail "invalid skill name: $SKILL_NAME"

if [[ -z "$INSTALL_DIR" ]]; then
  case "${TARGET}" in
    claude) INSTALL_DIR="$HOME/.claude/skills/$SKILL_NAME" ;;
    agents|codex|gemini|copilot|opencode|grok) INSTALL_DIR="$HOME/.agents/skills/$SKILL_NAME" ;;
    "") fail "--target or --dir is required" ;;
    *) fail "unsupported target: $TARGET" ;;
  esac
fi

INSTALL_DIR="$(expand_home_path "$INSTALL_DIR")"
[[ "$(basename "$INSTALL_DIR")" == "$SKILL_NAME" ]] || {
  fail "install directory basename must match skill name ($SKILL_NAME): $INSTALL_DIR"
}

# lawhot 有专用安装器时优先提示（仍可用通用路径）
if [[ "$SKILL_NAME" == "lawhot" ]]; then
  echo "[info] lawhot 推荐专用安装器（含 SHA-256 校验）："
  echo "  bash <(curl -fsSL https://hot.fachuiai.com/lawhot-skill/install.sh) --target ${TARGET:-claude}"
  echo "[info] 继续使用通用安装器..."
fi

PARENT="$(dirname "$INSTALL_DIR")"
mkdir -p "$PARENT"
TMP="$(mktemp -d "$PARENT/.legalaims-install.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

STAGE="$TMP/skill"
mkdir -p "$STAGE"

# 先拉 SKILL.md 探测可用镜像
ACTIVE=""
for base in "${MIRRORS[@]}"; do
  if curl -fsSL --connect-timeout 10 --max-time 30 \
      "$base/$SKILL_NAME/SKILL.md" -o "$STAGE/SKILL.md" 2>/dev/null \
      && [[ -s "$STAGE/SKILL.md" ]]; then
    ACTIVE="$base"
    break
  fi
done
[[ -n "$ACTIVE" ]] || fail "cannot download $SKILL_NAME/SKILL.md from any mirror"

grep -q "^name: $SKILL_NAME\$" "$STAGE/SKILL.md" || {
  # 允许 frontmatter 里 name 与目录略有差异时仍安装，但警告
  if ! grep -q '^name:' "$STAGE/SKILL.md"; then
    fail "downloaded file is not a valid SKILL.md (missing name frontmatter)"
  fi
  echo "[warn] SKILL.md name frontmatter may not equal directory name $SKILL_NAME"
}

# 收集需要下载的相对路径：优先用 GitHub API 列目录；失败则递归常见结构
collect_paths() {
  local api_url="https://api.github.com/repos/${REPO_SLUG}/git/trees/${REF}?recursive=1"
  local list
  if list="$(curl -fsSL --connect-timeout 10 --max-time 45 "$api_url" 2>/dev/null)"; then
    printf '%s' "$list" | python3 -c "
import json,sys
data=json.load(sys.stdin)
prefix='${SKILL_NAME}/'
for t in data.get('tree',[]):
    p=t.get('path','')
    if t.get('type')=='blob' and p.startswith(prefix):
        rel=p[len(prefix):]
        # 跳过巨大/无关
        if rel.startswith('server/') or rel.startswith('deploy/') or rel.startswith('evals/'):
            continue
        if rel.endswith(('.pyc','.DS_Store')):
            continue
        print(rel)
" 2>/dev/null && return 0
  fi
  return 1
}

PATHS_FILE="$TMP/paths.txt"
if collect_paths >"$PATHS_FILE" && [[ -s "$PATHS_FILE" ]]; then
  :
else
  # 最小回退：只装 SKILL.md + 常见子目录探测
  echo "SKILL.md" >"$PATHS_FILE"
  for rel in LICENSE README.md agents/openai.yaml \
      references/api.md references/errors.md references/sync.md \
      references/content_methodology.md references/style_examples.md \
      references/schema.json references/macos.md references/windows.md \
      references/agent-paths.md references/governance.md references/sync-matrix.md references/verification.md \
      scripts/md_to_pdf.py scripts/scan.py scripts/build_report.py scripts/server.py scripts/audit-inventory.sh \
      assets/report_template.html; do
    if curl -fsSL --connect-timeout 5 --max-time 20 \
        -o /dev/null -w "%{http_code}" "$ACTIVE/$SKILL_NAME/$rel" 2>/dev/null | grep -q 200; then
      echo "$rel" >>"$PATHS_FILE"
    fi
  done
fi

echo "Installing skill: $SKILL_NAME"
echo "  mirror: $ACTIVE"
echo "  path:   $INSTALL_DIR"

while IFS= read -r rel || [[ -n "$rel" ]]; do
  [[ -z "$rel" ]] && continue
  [[ "$rel" != *".."* ]] || fail "unsafe path: $rel"
  out="$STAGE/$rel"
  mkdir -p "$(dirname "$out")"
  if [[ "$rel" == "SKILL.md" && -f "$STAGE/SKILL.md" ]]; then
    continue
  fi
  curl -fsSL --connect-timeout 10 --max-time 60 \
    "$ACTIVE/$SKILL_NAME/$rel" -o "$out" || fail "download failed: $rel"
done <"$PATHS_FILE"

# 确保 SKILL.md 存在
[[ -f "$STAGE/SKILL.md" ]] || fail "SKILL.md missing after download"

# 原子替换
if [[ -e "$INSTALL_DIR" ]]; then
  BACKUP="$PARENT/.${SKILL_NAME}-previous.$$"
  mv "$INSTALL_DIR" "$BACKUP"
  if ! mv "$STAGE" "$INSTALL_DIR"; then
    mv "$BACKUP" "$INSTALL_DIR" || true
    fail "failed to activate package"
  fi
  rm -rf "$BACKUP" || true
else
  mv "$STAGE" "$INSTALL_DIR"
fi

# 可执行脚本
find "$INSTALL_DIR" -type f \( -name "*.sh" -o -name "*.py" \) -exec chmod +x {} \; 2>/dev/null || true

echo "✓ Installed $SKILL_NAME -> $INSTALL_DIR"
echo "  Next: restart Agent / new conversation, then try the skill triggers."
