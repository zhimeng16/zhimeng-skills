---
name: daily-report
description: >-
  AI 日报自动生成器：从 Cursor 对话、Claude Code 对话、Codex 对话、滴答清单、Git 提交采集当天数据，
  调用 LLM 生成柳比歇夫格式日记并输出到 Obsidian 日记文件。
  Use when the user mentions 日报、日记、daily report、柳比歇夫、生成今天的日记、
  采集数据、collect data，或需要调试日报生成流程。
---

# AI 日报自动生成器

自动从 5 个数据源采集当天信息，调用 LLM 生成柳比歇夫格式日记，写入 Obsidian vault。

## 执行环境

**执行前必须设编码**（每次会话开头执行一次）：

- Windows (PowerShell): `$env:PYTHONIOENCODING='utf-8'`
- macOS/Linux (Bash/Zsh): `export PYTHONIOENCODING=utf-8`

> **Python 命令**：Windows 用 `py`，macOS/Linux 用 `python3`。下文示例统一用 `python3`，Windows 环境自行替换。

**脚本目录**：`.claude/skills/daily-report/daily-report`

**CLI 入口**（在 vault 根目录执行）：

```bash
python3 ".claude/skills/daily-report/daily-report/daily_report.py" <options>
```

## 命令速查

```bash
# 完整流程：采集 → LLM 生成 → 写入文件
python3 ".claude/skills/daily-report/daily-report/daily_report.py"

# 指定日期
python3 ".claude/skills/daily-report/daily-report/daily_report.py" --date 2026-03-15

# 仅采集数据，输出到控制台（不调 LLM，不写文件）
python3 ".claude/skills/daily-report/daily-report/daily_report.py" --collect-only

# 仅采集单个数据源（支持逗号分隔多个: cursor,claude,codex,ticktick,git）
python3 ".claude/skills/daily-report/daily-report/daily_report.py" --collect-only --source cursor
python3 ".claude/skills/daily-report/daily-report/daily_report.py" --collect-only --source claude
python3 ".claude/skills/daily-report/daily-report/daily_report.py" --collect-only --source codex
python3 ".claude/skills/daily-report/daily-report/daily_report.py" --collect-only --source ticktick
python3 ".claude/skills/daily-report/daily-report/daily_report.py" --collect-only --source git

# 试运行（调 LLM 生成但不写文件）
python3 ".claude/skills/daily-report/daily-report/daily_report.py" --dry-run

# 目标文件已存在且非空时强制重跑
python3 ".claude/skills/daily-report/daily-report/daily_report.py" --date 2026-03-15 --force
```

## 数据源

| 数据源 | 采集方式 |
|--------|----------|
| Cursor 对话 | 扫描 `.cursor/projects/*/agent-transcripts/` 下 JSONL，按文件修改时间筛选当天 |
| Claude Code 对话 | 读 `.claude/history.jsonl` 索引按 timestamp 筛选，再读 `projects/<encoded>/session.jsonl` |
| Codex 对话 | 读 `.codex/state_*.sqlite` 的 threads 索引，再解析 `sessions/` 与 `archived_sessions/` 下 rollout JSONL |
| 滴答清单 | 子进程调用 `ticktick_cli.py completed --start-date ... --end-date ...` |
| Git 提交 | `git log --since --until` 扫描 config.json `code_dirs` 配置的目录下所有仓库 |

Codex 采集以 `state_*.sqlite` 的 threads 元数据为准；仅当 SQLite 不可用或无结果时，才按日期文件名 fallback 扫描 rollout。fallback 会基于 rollout 内元数据和已知内部线程标记做 best-effort 过滤；如 Codex 存储格式变化，需用 `--collect-only --source codex` 人工核查。

## 输出

- **路径**：`output_dir` 是日记根目录；默认写入 `./40-个人/日记/00-当前年-YYYY/00-当前月-YYYY-MM/日报/YYYY-MM-DD.md`
- 文件已存在且非空 → 默认跳过，避免自动化重复生成；显式传 `--force` 才继续生成并追加
- 文件不存在 → 创建

## 输出格式（柳比歇夫日记）

文件最上方先输出一行工时填报备注：

```
工时填报：……
```

要求：

