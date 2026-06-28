"""LLM 汇总生成模块

将采集到的数据组装成 prompt，调用 Anthropic Messages API 生成柳比歇夫格式日记。
"""

import json
import re
import subprocess
import tempfile
import urllib.error
import urllib.request
from pathlib import Path


SYSTEM_PROMPT = """你是一个日记整理助手。你的任务是根据提供的原始数据，生成"柳比歇夫日记"——一份时间流水账。

严格要求：
- 只整理出当天实际发生的事项，尽量按时间顺序
- 每条只保留：时间、事项、耗时、产出
- 语言简洁，不啰嗦
- 不补充背景分析
- 不写"时间分类汇总"、"今日复盘"、主观感受
- 不虚构时间和产出，资料里没有的信息写"无法确认"或省略
- 不要把一条事项拆成很多层级
- 不要使用表格
- 输出像个人当天的时间流水账
- 日报最上方必须先输出一行"工时填报：……"
- "工时填报"只写当天的工作、公司项目、项目开发、团队协作相关内容
- 判断是否属于工作项目时，优先参考用户近期安排、近期计划、滴答清单和当日对话中明确出现的工作项目
- "工时填报"必须是一句话，不超过 255 个中文字符
- "工时填报"下面空一行，然后继续输出原有柳比歇夫日记条目
- 除新增"工时填报"首行外，下面的日报格式保持不变
- 如果当天只有很少事项，也只输出核心事项，不为凑内容而扩写
- 相关的对话可以合并为一条事项（比如同一个项目的多次对话）
- 跨数据源合并：滴答清单任务和 Cursor/Claude/Codex 对话的标题/主题有明显交集时，合并为一条（优先用滴答清单的时间 + 对话的细节）；无交集的各自独立成条
- 产出只写有明确依据的（如对话内容、Git 提交可佐证），无法确认产出时省略该行
- 不输出标题，直接从"工时填报"开始

输出格式（每条之间空一行）：
工时填报：一句话概括当天工作相关内容，不超过255字

时间：xx:xx - xx:xx / 时间无法确认
事项：……
耗时：……
产出：……"""


def format_collected_data(cursor_data, claude_data, codex_data, ticktick_data, git_data, target_date):
    """将采集数据格式化为可读文本，用于喂给 LLM 或人工查看。"""
    sections = []
    sections.append(f"# {target_date} 采集数据\n")

    if cursor_data:
        sections.append("## Cursor 对话记录")
        for i, conv in enumerate(cursor_data, 1):
            project = conv.get("project", "未知项目")
            topic = conv.get("topic", "无主题")
            msg_count = conv.get("message_count", 0)
            start = conv.get("start_time", "")
            end = conv.get("end_time", "")
            time_range = f"{start} - {end}" if start and end else "时间未知"
            sections.append(
                f"{i}. 【{project}】{topic}\n"
                f"   消息数: {msg_count}  时间: {time_range}"
            )
        sections.append("")

    if claude_data:
        sections.append("## Claude Code 对话记录")
        for i, conv in enumerate(claude_data, 1):
            project = conv.get("project", "未知项目")
            topic = conv.get("topic", "无主题")
            msg_count = conv.get("message_count", 0)
            start = conv.get("start_time", "")
            end = conv.get("end_time", "")
            time_range = f"{start} - {end}" if start and end else "时间未知"
            sections.append(
                f"{i}. 【{project}】{topic}\n"
                f"   消息数: {msg_count}  时间: {time_range}"
            )
        sections.append("")

    if codex_data:
        sections.append("## Codex 对话记录")
        for i, conv in enumerate(codex_data, 1):
            project = conv.get("project", "未知项目")
            topic = conv.get("topic", "无主题")
            title = conv.get("title", "")
            msg_count = conv.get("message_count", 0)
            start = conv.get("start_time", "")
            end = conv.get("end_time", "")
            time_range = f"{start} - {end}" if start and end else "时间未知"
            title_line = f"（{title}）" if title and title != topic else ""
            sections.append(
                f"{i}. 【{project}】{topic}{title_line}\n"
                f"   消息数: {msg_count}  时间: {time_range}"
            )
        sections.append("")

    if ticktick_data:
        sections.append("## 滴答清单已完成任务")
        grouped = _group_ticktick_tasks(ticktick_data)
        for group_label, tasks in grouped:
            for task in tasks:
                title = task.get("title", "")
                comp_time = task.get("completed_time", "")
                sections.append(f"- {title}  完成于 {comp_time}" if comp_time else f"- {title}")
        sections.append("")

    if git_data:
        sections.append("## Git 提交记录")
        for i, commit in enumerate(git_data, 1):
            project = commit.get("project", "")
            message = commit.get("message", "")
            time = commit.get("time", "")
            sections.append(f"{i}. 【{project}】{message}  ({time})")
        sections.append("")

    if not any([cursor_data, claude_data, codex_data, ticktick_data, git_data]):
        sections.append("（今天没有采集到任何数据）")

    return "\n".join(sections)


