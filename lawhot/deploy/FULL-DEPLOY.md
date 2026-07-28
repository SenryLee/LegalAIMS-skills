# 完整部署（防 Workbench 掉线）

## 为什么会“一运行就退出登录”

在 2G 阿里云 + Workbench 上，常见原因：

1. 脚本里 **`systemctl restart docker`**（已去掉）
2. **`docker build` / `pip install` 内存打满 OOM**，整机卡死，Workbench 看起来像被踢下线

所以请用 **`screen`** 跑部署：即使网页断开，服务器上任务还在。

## 推荐：screen 后台部署（整段粘贴）

```bash
# 1) 安装 screen（若已有会很快结束）
apt-get update -y && apt-get install -y screen curl

# 2) 进入独立会话（掉线后可恢复）
screen -S lawhot

# 3) 在 screen 里设置变量并部署
set -e
export LAWHOT_REPO_BRANCH=main
export LAWHOT_REPO_URL="https://ghfast.top/https://github.com/SenryLee/LegalAIMS-skills.git"
export LAWHOT_BASE_IMAGE="docker.m.daocloud.io/library/python:3.12-slim"
# 密码见洛杉矶：cat /etc/lawhot/proxy.env 里的 LAWHOT_PROXY_PASS
export LAWHOT_HTTP_PROXY="http://lawhot:YOUR_PASS@192.3.90.184:13128"
export LAWHOT_HTTPS_PROXY="$LAWHOT_HTTP_PROXY"

curl -fL --connect-timeout 15 --max-time 90 \
  -o /tmp/lawhot-one-click.sh \
  "https://ghfast.top/https://raw.githubusercontent.com/SenryLee/LegalAIMS-skills/${LAWHOT_REPO_BRANCH}/lawhot/deploy/one-click.sh"

grep -n "不重启 docker" /tmp/lawhot-one-click.sh || grep -n ensure_base_image /tmp/lawhot-one-click.sh

bash /tmp/lawhot-one-click.sh 2>&1 | tee /tmp/lawhot-deploy.log
```

### screen 常用操作

| 操作 | 按键/命令 |
|---|---|
| 暂时离开（任务继续跑） | `Ctrl+A` 然后按 `D` |
| 重新连上 | `screen -r lawhot` |
| 看有没有会话 | `screen -ls` |
| 看部署日志 | `tail -f /tmp/lawhot-deploy.log` |

若网页又断了：重新 Workbench 登录 → `screen -r lawhot` 或 `tail -f /tmp/lawhot-deploy.log`。

## 部署成功验收

```bash
curl -s http://127.0.0.1:18080/healthz
curl -s 'http://127.0.0.1:18080/api/v1/items?mode=selected&window=7d&limit=3'
```

期望含 `"proxy_configured": true`。

## 若仍 OOM

```bash
free -h
swapon --show
dmesg | tail -50 | grep -i -E 'kill|oom' || true
# 构建期间可先停不必要的占内存服务（慎用，确认后再停）
# systemctl stop 某服务
```