- 只写当天的工作、公司项目、项目开发、团队协作相关内容
- 判断是否属于工作项目时，优先参考用户近期安排、近期计划、滴答清单和当日对话中明确出现的工作项目
- 一句话
- 不超过 255 个中文字符
- 工时填报下面空一行，再输出原有柳比歇夫日记

每条事项格式：

```
时间：xx:xx - xx:xx / 时间无法确认
事项：……
耗时：……
产出：……
```

条目间空一行。不输出标题，直接从第一条事项开始。

**严格要求**：

- 只记录时间流水账，不写复盘、不加感受、不虚构时间和产出
- 滴答清单任务和 Cursor/Claude/Codex 对话有明显交集时合并为一条（用滴答的时间 + 对话的细节），无交集的各自独立
- 产出只写有明确依据的（如对话内容、Git 提交可佐证），无法确认时省略该行
- 禁止把消息数、对话条数、会话长度写成产出；能从主题明确推导具体结果就写结果，推导不出就省略产出行
- 相关的对话可合并为一条事项（如同一项目的多次对话）
- 不要使用表格、不要写"时间分类汇总"或"今日复盘"
- 如果当天只有很少事项，也只输出核心事项，不为凑内容而扩写

## Agent 操作指引

### 场景 1：用户说"生成今天的日记"

1. 设编码 `PYTHONIOENCODING=utf-8`
2. 执行 `python3 ".claude/skills/daily-report/daily-report/daily_report.py"`
3. 检查输出，确认写入成功
4. 如果当前 `config.json` 配置的 LLM 生成不可用，回退到 `python3 ".claude/skills/daily-report/daily-report/daily_report.py" --collect-only` 获取原始数据，再手动按柳比歇夫格式整理写入

### 场景 2：用户说"生成某天的日记"

同场景 1，加 `--date YYYY-MM-DD` 参数。

### 场景 3：调试 / 排查问题

- 用 `--collect-only --source <name>` 隔离单个数据源
- 用 `--dry-run` 验证 LLM 生成但不写文件
- 滴答清单 401 错误时先执行 `python3 ".claude/skills/ticktick/ticktick_cli/ticktick_cli.py" refresh-token`

### 场景 4：LLM 不可用时手动生成

当 `python3 daily_report.py` 失败（LLM API 无响应）：

1. 执行 `python3 daily_report.py --collect-only` 获取全部采集数据
2. 根据采集数据，按柳比歇夫格式手动整理
3. 写入对应日期的日记文件（按 `40-个人/日记/CLAUDE.md` 的年/月/日报目录）
4. 如文件已存在，用 `\n\n---\n\n` 分隔后追加

## 架构与文件结构

```
.claude/skills/daily-report/daily-report/
├── daily_report.py              # 主入口：参数解析 → 采集 → LLM 生成 → 写文件
├── generator.py                 # 格式化采集数据 + 调 config.json 配置的 LLM provider
├── collectors/
│   ├── cursor_collector.py      # Cursor 对话采集（扫描 JSONL 文件修改时间）
│   ├── claude_collector.py      # Claude Code 对话采集（history.jsonl 索引）
│   ├── codex_collector.py       # Codex 对话采集（threads 索引 + rollout JSONL）
│   ├── ticktick_collector.py    # 滴答清单采集（子进程调 CLI）
│   └── git_collector.py         # Git 提交采集（git log）
├── config.json                  # 运行配置（不提交 git）
└── config.example.json          # 配置模板
```

## 配置

`config.json` 关键字段：

| 字段 | 用途 |
|------|------|
| `cursor_projects_dir` | Cursor 项目数据根目录 |
| `claude_dir` | Claude Code 数据目录（含 history.jsonl） |
| `codex_dir` | Codex 数据目录（含 state_*.sqlite、sessions、archived_sessions） |
| `ticktick_cli` | ticktick_cli.py 路径，推荐 vault 相对路径 |
| `ticktick_cache_dir` | TickTick 已完成任务缓存目录；自动化会先用顶层 TickTick CLI 预取 `completed-YYYY-MM-DD.json` |
| `code_dirs` | Git 仓库扫描根目录列表 |
| `output_dir` | Obsidian 日记根目录，脚本会自动进入年/月/日报目录 |
| `timezone_offset_hours` | 时区偏移（8 = UTC+8） |
| `llm.api_base` | LLM API 地址 |
| `llm.api_key` | LLM API 密钥 |
| `llm.model` | 模型名称 |
| `llm.max_tokens` | 最大 token 数 |
| `llm.provider` | 生成器类型，按本机 `config.json` 配置使用；`local_summary` 为本地降级生成器，不联网、不启动嵌套 Codex |
| `llm.codex_bin` | 可选字段，仅当本机明确配置 `codex_cli` provider 时使用 |
| `fail_on_generation_error` | 生成失败时是否停止写入，推荐 `true` |

