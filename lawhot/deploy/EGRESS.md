# 出境访问约束与方案 A（洛杉矶代理）

## 结论

深圳 ECS **默认不能稳定访问境外站**。P0 英文 RSS 必须走代理，否则抓不到。

已选 **方案 A**：阿里云中台直连国内源；境外源经洛杉矶 HTTP 代理出网。

## 洛杉矶代理（已就绪）

| 项 | 值 |
|---|---|
| 主机 | `192.3.90.184`（dedirock-711993720） |
| 服务 | tinyproxy（独立端口，**不动**现有 sing-box） |
| 端口 | `13128` |
| 账号 | `lawhot` |
| 密码 | 只存在洛杉矶机：`/etc/lawhot/proxy.env`（chmod 600） |
| IP 白名单 | 仅 `127.0.0.1` + 阿里云公网 `47.119.184.45` |
| 鉴权 | BasicAuth；无密码 → 407；非白名单 IP → 403 |

在洛杉矶机查看完整连接串：

```bash
sudo cat /etc/lawhot/proxy.env
```

本机自检（在洛杉矶执行）：

```bash
source /etc/lawhot/proxy.env
curl -sS -o /dev/null -w "%{http_code}\n" \
  -x "http://${LAWHOT_PROXY_USER}:${LAWHOT_PROXY_PASS}@127.0.0.1:${LAWHOT_PROXY_PORT}" \
  https://openai.com/news/rss.xml
# 期望 200
```

## 阿里云中台如何接上

部署 LawHOT 后，编辑 `/opt/lawhot/repo/lawhot/deploy/.env`（或 `lawhot/deploy/.env`）：

```bash
# 把 YOUR_PASS 换成洛杉矶 /etc/lawhot/proxy.env 里的 LAWHOT_PROXY_PASS
LAWHOT_HTTP_PROXY=http://lawhot:YOUR_PASS@192.3.90.184:13128
LAWHOT_HTTPS_PROXY=http://lawhot:YOUR_PASS@192.3.90.184:13128
LAWHOT_NO_PROXY=localhost,127.0.0.1,.cn,cac.gov.cn,court.gov.cn,gov.cn,miit.gov.cn,npc.gov.cn,moj.gov.cn,legaldaily.com.cn
```

然后重建容器：

```bash
cd /opt/lawhot/repo/lawhot/deploy
docker compose --env-file .env up -d
# 手动触发一次抓取
token=$(grep ^LAWHOT_ADMIN_TOKEN= .env | cut -d= -f2-)
curl -sS -X POST -H "x-admin-token: $token" http://127.0.0.1:18080/admin/ingest
curl -s http://127.0.0.1:18080/healthz
# 应看到 "proxy_configured": true，且 last_ingest_stats 里 overseas_attempted > 0
```

## 中台行为

- `source_needs_proxy()`：国内 `region:[cn]` / 公众号 → **直连**
- 其它 RSS/网页 → **必须走代理**；未配置代理则跳过并打日志（避免空转超时）
- `healthz.proxy_configured` 只反映是否配置，不回显密码

## 安全提醒

1. **勿把代理密码、root 密码提交到 git / 发到公开 Issue**
2. 根密码若曾在聊天中出现，建议在洛杉矶机尽快 `passwd` 更换
3. 代理仅放行阿里云 IP；换 ECS 公网 IP 后需改 tinyproxy `Allow` 并 `systemctl restart tinyproxy`
4. 不要拿这个 tinyproxy 给浏览器日常翻墙用；LawHOT 抓取专用即可

## 运维命令（洛杉矶）

```bash
systemctl status tinyproxy
journalctl -u tinyproxy -n 50 --no-pager
# 若阿里云换 IP：
# 编辑 /etc/tinyproxy/tinyproxy.conf 的 Allow 行，然后：
systemctl restart tinyproxy
```
