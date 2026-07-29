<div align="center">

**中文** · [English](./README.en.md)

# LegalAIMS Skills

#### 法锤智能 · 可直接安装的 Agent Skills 合集

[![License](https://img.shields.io/badge/License-MIT-3B82F6?style=for-the-badge)](./LICENSE)
[![Skills](https://img.shields.io/badge/Skills-6-10B981?style=for-the-badge)](#-skills)
[![AgentSkills](https://img.shields.io/badge/AgentSkills-Standard-8B5CF6?style=for-the-badge)](https://agentskills.io)

![Claude Code](https://img.shields.io/badge/Claude_Code-Skill-D97706?style=flat-square&logo=anthropic&logoColor=white)
![Codex](https://img.shields.io/badge/Codex-Skill-10B981?style=flat-square&logo=openai&logoColor=white)
![Grok](https://img.shields.io/badge/Grok-Skill-000000?style=flat-square)

</div>

仓库：https://github.com/SenryLee/LegalAIMS-skills  

每个 Skill 都是 Agent 能直接加载的结构化指令集，遵循 [Agent Skills](https://agentskills.io) 开放标准。Claude Code、Codex、Cursor、Grok 等支持该标准的 Agent 都能装。

---

## 🚀 怎么装（复制即用）

### 方式 A · 丢给 Agent（最省事）

```text
帮我安装这个 skill：https://github.com/SenryLee/LegalAIMS-skills/tree/main/<skill-name>
```

把 `<skill-name>` 换成目录名，例如 `lawhot`、`neat-freak`。

### 方式 B · 终端一键（Bash / macOS / Linux / WSL）

**装任意 skill（通用）：**

```bash
bash <(curl -fsSL https://cdn.jsdelivr.net/gh/SenryLee/LegalAIMS-skills@main/install-skill.sh) \
  --skill lawhot --target claude
```

```bash
bash <(curl -fsSL https://cdn.jsdelivr.net/gh/SenryLee/LegalAIMS-skills@main/install-skill.sh) \
  --skill neat-freak --target agents
```

`--target` 可选：`claude` → `~/.claude/skills/<name>`；`agents` / `codex` / `grok` 等 → `~/.agents/skills/<name>`。

**LawHOT / Legal Bulletins（推荐专用安装器，带 SHA-256 校验）：**

```bash
# Claude Code
bash <(curl -fsSL https://hot.fachuiai.com/lawhot-skill/install.sh) --target claude

# Codex / Grok / 通用 agents 目录
bash <(curl -fsSL https://hot.fachuiai.com/lawhot-skill/install.sh) --target agents
```

**丢给 Agent 的完整提示词（LawHOT）：**

```text
请先审阅并安装 Legal Bulletins（LawHOT）Skill：
https://hot.fachuiai.com/lawhot-skill/README.md

先告诉我当前平台、准备写入的目录和会安装的文件；不要使用 sudo，不要覆盖其它 Skill。
安装完成后用「过去 24 小时最重要的法律 AI 动态是什么？」验证。
```

---

## 📋 Skills 目录

| 名字 | 一句话 | 复制安装 |
|---|---|---|
| ⚖️ [**lawhot**](./lawhot/) | 法律 AI 资讯 / Legal Bulletins（`hot.fachuiai.com`） | [专用 install](https://hot.fachuiai.com/lawhot-skill/install.sh) |
| 🔥 [**aihot**](./aihot/) | AI HOT 资讯（`aihot.virxact.com`） | 见目录 README |
| 🧹 [**neat-freak**](./neat-freak/) | 任务收尾：对齐文档 / CLAUDE.md / Agent 记忆 | `--skill neat-freak` |
| 🔭 [**hv-analysis**](./hv-analysis/) | 横纵分析法 · 万字 PDF 研究报告 | `--skill hv-analysis` |
| ✍️ [**khazix-writer**](./khazix-writer/) | 公众号长文写作口吻 | `--skill khazix-writer` |
| 💽 [**storage-analyzer**](./storage-analyzer/) | Mac / Windows 磁盘清理决策 | `--skill storage-analyzer` |

---

## ✨ Skills 说明

### ⚖️ lawhot · Legal Bulletins（法律 AI 资讯）

查询 [hot.fachuiai.com](https://hot.fachuiai.com) 的精选、公开动态、热点与日报。无需 API Key。

**触发示例**

```
今天法律 AI 圈有什么
最近一周 LegalTech
AI Act 相关动态
法律 AI 日报
```

**信源**：`lawhot/references/sources.v1.yaml` **v0.2**（约 110+ 源，排除付费墙）。  
线上验收：`curl -s https://hot.fachuiai.com/healthz` 应见 `"sources_registry_version":"0.2"`。

→ [安装 README](./lawhot/README.md) · [SKILL.md](./lawhot/SKILL.md) · [信源说明](./lawhot/references/sources.md)

---

### 🔥 aihot · AI HOT 资讯

原 [aihot.virxact.com](https://aihot.virxact.com) 查询 skill，可与 lawhot 互补（通用 AI vs 法律 AI）。

```bash
bash <(curl -fsSL https://aihot.virxact.com/aihot-skill/install.sh) --target claude
```

→ [aihot/README.md](./aihot/README.md)

---

### 🧹 neat-freak · 洁癖

任务做完跑 `/neat`，对齐项目文档、CLAUDE.md、Agent 记忆，审计规则是否落地。

```bash
bash <(curl -fsSL https://cdn.jsdelivr.net/gh/SenryLee/LegalAIMS-skills@main/install-skill.sh) \
  --skill neat-freak --target claude
```

→ [neat-freak/SKILL.md](./neat-freak/SKILL.md)

---

### 🔭 hv-analysis · 横纵分析法

纵向时间线 + 横向竞品，输出长篇 PDF 研究报告。

```bash
bash <(curl -fsSL https://cdn.jsdelivr.net/gh/SenryLee/LegalAIMS-skills@main/install-skill.sh) \
  --skill hv-analysis --target claude
```

→ [hv-analysis/SKILL.md](./hv-analysis/SKILL.md)

---

### ✍️ khazix-writer · 写作

固定口吻与禁忌词的公众号长文 skill。

```bash
bash <(curl -fsSL https://cdn.jsdelivr.net/gh/SenryLee/LegalAIMS-skills@main/install-skill.sh) \
  --skill khazix-writer --target claude
```

→ [khazix-writer/SKILL.md](./khazix-writer/SKILL.md)

---

### 💽 storage-analyzer · 清理垃圾

整机磁盘扫描 + 三色清理决策 HTML 报告。

```bash
bash <(curl -fsSL https://cdn.jsdelivr.net/gh/SenryLee/LegalAIMS-skills@main/install-skill.sh) \
  --skill storage-analyzer --target claude
```

→ [storage-analyzer/SKILL.md](./storage-analyzer/SKILL.md)

---

## 🔧 运维备注（LawHOT 中台）

内容中台部署在 `lawhot/server` + `lawhot/deploy`，与「装 Skill 到本机 Agent」是两件事：

| 场景 | 文档 |
|---|---|
| 首次 Workbench 部署 | [lawhot/deploy/FULL-DEPLOY.md](./lawhot/deploy/FULL-DEPLOY.md) |
| 小升级（代码 + seed 信源） | [lawhot/deploy/UPGRADE.md](./lawhot/deploy/UPGRADE.md) |
| 只刷新公网 Skill 安装包 | [lawhot/deploy/publish-skill.sh](./lawhot/deploy/publish-skill.sh) |

---

## 关于

本仓库由 [SenryLee](https://github.com/SenryLee) / 法锤智能维护。  
部分通用 skill 源自 [KKKKhazix/khazix-skills](https://github.com/KKKKhazix/khazix-skills)（MIT），已接入本仓库并改安装入口到 `SenryLee/LegalAIMS-skills`。

[MIT License](./LICENSE)
