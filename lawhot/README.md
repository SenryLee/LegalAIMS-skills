# Legal Bulletins（原 LawHOT / 法锤法律 AI 资讯）

以**全球法律 AI 资讯**与 **AI 对法律行业的启迪**为核心的 Agent Skill + 内容中台 MVP。  
对外品牌：**Legal Bulletins**（法律 AI 每日读本）；仓库与部署目录暂仍用 `lawhot/`。  
策略：抄 [aihot](../aihot/) 的骨架（Skill + 匿名 API + 精选/日报），换法律向信源与分类。

公网入口（部署后）：`https://hot.fachuiai.com`

## 当前进度

| 状态 | 内容 |
|---|---|
| ✅ | 信源表：[`references/sources.md`](./references/sources.md) |
| ✅ | Skill 合同：[`SKILL.md`](./SKILL.md) |
| ✅ | 中台 MVP：[`server/`](./server/)（RSS → SQLite → `/api/v1/*`） |
| ✅ | Workbench 一键部署：[`deploy/one-click.sh`](./deploy/one-click.sh) |
| ⏳ | 网页抓取 / 公众号 / LLM 精摘要（二期） |

## 在阿里云 Workbench 一键部署

DNS 已指向服务器后，用 **root** 登录 Workbench。

> 完整可复制命令见 [`deploy/FULL-DEPLOY.md`](./deploy/FULL-DEPLOY.md)（含国内 Docker 镜像 + 洛杉矶抓取代理）。

要点：
- 用 jsDelivr 下脚本，避免 GitHub raw 卡住
- 基础镜像默认 `docker.m.daocloud.io/library/python:3.12-slim`（不直连 docker.io）
- 境外 RSS 经洛杉矶 `192.3.90.184:13128` 代理

部署后自检：

```bash
curl -s http://127.0.0.1:18080/healthz
curl -s 'http://127.0.0.1:18080/api/v1/items?mode=selected&window=7d&limit=5'
curl -sI https://hot.fachuiai.com/healthz
```

环境变量：`/opt/lawhot/repo/lawhot/deploy/.env`（可填 `OPENAI_API_KEY`，MVP 不强制）。

## 本地开发（无 Docker）

```bash
cd lawhot/server
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
LAWHOT_PUBLIC_BASE_URL=http://127.0.0.1:8080 uvicorn app.main:app --port 8080
```

## 文档

- 改造路径：[`BUILD.md`](./BUILD.md)
- 域名约定：[`deploy/DNS.md`](./deploy/DNS.md)
- API：[`references/api.md`](./references/api.md)

**免责声明**：资讯聚合，非法律意见；重要引用请回原文核对。
