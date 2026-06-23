# zhimeng-skills

这是我的个人 Skill 仓库，用来沉淀可复用的 AI Agent 工作流能力。

这里的每个 Skill 都是一个独立的运行时包，目标是让 Codex、Claude Code 或兼容 Agent 在特定任务里少走弯路：读到更明确的流程、约束、脚本、模板和验收规则。

## 当前 Skill

- `goal-command-writer`：把任务收敛成可复制的 `/目标` 或 `/goal` 指令。
- `jdbc-er-html`：通过 JDBC 读取 MySQL schema，生成并校验交互式 ER HTML。
- `zhimeng-architecture-diagram`：生成高信息密度、固定版式的系统架构图 HTML。
- `zhimeng-fusion`：同题并行多 Agent 协商，用于方案、选型、架构和高风险判断。
- `zhimeng-style-capture`：把网站或截图的视觉语言沉淀为可复用的 style-kit，并在新内容中复用。

## 使用方式

进入 `skills/`，选择需要的 Skill。每个 Skill 的运行时包位于：

```text
skills/<skill-project>/skill/current/<skill-name>/
```

其中 `SKILL.md` 是入口说明，其他子目录是该 Skill 运行时需要的脚本、参考资料、模板或示例。

如果你的 Agent 支持本地 Skill 安装，可以把对应的 `skill/current/<skill-name>/` 目录复制到它的 Skill 目录中使用。
