# fachuiai.com 域名与服务器部署约定

服务器实勘（2026-07-25）：

| 项 | 值 |
|---|---|
| 实例名 | 法锤智能 |
| 公网 IP | `47.119.184.45` |
| 地域 | 华南1（深圳） |
| 规格 | 2 vCPU / 2 GiB / 40 GiB / 带宽 3 Mbps |
| 系统 | Ubuntu 22.04 |
| 现状 | 已有 nginx；`fachuiai.com` → `www.fachuiai.com`（法锤 AI 法律智能体工作台） |

**结论：资讯中台不要占主域，单独开二级域名。**

## 1. 推荐域名结构（MVP 够用，别上三级域）

对齐 aihot「一个主机吃掉网页 + API + RSS + Skill 包」的做法：

| 主机名 | 用途 | 备注 |
|---|---|---|
| `fachuiai.com` / `www.fachuiai.com` | 现有「法锤 AI」工作台 | **不动** |
| **`hot.fachuiai.com`** | LawHOT 中台（网页精选 + `/api/v1/*` + `/feed/*` + Skill 安装包） | **推荐主入口** |
| `blog.fachuiai.com` 等 | 若你已有博客/其它服务 | 与资讯无关则保持原样 |

路径约定（都在 `hot.fachuiai.com` 下，无需三级域）：

```text
https://hot.fachuiai.com/                 # 精选页（可后期再做）
https://hot.fachuiai.com/api/v1/items     # Skill / 第三方调用
https://hot.fachuiai.com/feed.xml         # RSS
https://hot.fachuiai.com/agent            # Agent 接入说明
https://hot.fachuiai.com/lawhot-skill/    # Skill 安装包（对齐 aihot-skill）
```

### 为什么不建议 `api.hot.fachuiai.com` 这类三级域

- 2G 内存机器不宜拆太多服务/证书/反代
- Skill、RSS、网页同源更简单（Cookie/CORS/ETag 都省事）
- 证书用一张 `hot.fachuiai.com` 即可；真要通配再上 `*.fachuiai.com`

### 备选主机名（若你不喜欢 hot）

| 备选 | 语感 |
|---|---|
| `news.fachuiai.com` | 更直白「资讯」 |
| `lawhot.fachuiai.com` | 产品代号感强 |
| `daily.fachuiai.com` | 偏日报，稍窄 |

默认文档与后续脚本按 **`hot.fachuiai.com`** 书写；若你拍板换成 `news`，全局替换即可。

## 2. 你需要在阿里云做的 DNS（5 分钟）

在域名解析里新增：

| 类型 | 主机记录 | 记录值 | TTL |
|---|---|---|---|
| A | `hot` | `47.119.184.45` | 10 分钟 |

可选：若希望 `www.hot` 也通，再加一条 `www.hot` → 同 IP（一般不需要）。

生效后自检：

```bash
dig +short hot.fachuiai.com A
# 应返回 47.119.184.45
```

## 3. 安全组（必须）

ECS「网络与安全组」放行入方向：

| 端口 | 协议 | 说明 |
|---|---|---|
| 22 | TCP | 若你仍用 SSH/Workbench（Workbench 有时不依赖 22 公网，但保留无妨） |
| 80 | TCP | HTTP / ACME 申请证书 |
| 443 | TCP | HTTPS（Skill 与 API 正式入口） |

**不要**把 Postgres/Redis 端口对公网开放。

## 4. 这台 2C2G 的资源约束（设计时就要认）

机器上已有「法锤」站 + 你提到的 Hermes Agent，内存很紧：

- MVP：**一个** Docker Compose 栈（API + worker + DB）
- DB 优先 **Postgres 限内存**，或先 SQLite（更省，后期再迁）
- **不加**独立 Redis（可用 DB 锁 / 进程内调度）；二期再加
- LLM 只走外部 API，不在本机跑模型
- nginx **复用现机**，只加一个 `server_name hot.fachuiai.com` 反代到 `127.0.0.1:端口`
- 建议加 **1–2G swap**，避免偶发 OOM

若以后日活/抓取变重，再把中台迁到 4G 机或与主站拆机。

## 5. 我和你怎么协作（针对「Workbench 免密」）

你的登录方式是**阿里云控制台 Workbench 免密**，会话在你浏览器里，**我这边的 Cloud Agent 进不去这条通道**，也不能复用你的免密状态。

因此默认协作模式是：

```text
我：在仓库写好中台代码 + deploy/one-click.sh + nginx 样例
你：Workbench 登录后，粘贴一两行命令完成部署/升级
我：用公网 https://hot.fachuiai.com 做验收（curl API / 装 Skill 验证）
```

**不推荐**把 root 密码发给我长期代管。  
若你希望我「直接 SSH 上车」，需要额外提供其一（可选，非必须）：

1. 新增一个仅部署用的 Linux 用户 + 我提供的 SSH 公钥；或  
2. 你在本机配置好 SSH 别名后，明确授权我用该别名执行只读/部署命令  

MVP 阶段 **Workbench + 一键脚本** 就够，更安全。

## 6. 一键部署长什么样（上线时你要跑的）

脚本尚未绑定真实中台镜像（中台代码下一阶段才写）。预定形态如下——你在 Workbench 里执行：

```bash
# 示例（中台仓库就绪后会换成真实 URL）
curl -fsSL https://hot.fachuiai.com/lawhot-skill/install-server.sh | bash
# 或：
cd /opt/lawhot && ./deploy/one-click.sh
```

脚本会负责：Docker（若无则装）、拉 compose、写 `.env`、申请/挂载证书、重载 nginx、健康检查。  
**证书**：优先用已有 nginx + certbot；若你已有通配证书也可复用。

你现在可以先做、且只做这两件：

1. DNS：`hot` → `47.119.184.45`  
2. 安全组：放行 80/443  

做完告诉我，我验收解析；中台代码与 `one-click.sh` 作为下一步交付。