### 自动化 TickTick 预取

Codex 6:00 日报自动化必须先用顶层 TickTick CLI 只读预取前一天已完成任务，再运行 `daily_report.py`：

```bash
python3 -X utf8 .claude/skills/ticktick/ticktick_cli/ticktick_cli.py daily-completed --date YYYY-MM-DD --timezone-offset-hours 8 --output-file .claude/skills/daily-report/daily-report/cache/ticktick/completed-YYYY-MM-DD.json --no-stdout
```

原因：Codex 能对顶层 TickTick CLI 命令应用已批准的联网路径；但 `daily_report.py` 内部再用 `subprocess` 启动 TickTick 时，子进程可能继承自动化沙箱网络限制并 DNS 失败。`ticktick_collector.py` 会优先读取该缓存，没有缓存才实时调用 TickTick CLI。

### 自动化默认生成器

Codex 6:00 日报自动化优先使用 `local_summary`，避免在受限自动化环境中嵌套启动 Codex CLI，也避免把本地对话和任务素材发送到未确认的外部 LLM。`local_summary` 只基于已采集到的标题、时间范围、任务和提交元数据生成保守柳比歇夫流水账；TickTick 网络失败时降级为空，不阻断日报写入。

如需更高质量自然语言整理，可以在明确授权外发目的地后，把 provider 切回可信 API provider；不建议把 `codex_cli` 作为自动化默认 provider。

## 技术约束

- **零第三方依赖**：纯 Python 标准库（json, urllib, subprocess, pathlib 等）
- LLM 生成按 `config.json` 的 provider 执行；Anthropic Messages API provider 使用 `urllib.request` 直接发 HTTP，`codex_cli` 仅作为显式配置时的可选 provider
- 滴答清单通过 `subprocess` 调用 `ticktick_cli.py`
- 文件编码统一 `utf-8`

## 添加新 Collector

1. 在 `.claude/skills/daily-report/daily-report/collectors/` 下创建 `xxx_collector.py`
2. 实现 `collect(config, target_date) -> list[dict]`
3. 在 `daily_report.py` 的 `collect_all()` 中注册调用
4. 在 `generator.py` 的 `format_collected_data()` 中添加格式化逻辑
5. 如需新配置字段，同步更新 `config.example.json` 和 `CLAUDE.md`

## 跨平台 config.json 配置

`config.json` 不提交 Git，每台机器需要单独创建。参考 `config.example.json` 模板。

### Windows 配置参考

```json
{
  "cursor_projects_dir": "~/.cursor/projects",
  "claude_dir": "~/.claude",
  "codex_dir": "~/.codex",
  "ticktick_cli": ".claude/skills/ticktick/ticktick_cli/ticktick_cli.py",
  "code_dirs": ["~/Code"],
  "output_dir": "./40-个人/日记",
  "timezone_offset_hours": 8,
  "llm": { "api_base": "...", "api_key": "...", "model": "...", "max_tokens": 8192 }
}
```

### macOS 配置参考

> **TODO（Mac 端首次初始化时填写）**：在 Mac 上打开 Claude Code，告诉 AI：
> "帮我创建 `.claude/skills/daily-report/daily-report/config.json`，参考同目录的 `config.example.json`，把路径改成我 Mac 上的实际路径。"
> AI 会自动检测 Mac 上的 `~/.cursor/projects`、`~/.claude` 等路径并填入。

```json
{
  "cursor_projects_dir": "~/.cursor/projects",
  "claude_dir": "~/.claude",
  "codex_dir": "~/.codex",
  "ticktick_cli": ".claude/skills/ticktick/ticktick_cli/ticktick_cli.py",
  "code_dirs": ["<TODO: Mac 上的代码目录，如 ~/Code>"],
  "output_dir": "./40-个人/日记",
  "timezone_offset_hours": 8,
  "llm": { "api_base": "...", "api_key": "...", "model": "...", "max_tokens": 8192 }
}
```
