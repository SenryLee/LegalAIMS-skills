# 小升级（不停机感尽量短）

在阿里云 Workbench（`hot.fachuiai.com` → `47.119.184.45`）：

```bash
export LAWHOT_REPO_BRANCH=main
export LAWHOT_REPO_URL="https://ghfast.top/https://github.com/SenryLee/LegalAIMS-skills.git"

cd /opt/lawhot/repo
git remote set-url origin "$LAWHOT_REPO_URL" || true
git fetch --depth 1 origin "$LAWHOT_REPO_BRANCH"
git checkout -B "$LAWHOT_REPO_BRANCH" FETCH_HEAD
git reset --hard FETCH_HEAD
```

## 配置 DeepSeek（摘要 + 英译中，必做）

在 `lawhot/deploy/.env` 写入（**不要把 Key 提交到 git**）：

```bash
cd /opt/lawhot/repo/lawhot/deploy

# 若已有旧行则覆盖，否则追加
grep -q '^OPENAI_API_KEY=' .env \
  && sed -i 's|^OPENAI_API_KEY=.*|OPENAI_API_KEY=你的DeepSeekKey|' .env \
  || echo 'OPENAI_API_KEY=你的DeepSeekKey' >> .env

grep -q '^OPENAI_BASE_URL=' .env \
  && sed -i 's|^OPENAI_BASE_URL=.*|OPENAI_BASE_URL=https://api.deepseek.com|' .env \
  || echo 'OPENAI_BASE_URL=https://api.deepseek.com' >> .env

grep -q '^OPENAI_MODEL=' .env \
  && sed -i 's|^OPENAI_MODEL=.*|OPENAI_MODEL=deepseek-v4-flash|' .env \
  || echo 'OPENAI_MODEL=deepseek-v4-flash' >> .env
```

## 重建容器并触发 seed + 抓取 + 刊发

```bash
cd /opt/lawhot/repo/lawhot/deploy
source .env
export LAWHOT_BASE_IMAGE="${LAWHOT_BASE_IMAGE:-docker.m.daocloud.io/library/python:3.12-slim}"
docker compose --env-file .env build --pull=false --build-arg "BASE_IMAGE=${LAWHOT_BASE_IMAGE}"
docker compose --env-file .env up -d

# 仅把 sources.v1.yaml 写入 SQLite 信源表（不抓网页）
curl -sS -X POST -H "x-admin-token: ${LAWHOT_ADMIN_TOKEN}" \
  https://hot.fachuiai.com/admin/seed-sources

# 抓取 + 摘要/翻译 + 生成「今日读本」（中≤10 / 英≤5）
curl -sS -X POST -H "x-admin-token: ${LAWHOT_ADMIN_TOKEN}" \
  https://hot.fachuiai.com/admin/ingest

# 若只想先恢复首页、暂不重抓：用库内候选重编今日刊
curl -sS -X POST -H "x-admin-token: ${LAWHOT_ADMIN_TOKEN}" \
  https://hot.fachuiai.com/admin/rebuild-edition

curl -sS https://hot.fachuiai.com/healthz | python3 -m json.tool | head -40
curl -sS 'https://hot.fachuiai.com/api/v1/sources?ingestible=true' | python3 -c \
  'import sys,json; d=json.load(sys.stdin); print(d.get("counts"), "items", d.get("count"))'
```

说明：

- 启动时会自动 `seed_sources_to_db()`（注册表 v0.2 → SQLite `sources` 表）。
- 升级后若未跑 ingest，可能出现「今日读本为空」；新版本启动时会尝试重建；仍空时执行 `rebuild-edition` 或完整 `ingest`。
- 公开查看信源：`GET /api/v1/sources`（可加 `tier=P0`、`ingestible=true`）。

验收：

- `healthz.sources_registry_version` = `"0.2"`
- `healthz.sources.ingestible` ≥ 80
- 首页品牌为 **Legal Bulletins**
- 「今日读本」有中文 N / 英文 M；摘要是 2～4 句概括

若摘要仍像半截翻译，确认 `.env` 已配 DeepSeek 后执行：

```bash
curl -sS -X POST -H "x-admin-token: ${LAWHOT_ADMIN_TOKEN}" \
  https://hot.fachuiai.com/admin/reenrich
```

## 本版刊发规则

- 每日自然日固定刊：中文最多 10、英文最多 5（英文宁缺毋滥）
- 监管最多 1 条，可为 0
- 首页与 `mode=selected` API / Skill 口径一致
- 偏重法律科技媒体；政务源降权
- 信源注册表 v0.2：约 117+ YAML 条 + 内置中文列表；**不含付费墙**
- MVP 自动抓取：RSS + 网页列表（P0/P1）；公众号 / X / 付费库不进抓取