def _group_ticktick_tasks(tasks):
    """将同一时间批量完成的任务分组，减少 LLM 输入量。"""
    from collections import OrderedDict
    groups = OrderedDict()
    for task in tasks:
        comp_time = task.get("completed_time", "未知")
        if comp_time not in groups:
            groups[comp_time] = []
        groups[comp_time].append(task)

    result = []
    for time_key, group_tasks in groups.items():
        label = f"完成于 {time_key}" if time_key != "未知" else "完成时间未知"
        result.append((label, group_tasks))
    return result


def generate_diary(formatted_data, config):
    """调用配置的生成器生成柳比歇夫日记。"""
    llm_config = config.get("llm", {})
    provider = llm_config.get("provider", "anthropic")

    if provider == "codex_cli":
        return _generate_with_codex_cli(formatted_data, config)
    if provider == "local_summary":
        return _generate_local_summary(formatted_data)

    return _generate_with_anthropic_messages(formatted_data, llm_config)


def _generate_local_summary(formatted_data):
    """Generate a conservative diary locally from collected metadata.

    This fallback avoids networked LLM calls and nested Codex execution. It only
    uses the collected titles, time ranges, and message/task/commit counts.
    """
    entries = _extract_local_entries(formatted_data)
    work_topics = _summarize_work_topics(entries)

    lines = [
        f"工时填报：{work_topics}",
        "",
    ]

    if not entries:
        lines.extend([
            "时间：时间无法确认",
            "事项：当天未采集到可确认的工作记录",
            "耗时：无法确认",
        ])
        return "\n".join(lines).strip()

    for index, entry in enumerate(entries):
        if index:
            lines.append("")
        lines.append(f"时间：{entry['time']}")
        lines.append(f"事项：{entry['source']}：{entry['title']}")
        lines.append(f"耗时：{entry['duration']}")
        if entry["evidence"]:
            lines.append(f"产出：{entry['evidence']}")

    return "\n".join(lines).strip()


def _extract_local_entries(formatted_data):
    entries = []
    source = ""
    pending = None

    source_map = {
        "## Cursor 对话记录": "Cursor 协作",
        "## Claude Code 对话记录": "Claude Code 协作",
        "## Codex 对话记录": "Codex 协作",
        "## 滴答清单已完成任务": "滴答任务",
        "## Git 提交记录": "Git 提交",
    }

    for raw_line in formatted_data.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line in source_map:
            if pending:
                entries.append(pending)
                pending = None
            source = source_map[line]
            continue
        if not source:
            continue

        numbered = re.match(r"^\d+\.\s*(.+)$", line)
        task = re.match(r"^-\s*(.+?)(?:\s+完成于\s+(.+))?$", line)

        if numbered:
            if pending:
                entries.append(pending)
            pending = _entry_from_numbered(source, numbered.group(1))
            continue

        if task and source == "滴答任务":
            if pending:
                entries.append(pending)
                pending = None
            title = _clean_title(task.group(1))
            completed = task.group(2) or ""
            entries.append({
                "source": source,
                "title": title,
                "time": completed if completed else "时间无法确认",
                "duration": "无法确认",
                "evidence": "完成任务",
            })
            continue

        if pending and "消息数:" in line:
            pending.update(_metadata_from_message_line(line))

    if pending:
        entries.append(pending)

    return entries


def _entry_from_numbered(source, text):
    title = text
    evidence = ""

    if source in ("Cursor 协作", "Claude Code 协作", "Codex 协作"):
        match = re.match(r"【([^】]+)】(.+)$", text)
        if match:
            project = match.group(1).strip()
            topic = _clean_title(match.group(2))
            use_project = (
                project
                and project != "未知项目"
                and not project.startswith("/")
                and not project.startswith("files-mentioned-")
            )
            title = f"{project} / {topic}" if use_project else topic
            evidence = _infer_conversation_output(topic)
    elif source == "Git 提交":
        title = _clean_title(text)
        evidence = "完成 Git 提交"

    return {
        "source": source,
        "title": _clean_title(title),
        "time": "时间无法确认",
        "duration": "无法确认",
        "evidence": evidence,
    }


