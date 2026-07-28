<div align="center">

[中文](./README.md) · **English**

# LegalAIMS Skills

#### Agent Skills you can install with one paste

[![License](https://img.shields.io/badge/License-MIT-3B82F6?style=for-the-badge)](./LICENSE)
[![AgentSkills](https://img.shields.io/badge/AgentSkills-Standard-8B5CF6?style=for-the-badge)](https://agentskills.io)

</div>

Repo: https://github.com/SenryLee/LegalAIMS-skills

## Install

**Tell your agent:**

```text
Install this skill: https://github.com/SenryLee/LegalAIMS-skills/tree/main/<skill-name>
```

**Or bash (Claude Code):**

```bash
bash <(curl -fsSL https://cdn.jsdelivr.net/gh/SenryLee/LegalAIMS-skills@main/install-skill.sh) \
  --skill lawhot --target claude
```

**LawHOT (Legal Bulletins) preferred installer with SHA-256 checks:**

```bash
bash <(curl -fsSL https://hot.fachuiai.com/lawhot-skill/install.sh) --target claude
bash <(curl -fsSL https://hot.fachuiai.com/lawhot-skill/install.sh) --target agents
```

Agent prompt:

```text
Please review and install the Legal Bulletins (LawHOT) Skill:
https://hot.fachuiai.com/lawhot-skill/README.md

Tell me the platform, target directory, and files to install first.
Do not use sudo. Do not overwrite other skills.
Verify with: "What were the most important legal AI updates in the past 24 hours?"
```

## Skills

| Skill | What it does |
|---|---|
| [lawhot](./lawhot/) | Legal AI news via hot.fachuiai.com |
| [aihot](./aihot/) | AI HOT news via aihot.virxact.com |
| [neat-freak](./neat-freak/) | Post-task docs / memory alignment |
| [hv-analysis](./hv-analysis/) | Horizontal–vertical research PDF |
| [khazix-writer](./khazix-writer/) | Long-form writing voice |
| [storage-analyzer](./storage-analyzer/) | Disk cleanup report |

Sources registry for LawHOT: `lawhot/references/sources.v1.yaml` **v0.2** (no paywalls). Live check: https://hot.fachuiai.com/healthz

Maintained by [SenryLee](https://github.com/SenryLee). Some general skills originated from [KKKKhazix/khazix-skills](https://github.com/KKKKhazix/khazix-skills) (MIT).

[MIT License](./LICENSE)
