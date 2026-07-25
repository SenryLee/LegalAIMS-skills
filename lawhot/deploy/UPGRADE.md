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
```

浏览器打开 https://hot.fachuiai.com/ 应看到精选列表网页，而不是一整段 JSON。
