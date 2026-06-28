"""Cursor 对话记录采集模块

扫描 .cursor/projects/*/agent-transcripts/*/*.jsonl
按文件修改时间筛选当天对话，提取主题摘要。
"""

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path


def collect(config, target_date):
    """采集 Cursor 对话记录。

    返回: [{project, topic, start_time, end_time, message_count, file_path}]
    """
    projects_dir = Path(config["cursor_projects_dir"]).expanduser()
    tz_offset = config.get("timezone_offset_hours", 8)
    tz = timezone(timedelta(hours=tz_offset))

    day_start = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=tz)
    day_end = day_start + timedelta(days=1)

    results = []

    if not projects_dir.exists():
        print(f"[cursor] 目录不存在: {projects_dir}")
        return results

    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue

        transcripts_dir = project_dir / "agent-transcripts"
        if not transcripts_dir.exists():
            continue

        project_name = project_dir.name

        for session_dir in transcripts_dir.iterdir():
            if not session_dir.is_dir():
                continue

            for jsonl_file in session_dir.glob("*.jsonl"):
                mtime = datetime.fromtimestamp(os.path.getmtime(jsonl_file), tz=tz)
                if not (day_start <= mtime < day_end):
                    continue

                conversation = _parse_transcript(jsonl_file)
                if conversation:
                    conversation["project"] = project_name
                    conversation["file_path"] = str(jsonl_file)
                    results.append(conversation)

    results.sort(key=lambda x: x.get("start_time", ""))
    return results


def _parse_transcript(jsonl_path):
    """解析单个 Cursor 对话文件，提取主题和时间信息。"""
    messages = []
    try:
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                    messages.append(msg)
                except json.JSONDecodeError:
                    continue
    except (OSError, UnicodeDecodeError):
        return None

    if not messages:
        return None

    topic = _extract_topic(messages)
    user_msg_count = sum(1 for m in messages if m.get("role") == "user")
    assistant_msg_count = sum(1 for m in messages if m.get("role") == "assistant")

    start_time = ""
    end_time = ""

    first_ts = _find_timestamp(messages, from_start=True)
    last_ts = _find_timestamp(messages, from_start=False)
    if first_ts:
        start_time = first_ts
    if last_ts:
        end_time = last_ts

    return {
        "topic": topic,
        "start_time": start_time,
        "end_time": end_time,
        "user_messages": user_msg_count,
        "assistant_messages": assistant_msg_count,
        "message_count": user_msg_count + assistant_msg_count,
    }


def _extract_topic(messages):
    """从用户第一条消息中提取对话主题。"""
    for msg in messages:
        if msg.get("role") != "user":
            continue
        content = msg.get("message", {}).get("content", [])
        if isinstance(content, str):
            return _truncate(content, 200)
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text", "")
                    text = _strip_system_tags(text)
                    if text:
                        return _truncate(text, 200)
    return "（无法提取主题）"


def _strip_system_tags(text):
    """去除 Cursor 注入的 <user_query> 等系统标签，只保留用户原始输入。"""
    import re
    match = re.search(r"<user_query>\s*(.*?)\s*</user_query>", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    for tag in ["<attached_files>", "<system_reminder>", "<open_and_recently_viewed_files>",
                "<git_status>", "<user_info>", "<rules>", "<agent_skills>", "<agent_transcripts>"]:
        idx = text.find(tag)
        if idx == 0:
            close_tag = tag.replace("<", "</")
            close_idx = text.find(close_tag)
            if close_idx > 0:
                text = text[close_idx + len(close_tag):]
    text = text.strip()
    if not text:
        return ""
    lines = text.split("\n")
    meaningful = [l for l in lines if l.strip() and not l.strip().startswith("<")]
    return "\n".join(meaningful[:5]).strip() if meaningful else text[:200]


def _find_timestamp(messages, from_start=True):
    """尝试从消息中提取时间戳。Cursor 的标准 transcript 没有时间字段，用文件时间兜底。"""
    return ""


def _truncate(text, max_len):
    text = text.strip()
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."
