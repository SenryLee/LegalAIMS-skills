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

## 重建容器并触发刊发

```bash
cd /opt/lawhot/repo/lawhot/deploy
source .env
export LAWHOT_BASE_IMAGE="${LAWHOT_BASE_IMAGE:-docker.m.daocloud.io/library/python:3.12-slim}"
docker compose --env-file .env build --pull=false --build-arg "BASE_IMAGE=${LAWHOT_BASE_IMAGE}"
docker compose --env-file .env up -d

# 抓取 + 摘要/翻译 + 生成「今日读本」（中≤10 / 英≤5）
curl -sS -X POST -H "x-admin-token: ${LAWHOT_ADMIN_TOKEN}" https://hot.fachuiai.com/admin/ingest
curl -sS https://hot.fachuiai.com/healthz
```

验收：首页应显示「今日读本 · 日期 · 中文 N / 英文 M」；条目有可读摘要；英文条目标题为中文并保留原文链接。

## 本版刊发规则

- 每日自然日固定刊：中文最多 10、英文最多 5（英文宁缺毋滥）
- 监管最多 1 条，可为 0
- 首页与 `mode=selected` API / Skill 口径一致
- 偏重法律科技媒体（律页、智律云、Artificial Lawyer 等），政务源降权
