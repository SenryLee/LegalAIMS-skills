# Workbench 小升级（防弹出登录 / 掉线）

阿里云 2G 机器 + Workbench 网页终端有两个坑：

1. **一次粘贴太长** → 终端卡死，网页像“重新登录”
2. **`docker build` 内存打满** → 会话断开（任务其实可能还在跑）

所以：**不要一次粘贴整段多行命令**。按下面 **3 行**，一行一行回车。

---

## 正确做法（只粘 3 次，每次一行）

### 第 1 行：开 screen（掉线也不丢任务）

```bash
screen -S lawhot || (apt-get install -y screen && screen -S lawhot)
```

看到空终端、提示符回来即可。  
若提示 `screen` 没有，用：`apt-get install -y screen` 再执行 `screen -S lawhot`。

### 第 2 行：下载升级脚本（只要这一行）

```bash
curl -fL --connect-timeout 15 --max-time 90 -o /tmp/lawhot-upgrade.sh https://ghfast.top/https://raw.githubusercontent.com/SenryLee/LegalAIMS-skills/main/lawhot/deploy/upgrade-sources.sh
```

检查：

```bash
wc -c /tmp/lawhot-upgrade.sh; head -n 3 /tmp/lawhot-upgrade.sh
```

应能看到 `LawHOT 小升级` 字样，文件大约几千字节。若失败，换镜像：

```bash
curl -fL --connect-timeout 15 --max-time 90 -o /tmp/lawhot-upgrade.sh https://cdn.jsdelivr.net/gh/SenryLee/LegalAIMS-skills@main/lawhot/deploy/upgrade-sources.sh
```

### 第 3 行：执行（构建会跑几分钟，别关页面也没关系）

```bash
bash /tmp/lawhot-upgrade.sh
```

日志会打印 `pull main`、`docker compose build`、`seed sources`、`ingest`。

---

## 若网页又“弹出登录”

1. 重新进 Workbench  
2. 执行：

```bash
screen -r lawhot
```

没有会话再：

```bash
tail -100 /tmp/lawhot-deploy.log
docker ps | grep lawhot
curl -sS http://127.0.0.1:18080/healthz
```

---

## 验收（升级跑完后，再单独粘）

```bash
curl -sS http://127.0.0.1:18080/healthz
```

期望看到类似：

- `"version":"0.2.0"`
- `"sources_registry_version":"0.2"`
- `sources.ingestible` 数字较大

公网：

```bash
curl -sS https://hot.fachuiai.com/healthz
curl -sS "https://hot.fachuiai.com/api/v1/sources?ingestible=true" | head -c 300
```

---

## 常见误操作（会导致弹出登录感）

| 不要 | 原因 |
|---|---|
| 一次粘贴 20 行带 `export`/`set -e` 的长脚本 | Workbench 粘贴缓冲区/会话易炸 |
| 粘贴里带 `YOUR_PASS`、密钥、中文说明混命令 | 容易敲错或交互卡住 |
| `systemctl restart docker` | 2G 机易 OOM，表现为退出登录 |
| 不进 `screen` 直接 `docker compose build` | 掉线后不知道进度 |

---

## 脚本做了什么

`upgrade-sources.sh` 会：

1. `git fetch` **main**（经 ghfast 镜像，无需 GitHub 登录）  
2. `docker compose build && up -d`（**不**重启宿主机 docker）  
3. 调本机 `admin/seed-sources` + `admin/ingest`（用 `.env` 里已有的 `LAWHOT_ADMIN_TOKEN`）

不需要你输入任何账号密码。若提示密码，说明粘贴串了命令或当前不是 root 会话，先 `whoami` 看是否为 `root`。
