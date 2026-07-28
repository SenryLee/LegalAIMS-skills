# Legal Bulletins（LawHOT）— Agent Skill

让支持 Agent Skills（`SKILL.md`）的工具查询 [Legal Bulletins](https://hot.fachuiai.com) 的法律 AI 精选、公开动态、热点与日报。

基础能力：匿名、只读、无需 API Key。通过 `https://hot.fachuiai.com/api/v1/*` 取数；后端信源与抓取可继续迭代，用户无需因此更新 Skill。

仓库目录名仍为 `lawhot/`；对外品牌为 **Legal Bulletins**。

## 推荐安装（粘贴给 Agent）

把下面整段发给 Cursor / Claude Code / Codex 等当前 Agent：

```text
请先审阅并安装 Legal Bulletins（LawHOT）Skill：https://hot.fachuiai.com/lawhot-skill/README.md

也可从 GitHub 按 Agent Skills 标准安装：
https://github.com/SenryLee/LegalAIMS-skills/tree/main/lawhot

先告诉我当前平台、准备写入的目录和会安装的文件；不要使用 sudo，不要覆盖其它 Skill。安装完成后告诉我是否需要重启或开启新会话，并用「过去 24 小时最重要的法律 AI 动态是什么？」验证。
```

可直接审阅：

- [SKILL.md](https://hot.fachuiai.com/lawhot-skill/SKILL.md)
- [安装包清单](https://hot.fachuiai.com/lawhot-skill/manifest.sha256)
- [install.sh](https://hot.fachuiai.com/lawhot-skill/install.sh)
- [GitHub 目录](https://github.com/SenryLee/LegalAIMS-skills/tree/main/lawhot)

用 [skills.sh](https://skills.sh) / `npx skills`：

```bash
npx skills add https://github.com/SenryLee/LegalAIMS-skills --skill lawhot
```

## 手动安装

以下 Bash 适用于 macOS、Linux 与 WSL。Windows 原生环境优先把「推荐安装」提示发给 Agent，不要把 Bash 直接粘进 PowerShell。脚本不会猜测平台，必须显式指定 `--target` 或 `--dir`。

Codex、Gemini CLI、GitHub Copilot、OpenCode、Cursor 等共享通用目录 `~/.agents/skills/lawhot`：

```bash
bash <(curl -fsSL https://hot.fachuiai.com/lawhot-skill/install.sh) --target codex
bash <(curl -fsSL https://hot.fachuiai.com/lawhot-skill/install.sh) --target gemini
bash <(curl -fsSL https://hot.fachuiai.com/lawhot-skill/install.sh) --target copilot
bash <(curl -fsSL https://hot.fachuiai.com/lawhot-skill/install.sh) --target opencode
bash <(curl -fsSL https://hot.fachuiai.com/lawhot-skill/install.sh) --target agents
```

Claude Code：

```bash
bash <(curl -fsSL https://hot.fachuiai.com/lawhot-skill/install.sh) --target claude
```

自定义目录（目录名必须是 `lawhot`）：

```bash
bash <(curl -fsSL https://hot.fachuiai.com/lawhot-skill/install.sh) \
  --dir "$HOME/path/to/skills/lawhot"
```

安装包只含运行所需文件：

```text
SKILL.md
LICENSE
agents/openai.yaml
references/api.md
references/errors.md
```

人类说明本 `README.md` **不会**进入 Agent 的 Skill 安装目录。

## 安装后验证

1. 重启 Agent 或开新会话。
2. 询问：`过去 24 小时最重要的法律 AI 动态是什么？`
3. 成功标志：Agent 只发现一份 `lawhot` Skill；回答带时间窗；标题链到 `hot.fachuiai.com` 读本页或原文。

## 更新

把下面发给当前 Agent：

```text
请更新当前已安装的 Legal Bulletins（LawHOT）Skill：https://hot.fachuiai.com/lawhot-skill/README.md

先说明将写入的目录和文件；不要 sudo、不要覆盖其它 Skill。完成后用「最近一周法律 AI 精选有哪些？」验证。
```

或重跑对应的 `install.sh --target …`。

## 免责声明

资讯聚合，非法律意见；重要引用请回原文核对。