def _metadata_from_message_line(line):
    metadata = {}
    time_match = re.search(r"时间:\s*(.+)$", line)
    if time_match:
        time_text = time_match.group(1).strip()
        if time_text and time_text != "时间未知":
            metadata["time"] = time_text
            metadata["duration"] = _duration_from_range(time_text)

    return metadata


def _infer_conversation_output(title):
    """Infer a useful output from the task title; return empty when unsure."""
    text = _clean_title(title)
    if not text:
        return ""

    rules = [
        (("生成", "日报"), "日报生成结果"),
        (("日报", "自动化"), "日报自动化处理结果"),
        (("周报", "生成"), "周报生成结果"),
        (("HTML", "生成"), "HTML 交付物"),
        (("HTML", "预览"), "HTML 预览页"),
        (("演播稿",), "演播稿草稿"),
        (("方案",), "方案草稿"),
        (("架构",), "架构判断"),
        (("路线",), "路线判断"),
        (("计划",), "计划草稿"),
        (("排期",), "排期安排"),
        (("调研",), "调研结论"),
        (("调查",), "调查结果"),
        (("排查",), "排查结果"),
        (("核查",), "核查结果"),
        (("检查",), "检查结果"),
        (("验证",), "验证结果"),
        (("测试",), "测试结果"),
        (("修复",), "修复方案"),
        (("修改",), "修改方案"),
        (("优化",), "优化方案"),
        (("总结",), "总结稿"),
        (("整理",), "整理结果"),
        (("分类",), "分类结果"),
        (("搜索",), "搜索结果"),
        (("查找",), "查找结果"),
        (("识别",), "识别结果"),
        (("对比",), "对比结论"),
        (("分析",), "分析结论"),
        (("Lint",), "Lint 检查结果"),
        (("Skill",), "Skill 处理结果"),
    ]
    for keywords, output in rules:
        if all(keyword in text for keyword in keywords):
            return output
    return ""


def _duration_from_range(time_text):
    match = re.match(r"^(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})$", time_text)
    if not match:
        return "无法确认"

    start_h, start_m = [int(part) for part in match.group(1).split(":")]
    end_h, end_m = [int(part) for part in match.group(2).split(":")]
    minutes = (end_h * 60 + end_m) - (start_h * 60 + start_m)
    if minutes <= 0:
        return "无法确认"
    hours, mins = divmod(minutes, 60)
    if hours and mins:
        return f"{hours}小时{mins}分钟"
    if hours:
        return f"{hours}小时"
    return f"{mins}分钟"


def _clean_title(text):
    raw_text = text
    if "local-command-caveat" in raw_text or raw_text.strip().startswith("Caveat:"):
        return "本地命令与 Vault 自动化上下文处理"

    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    if "Automation:" in text:
        text = text.split("Automation:", 1)[1]
        text = re.split(r"\s+Automation ID:|\s+Automation memory:|\s+Last run", text, 1)[0]
        return f"自动化：{text.strip()}"

    if "AI 协作全生命周期" in text:
        return "AI 协作全生命周期系统支线合并与主线初始化"

    if "pinned ref" in text or "contracts" in text:
        return "contracts-docs 固定版本引用方案"

    if text.startswith("你是一个日记整理助手"):
        return "日报生成提示词与格式校验"

    if "Applications mentioned by the user" in text:
        return "访达窗口上下文相关任务"

    if "Hermes Agent" in text:
        return "Hermes Agent 官方 Logo 与头像生成"

    if "codex-clipboard" in text or "/var/folders/" in text:
        return "图片和文件上下文相关 Codex 任务"

    if "Claude Code v" in text or "API Usage Billing" in text:
        return "Claude Code 运行状态与用量核对"

    if text.startswith("/plan "):
        text = text.removeprefix("/plan ").strip()
    if "enterprise ontology" in text.lower():
        return "企业本体智能方案设计"

    if text.lower() in {"hi, calude", "hi, claude", "hi, caldue"}:
        return "Claude Code 连通性测试"

    if "https:/" in text:
        return "链接来源识别"

    text = re.sub(r"^#+\s*", "", text)
    text = re.sub(r"(/[A-Za-z0-9_.@-]+)+", " ", text)
    text = re.sub(r"（[^（）]*）$", "", text).strip()
    text = re.sub(r"\s+", " ", text)
    return text[:120] if len(text) > 120 else text


