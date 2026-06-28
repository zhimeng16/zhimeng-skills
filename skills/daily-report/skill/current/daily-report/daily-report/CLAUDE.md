# AI 日报自动生成器 (daily-report)

自动从 Cursor 对话记录、Claude Code 对话记录、Codex 对话记录、滴答清单已完成任务、Git 提交记录采集当天信息，调用 LLM API 生成柳比歇夫格式日记，输出到 Obsidian vault。

## 运行方式

```bash
# 执行前设编码：
# Windows (PowerShell): $env:PYTHONIOENCODING='utf-8'
# macOS/Linux (Bash/Zsh): export PYTHONIOENCODING=utf-8

# 生成今天的日记（完整流程：采集 → LLM 生成 → 写入文件）
python3 daily_report.py

# 指定日期
python3 daily_report.py --date YYYY-MM-DD

# 仅采集数据，输出到控制台（不调 LLM，不写文件）
python3 daily_report.py --collect-only

# 仅采集某个数据源
python3 daily_report.py --collect-only --source cursor
python3 daily_report.py --collect-only --source claude
python3 daily_report.py --collect-only --source codex
python3 daily_report.py --collect-only --source ticktick
python3 daily_report.py --collect-only --source git

# 试运行（调 LLM 生成但不写文件）
python3 daily_report.py --dry-run
```

## 数据源


| 数据源            | 路径                                                     | 采集方式                      |
| -------------- | ------------------------------------------------------ | ------------------------- |
| Cursor 对话      | `~/.cursor/projects/*/agent-transcripts/` | 按文件修改时间筛选当天 JSONL         |
| Claude Code 对话 | `~/.claude/history.jsonl` + `projects/`   | 按 timestamp 筛选当天 session  |
| Codex 对话       | `~/.codex/state_*.sqlite` + `sessions/` / `archived_sessions/` | 按 threads 时间筛选当天 rollout |
| 滴答清单           | 优先读取 `cache/ticktick/completed-YYYY-MM-DD.json`；无缓存时调用 `ticktick_cli.py completed` | 按日期查询已完成任务                |
| Git 提交         | config.json `code_dirs` 配置的目录                         | `git log --since --until` |

Codex 采集以 `state_*.sqlite` 的 threads 元数据为准；仅当 SQLite 不可用或无结果时，才按日期文件名 fallback 扫描 rollout。fallback 会基于 rollout 内元数据和已知内部线程标记做 best-effort 过滤；如 Codex 存储格式变化，需用 `--collect-only --source codex` 人工核查。

## 输出

- 路径：`output_dir` 是日记根目录；默认写入 `./40-个人/日记/00-当前年-YYYY/00-当前月-YYYY-MM/日报/YYYY-MM-DD.md`
- 文件已存在 → 追加（用 `---` 分隔）
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

```
时间：xx:xx - xx:xx / 时间无法确认
事项：……
耗时：……
产出：……

时间：xx:xx - xx:xx
事项：……
耗时：……
产出：……
```

严格要求：

- 只记录时间流水账，不写复盘、不加感受、不虚构时间和产出
- 滴答清单任务和 Cursor/Claude/Codex 对话有明显交集时合并为一条（用滴答的时间 + 对话的细节），无交集的各自独立
- 产出只写有明确依据的，无法确认时省略
- 禁止把消息数、对话条数、会话长度写成产出；能从主题明确推导具体结果就写结果，推导不出就省略产出行

## 配置

`config.json`（不提交 git）：

```json
{
  "cursor_projects_dir": "~/.cursor/projects",
  "claude_dir": "~/.claude",
  "codex_dir": "~/.codex",
  "ticktick_cli": ".claude/skills/ticktick/ticktick_cli/ticktick_cli.py",
  "ticktick_cache_dir": ".claude/skills/daily-report/daily-report/cache/ticktick",
  "code_dirs": ["~/Code"],
  "output_dir": "./40-个人/日记",
  "timezone_offset_hours": 8,
  "llm": {
    "provider": "local_summary",
    "codex_bin": "/Applications/Codex.app/Contents/Resources/codex",
    "codex_workdir": ".",
    "timeout": 900
  },
  "fail_on_generation_error": true
}
```

## AI Agent 使用指引

当用户说"生成今天的日记"时：

1. 自动化场景先用顶层 TickTick CLI 只读预取目标日期缓存：
   `python3 -X utf8 .claude/skills/ticktick/ticktick_cli/ticktick_cli.py daily-completed --date YYYY-MM-DD --timezone-offset-hours 8 --output-file .claude/skills/daily-report/daily-report/cache/ticktick/completed-YYYY-MM-DD.json --no-stdout`
2. 执行 `python3 daily_report.py`（完整流程）
3. 默认用 `local_summary` 本地生成，避免受限自动化环境中嵌套启动 Codex CLI
4. 检查目标文件存在、首行是 `工时填报：`，且没有原始采集标题残留
5. 目标文件已存在且非空时默认跳过；只有确认需要重跑时才加 `--force`

## 项目结构

```
daily-report/
├── daily_report.py              # 主入口
├── generator.py                 # LLM 汇总生成
├── collectors/
│   ├── cursor_collector.py      # Cursor 对话采集
│   ├── claude_collector.py      # Claude Code 对话采集
│   ├── codex_collector.py       # Codex 对话采集
│   ├── ticktick_collector.py    # 滴答清单采集
│   └── git_collector.py         # Git 提交采集
├── config.json                  # 配置（git 忽略）
├── config.example.json          # 配置模板
├── CLAUDE.md                    # 本文件
├── .gitignore
└── docs/                        # 软链接 → Obsidian 需求文档
```

## 依赖

纯 Python 标准库，无第三方依赖。滴答清单优先读取顶层 TickTick CLI 预取缓存；没有缓存时通过子进程调用 ticktick_cli。
