# Legal Bulletins / LawHOT — Agent Skill

让支持 Agent Skills（`SKILL.md`）的工具，用自然语言查询 [Legal Bulletins](https://hot.fachuiai.com) 的法律 AI 精选、公开动态、热点与日报。

- 匿名、只读、**无需 API Key / MCP**
- 数据源：`https://hot.fachuiai.com/api/v1/*`
- 安装包只含运行所需 5 个文件（不含中台 server / 信源表 / 部署脚本）

## 推荐安装（复制给 Agent）

把下面整段发给 Cursor / Claude Code / Codex / Grok 等：

```text
请先审阅并安装 Legal Bulletins（LawHOT）Skill：
https://hot.fachuiai.com/lawhot-skill/README.md

先告诉我当前平台、准备写入的目录和会安装的文件；不要使用 sudo，不要覆盖其它 Skill。
安装完成后告诉我是否需要重启或开启新会话，并用「过去 24 小时最重要的法律 AI 动态是什么？」验证。
```

也可直接让 Agent 装 GitHub 目录：

```text
帮我安装这个 skill：https://github.com/SenryLee/LegalAIMS-skills/tree/main/lawhot
```

可审阅的文件：

| 文件 | 地址 |
|---|---|
| SKILL.md | https://hot.fachuiai.com/lawhot-skill/SKILL.md |
| 安装清单 | https://hot.fachuiai.com/lawhot-skill/manifest.sha256 |
| install.sh | https://hot.fachuiai.com/lawhot-skill/install.sh |
| GitHub | https://github.com/SenryLee/LegalAIMS-skills/tree/main/lawhot |

## 手动一键安装（Bash）

macOS / Linux / WSL。**必须**指定 `--target` 或 `--dir`（无参数只打印帮助）。

**Claude Code：**

```bash
bash <(curl -fsSL https://hot.fachuiai.com/lawhot-skill/install.sh) --target claude
```

**Codex / Gemini / Copilot / OpenCode / Grok（共用 `~/.agents/skills`）：**

```bash
bash <(curl -fsSL https://hot.fachuiai.com/lawhot-skill/install.sh) --target agents
```

**自定义目录：**

```bash
bash <(curl -fsSL https://hot.fachuiai.com/lawhot-skill/install.sh) \
  --dir "$HOME/.agents/skills/lawhot"
```

若公网站点暂时不可达，安装器会自动回退到 jsDelivr / ghfast 上的 GitHub 镜像。也可强制指定包地址：

```bash
export LAWHOT_SKILL_PACKAGE="https://cdn.jsdelivr.net/gh/SenryLee/LegalAIMS-skills@main/lawhot"
bash <(curl -fsSL "$LAWHOT_SKILL_PACKAGE/install.sh") --target claude
```

安装包内容（进 Agent 目录的只有这些）：

```text
SKILL.md
LICENSE
agents/openai.yaml
references/api.md
references/errors.md
```

`README.md`、`server/`、`deploy/`、`references/sources.*` **不会**写入 Skill 目录。

## 安装后验证

1. 重启 Agent 或开新会话  
2. 确认只发现一份 `lawhot`  
3. 提问：`过去 24 小时最重要的法律 AI 动态是什么？`

成功时应写明时间窗、中文摘要，标题链到 `hot.fachuiai.com`。

## 更新

本地不会自动升级。需要时再跑同一条 install 命令，或对 Agent 说：

```text
请更新当前已安装的 LawHOT Skill：https://hot.fachuiai.com/lawhot-skill/README.md
先告诉我当前 lawhot/SKILL.md 路径和是否存在重复副本，再原子替换同一目录。
```

## 能查什么

- 过去 24h / 7d 精选（`mode=selected`）与公开池（`mode=all`）
- 热点 `hot-topics`、日报 `dailies`
- 分类：`regulation` · `litigation` · `legaltech` · `practice` · `insight` · `vendor`
- 关键词 / 公司 / 法规主题

**不是法律意见**；重要引用请回原文核对。

## 运维（中台部署，不是装 Skill）

内容中台部署、信源升级见：

- [`deploy/FULL-DEPLOY.md`](./deploy/FULL-DEPLOY.md) — 阿里云 Workbench 首次部署  
- [`deploy/UPGRADE.md`](./deploy/UPGRADE.md) — 小升级（拉代码 + seed 信源）  
- [`references/sources.md`](./references/sources.md) — 信源名单 v0.2  
- [`BUILD.md`](./BUILD.md) — 架构说明  

站点健康：https://hot.fachuiai.com/healthz
