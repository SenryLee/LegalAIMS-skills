# LawHOT（法锤法律 AI 资讯）

以**全球法律 AI 资讯**与 **AI 对法律行业的启迪**为核心的 Agent Skill + 内容中台 MVP。  
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

DNS 已指向服务器后，用 **root** 登录 Workbench，粘贴：

```bash
export LAWHOT_REPO_BRANCH=cursor/lawhot-sources-plan-e591
curl -fsSL https://raw.githubusercontent.com/SenryLee/LegalAIMS-skills/${LAWHOT_REPO_BRANCH}/lawhot/deploy/one-click.sh | bash
```

脚本会：安装 Docker（若无）→ 加 2G swap → 拉代码 → 启动容器（`127.0.0.1:18080`）→ 配置 nginx `hot.fachuiai.com` → 尝试 certbot → 触发首次抓取。

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