def _summarize_work_topics(entries):
    if not entries:
        return "当天未采集到可确认的工作项目记录"

    counts = {}
    for entry in entries:
        counts[entry["source"]] = counts.get(entry["source"], 0) + 1

    ordered_sources = ["Claude Code 协作", "Codex 协作", "Cursor 协作", "滴答任务", "Git 提交"]
    parts = [f"{source}{counts[source]}项" for source in ordered_sources if source in counts]
    result = f"整理推进{'、'.join(parts)}等工作记录"
    return result[:255]


def _generate_with_codex_cli(formatted_data, config):
    llm_config = config.get("llm", {})
    codex_bin = llm_config.get("codex_bin", "/Applications/Codex.app/Contents/Resources/codex")
    workdir = llm_config.get("codex_workdir") or str(Path.cwd())
    timeout = int(llm_config.get("timeout", 900))

    prompt = (
        SYSTEM_PROMPT
        + "\n\n只输出日报正文，不要解释，不要 Markdown 标题，不要代码块。"
        + "\n原始采集标题、采集日志、错误日志不要输出。"
        + "\n\n请根据以下采集数据生成柳比歇夫日记：\n\n"
        + formatted_data
    )

    with tempfile.TemporaryDirectory(prefix="daily-report-codex-") as tmp_dir:
        output_path = Path(tmp_dir) / "diary.md"
        cmd = [
            codex_bin,
            "--ask-for-approval",
            "never",
            "exec",
            "--skip-git-repo-check",
            "--sandbox",
            "read-only",
            "--cd",
            workdir,
            "-o",
            str(output_path),
            "-",
        ]
        try:
            result = subprocess.run(
                cmd,
                input=prompt,
                text=True,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
        except FileNotFoundError:
            print(f"[generator] Codex CLI 不存在: {codex_bin}")
            return None
        except subprocess.TimeoutExpired:
            print(f"[generator] Codex CLI 超时: {timeout}s")
            return None

        if result.returncode != 0:
            print(f"[generator] Codex CLI 失败: exit {result.returncode}")
            if result.stderr:
                print(result.stderr[-4000:])
            return None

        if not output_path.exists():
            print("[generator] Codex CLI 未生成输出文件")
            if result.stdout:
                print(result.stdout[-4000:])
            return None

        diary = output_path.read_text(encoding="utf-8").strip()
        if not diary.startswith("工时填报："):
            print("[generator] Codex CLI 输出缺少工时填报首行")
            print(diary[:1000])
            return None
        if "采集数据" in diary.splitlines()[0]:
            print("[generator] Codex CLI 输出疑似原始采集数据")
            return None
        return diary


def _generate_with_anthropic_messages(formatted_data, llm_config):
    api_base = llm_config.get("api_base", "")
    api_key = llm_config.get("api_key", "")
    model = llm_config.get("model", "")
    max_tokens = llm_config.get("max_tokens", 4096)

    if not api_base or not api_key:
        print("[generator] LLM 未配置，返回原始采集数据")
        return None

    url = f"{api_base}/v1/messages"

    payload = json.dumps({
        "model": model,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "user", "content": f"请根据以下采集数据生成柳比歇夫日记：\n\n{formatted_data}"}
        ],
        "system": SYSTEM_PROMPT,
    }).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }

    try:
        request = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(request, timeout=300) as response:
            body = json.loads(response.read().decode("utf-8"))
            content = body.get("content", [])
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    return block.get("text", "")
            return str(body)
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        print(f"[generator] API 请求失败: HTTP {exc.code}\n{error_body}")
        return None
    except urllib.error.URLError as exc:
        print(f"[generator] 网络请求失败: {exc}")
        return None
    except Exception as exc:
        print(f"[generator] 未知错误: {exc}")
        return None


def _self_check():
    sample = "\n".join([
        "## Codex 对话记录",
        "1. 【Zhimeng】调研左侧项目结构与右侧会话管理工具",
        "   消息数: 12  时间: 18:43 - 18:48",
        "2. 【Zhimeng】hi",
        "   消息数: 2  时间: 19:00 - 19:01",
    ])
    diary = _generate_local_summary(sample)
    assert "产出：调研结论" in diary
    assert "对话记录" not in diary
    assert "事项：Codex 协作：Zhimeng / hi" in diary


if __name__ == "__main__":
    _self_check()
