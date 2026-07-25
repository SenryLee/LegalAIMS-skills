# 完整一键部署（阿里云 Workbench）

在 **root** 会话整段粘贴执行即可（已含：jsDelivr 下脚本、Git 镜像、Docker 国内基础镜像、洛杉矶抓取代理）。

```bash
# 若上一条命令卡住：先 Ctrl+C

set -e
export LAWHOT_REPO_BRANCH=cursor/lawhot-sources-plan-e591
export LAWHOT_REPO_URL="https://ghfast.top/https://github.com/SenryLee/LegalAIMS-skills.git"
export LAWHOT_BASE_IMAGE="docker.m.daocloud.io/library/python:3.12-slim"
# 密码见洛杉矶机：sudo cat /etc/lawhot/proxy.env
export LAWHOT_HTTP_PROXY="http://lawhot:YOUR_PASS@192.3.90.184:13128"
export LAWHOT_HTTPS_PROXY="$LAWHOT_HTTP_PROXY"

curl -fL --connect-timeout 15 --max-time 90 \
  -o /tmp/lawhot-one-click.sh \
  "https://cdn.jsdelivr.net/gh/SenryLee/LegalAIMS-skills@${LAWHOT_REPO_BRANCH}/lawhot/deploy/one-click.sh"

wc -c /tmp/lawhot-one-click.sh
head -n 3 /tmp/lawhot-one-click.sh

bash /tmp/lawhot-one-click.sh
```

部署成功后验收：

```bash
curl -s http://127.0.0.1:18080/healthz
curl -s 'http://127.0.0.1:18080/api/v1/items?mode=selected&window=7d&limit=3'
curl -sI https://hot.fachuiai.com/healthz || true
```

期望 `healthz` 含 `"proxy_configured": true`，且 `stats.items` 或稍后 ingest 后大于 0。

若证书未自动签好：

```bash
apt-get install -y certbot python3-certbot-nginx
certbot --nginx -d hot.fachuiai.com
```
