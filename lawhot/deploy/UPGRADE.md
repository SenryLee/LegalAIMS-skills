# 小升级（不停机感尽量短）

在阿里云 Workbench：

```bash
export LAWHOT_REPO_BRANCH=cursor/lawhot-sources-plan-e591
export LAWHOT_REPO_URL="https://ghfast.top/https://github.com/SenryLee/LegalAIMS-skills.git"

cd /opt/lawhot/repo
git remote set-url origin "$LAWHOT_REPO_URL" || true
git fetch --depth 1 origin "$LAWHOT_REPO_BRANCH"
git checkout -B "$LAWHOT_REPO_BRANCH" FETCH_HEAD
git reset --hard FETCH_HEAD

# 同步 Skill 静态（含 index）
bash /opt/lawhot/repo/lawhot/deploy/one-click.sh
```

若只想快速重建容器、不动整机脚本：

```bash
cd /opt/lawhot/repo/lawhot/deploy
source .env
export LAWHOT_BASE_IMAGE="${LAWHOT_BASE_IMAGE:-docker.m.daocloud.io/library/python:3.12-slim}"
docker compose --env-file .env build --pull=false --build-arg "BASE_IMAGE=${LAWHOT_BASE_IMAGE}"
docker compose --env-file .env up -d
curl -sI https://hot.fachuiai.com/ | head -5
curl -s https://hot.fachuiai.com/healthz
```

## 本版新增能力

1. **纸质读本 UI**：首页像一本打开的书；顶部有分类卡片可筛选。
2. **英文译中**：展示中文标题/摘要，保留「原文标题」与「原文链接」。
   - 优先用 `OPENAI_API_KEY`（可用 DeepSeek：`OPENAI_BASE_URL=https://api.deepseek.com`）。
   - 未配置 Key 时走 Google 翻译回退（境外需已配 `LAWHOT_HTTP_PROXY`）。
3. **中文信源加强**：法治网、法院网、最高法、网信网、正义网、安全内参、澎湃科技、36氪等列表抓取。
4. **精选权重**：法律科技 / 融资实务 / 诉讼↑；联邦公报等监管噪声↓，首页监管最多露出 3 条。

### 建议在 `.env` 中补翻译（可选但更稳）

```bash
# DeepSeek 示例（国内可直连，不必走代理）
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-chat
```

改完 `.env` 后：

```bash
cd /opt/lawhot/repo/lawhot/deploy
docker compose --env-file .env up -d
# 手动触发一轮抓取+翻译（把 token 换成你的 LAWHOT_ADMIN_TOKEN）
curl -s -X POST -H "x-admin-token: $LAWHOT_ADMIN_TOKEN" https://hot.fachuiai.com/admin/ingest
```

浏览器打开 https://hot.fachuiai.com/ 应看到纸质读本首页、顶部分类卡片，英文条目为中文标题并带原文链接。
