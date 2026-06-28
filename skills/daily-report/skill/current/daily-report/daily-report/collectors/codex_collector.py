"""Codex 对话记录采集模块。

优先读取 ~/.codex/state_*.sqlite 中的 threads 表获取会话索引，
再解析 rollout JSONL 文件中的真实用户/助手消息。
"""

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path


def collect(config, target_date):
    """采集 Codex 对话记录。

    返回: [{project, topic, title, session_id, start_time, end_time, message_count, file_path}]
    """
    if not isinstance(config, dict):
        config = {}

    codex_dir = Path(config.get("codex_dir") or "~/.codex").expanduser()
    tz_offset = config.get("timezone_offset_hours", 8)
    tz = timezone(timedelta(hours=tz_offset))

    day_start = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=tz)
    day_end = day_start + timedelta(days=1)
    start_ts = int(day_start.timestamp())
    end_ts = int(day_end.timestamp())

    results = []

    if not codex_dir.exists():
        print(f"[codex] 目录不存在: {codex_dir}")
        return results

    threads = _load_threads_from_sqlite(codex_dir, start_ts, end_ts)
    if not threads:
        threads = _load_threads_from_files(codex_dir, target_date)

    seen_paths = set()
    for thread in threads:
        if not isinstance(thread, dict):
            continue
        if _should_skip_thread(thread):
            continue

        rollout_path_raw = _safe_str(thread.get("rollout_path"))
        if not rollout_path_raw:
            continue
        rollout_path = Path(rollout_path_raw).expanduser()
        if not rollout_path.is_absolute():
            rollout_path = codex_dir / rollout_path
        if not rollout_path.exists() or rollout_path in seen_paths:
            continue
        seen_paths.add(rollout_path)

        conversation = _parse_rollout(rollout_path, target_date, tz)
        if not conversation:
            continue

        title = _truncate(thread.get("title"), 120)
        cwd = thread.get("cwd", "") or conversation.get("cwd", "")
        project = _project_name(cwd)

        conversation["project"] = project
        conversation["title"] = title
        conversation["session_id"] = _safe_str(thread.get("id")) or conversation.get("session_id", "")
        conversation["file_path"] = str(rollout_path)
        if not conversation.get("topic"):
            conversation["topic"] = title or "（无主题）"
        results.append(conversation)

    results.sort(key=lambda x: x.get("start_time", ""))
    return results


def _load_threads_from_sqlite(codex_dir, start_ts, end_ts):
    """从 Codex state sqlite 中读取与目标日期有交集的 threads。"""
    db_paths = sorted(codex_dir.glob("state_*.sqlite"), key=lambda p: p.stat().st_mtime, reverse=True)
    for db_path in db_paths:
        try:
            with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    """
                    SELECT id, title, cwd, rollout_path, created_at, updated_at, source, thread_source, agent_role
                    FROM threads
                    WHERE updated_at >= ? AND created_at < ?
                    ORDER BY updated_at ASC
                    """,
                    (start_ts, end_ts),
                ).fetchall()
                return [dict(row) for row in rows]
        except sqlite3.Error:
            continue
    return []


def _load_threads_from_files(codex_dir, target_date):
    """SQLite 不可用时按 rollout 文件名兜底。"""
    date_part = target_date.strftime("%Y-%m-%d")
    y = target_date.strftime("%Y")
    m = target_date.strftime("%m")
    d = target_date.strftime("%d")

    candidates = []
    candidates.extend((codex_dir / "sessions" / y / m / d).glob(f"rollout-{date_part}*.jsonl"))
    candidates.extend((codex_dir / "archived_sessions").glob(f"rollout-{date_part}*.jsonl"))

    threads = []
    for path in sorted(candidates):
        meta = _read_rollout_head(path)
        threads.append(
            {
                "id": "",
                "title": "",
                "cwd": "",
                "rollout_path": str(path),
                "created_at": 0,
                "updated_at": 0,
                "source": "",
                "thread_source": "",
                "agent_role": "",
                "fallback_first_user": "",
                **meta,
            }
        )
    return threads


def _read_rollout_head(rollout_path, max_lines=80):
    """读取 rollout 开头的轻量元数据，用于兜底路径过滤内部线程。"""
    meta = {}

    try:
        with rollout_path.open("r", encoding="utf-8") as f:
            for index, line in enumerate(f):
                if index >= max_lines:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(entry, dict):
                    continue

                payload = entry.get("payload", {})
                if entry.get("type") == "session_meta" and isinstance(payload, dict):
                    meta["id"] = _safe_str(payload.get("id"))
                    meta["cwd"] = _safe_str(payload.get("cwd"))
                    meta["source"] = payload.get("source", "")
                    meta["thread_source"] = _safe_str(payload.get("thread_source"))
                    meta["agent_role"] = _safe_str(payload.get("agent_role"))

                if "fallback_first_user" not in meta:
                    first_user = _user_text_from_entry(entry)
                    if first_user:
                        meta["fallback_first_user"] = first_user

                if meta.get("source") and meta.get("fallback_first_user"):
                    break
    except (OSError, UnicodeDecodeError):
        return {}

    return meta


def _should_skip_thread(thread):
    """跳过 Codex 内部子线程与审批审查线程，避免污染日报。"""
    if not isinstance(thread, dict):
        return False

    source = thread.get("source", "")
    thread_source = _safe_str(thread.get("thread_source"))
    agent_role = _safe_str(thread.get("agent_role"))
    title = _safe_str(thread.get("title")).lstrip()
    fallback_first_user = _safe_str(thread.get("fallback_first_user")).lstrip()
    return (
        thread_source == "subagent"
        or agent_role == "guardian"
        or _source_mentions_subagent(source)
        or _has_internal_prompt_prefix(title)
        or _has_internal_prompt_prefix(fallback_first_user)
    )


def _parse_rollout(rollout_path, target_date, tz):
    user_texts = []
    assistant_count = 0
    user_count = 0
    timestamps = []
    fallback_user_texts = []
    fallback_user_count = 0
    fallback_assistant_count = 0
    session_id = ""
    cwd = ""

    try:
        with rollout_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(entry, dict):
                    continue

                timestamp = _parse_timestamp(entry.get("timestamp", ""), tz)
                payload = entry.get("payload", {})

                if entry.get("type") == "session_meta" and isinstance(payload, dict):
                    session_id = _safe_str(payload.get("id")) or session_id
                    cwd = _safe_str(payload.get("cwd")) or cwd

                if not isinstance(payload, dict):
                    continue

                if _is_real_user_event(entry):
                    text = _user_text_from_event_payload(payload)
                    if text and timestamp and timestamp.date() == target_date:
                        user_texts.append(text)
                        user_count += 1
                        timestamps.append(timestamp)
                    continue

                if _is_agent_event(entry):
                    if timestamp and timestamp.date() == target_date:
                        assistant_count += 1
                        timestamps.append(timestamp)
                    continue

                fallback = _fallback_message(payload)
                if not fallback:
                    continue
                role, text = fallback
                if role == "user":
                    text = _clean_user_text(text)
                    if text and timestamp and timestamp.date() == target_date:
                        fallback_user_texts.append(text)
                        fallback_user_count += 1
                        timestamps.append(timestamp)
                elif role == "assistant":
                    if timestamp and timestamp.date() == target_date:
                        fallback_assistant_count += 1
                        timestamps.append(timestamp)
    except (OSError, UnicodeDecodeError):
        return None

    if not user_texts and fallback_user_texts:
        user_texts = fallback_user_texts
        user_count = fallback_user_count
        assistant_count = fallback_assistant_count

    if not user_texts and not assistant_count:
        return None

    start_time = ""
    end_time = ""
    if timestamps:
        timestamps.sort()
        start_time = timestamps[0].strftime("%H:%M")
        end_time = timestamps[-1].strftime("%H:%M")

    return {
        "topic": _truncate(user_texts[0], 200) if user_texts else "",
        "start_time": start_time,
        "end_time": end_time,
        "user_messages": user_count,
        "assistant_messages": assistant_count,
        "message_count": user_count + assistant_count,
        "session_id": session_id,
        "cwd": cwd,
    }


def _is_real_user_event(entry):
    if not isinstance(entry, dict):
        return False
    payload = entry.get("payload", {})
    return isinstance(payload, dict) and entry.get("type") == "event_msg" and payload.get("type") == "user_message"


def _is_agent_event(entry):
    if not isinstance(entry, dict):
        return False
    payload = entry.get("payload", {})
    return isinstance(payload, dict) and entry.get("type") == "event_msg" and payload.get("type") == "agent_message"


def _fallback_message(payload):
    if not isinstance(payload, dict):
        return None
    if payload.get("type") != "message":
        return None
    role = payload.get("role", "")
    if role not in {"user", "assistant"}:
        return None
    text = _message_content_to_text(payload.get("content", []))
    if role == "user" and _looks_like_context_injection(text):
        return None
    return role, text


def _message_content_to_text(content):
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") in {"input_text", "output_text", "text"}:
            text = block.get("text", "")
            if isinstance(text, str):
                parts.append(text)
    return "\n".join(part for part in parts if part)


def _user_text_from_entry(entry):
    if not isinstance(entry, dict):
        return ""
    payload = entry.get("payload", {})
    if not isinstance(payload, dict):
        return ""
    if _is_real_user_event(entry):
        return _user_text_from_event_payload(payload)
    fallback = _fallback_message(payload)
    if fallback and fallback[0] == "user":
        return _clean_user_text(fallback[1])
    return ""


def _user_text_from_event_payload(payload):
    return _clean_user_text(payload.get("message", ""))


def _clean_user_text(text):
    if not isinstance(text, str):
        return ""
    lines = text.strip().splitlines()
    cleaned = []
    skipping_files = False

    for line in lines:
        stripped = line.strip()
        if stripped == "# Files mentioned by the user:":
            skipping_files = True
            continue
        if skipping_files:
            if not stripped:
                skipping_files = False
            continue
        cleaned.append(line)

    text = "\n".join(cleaned).strip()
    if _looks_like_context_injection(text):
        return ""
    return text


def _looks_like_context_injection(text):
    if not isinstance(text, str):
        return False
    stripped = text.lstrip()
    return (
        stripped.startswith("# AGENTS.md instructions")
        or stripped.startswith("<INSTRUCTIONS>")
        or stripped.startswith("<environment_context>")
    )


def _parse_timestamp(value, tz):
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(tz)
    except (TypeError, ValueError):
        return None


def _project_name(cwd):
    cwd = _safe_str(cwd)
    if not cwd:
        return "Codex"
    name = Path(cwd).name
    return name or "Codex"


def _truncate(text, max_len):
    text = _safe_str(text)
    text = " ".join(text.strip().split())
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def _safe_str(value):
    return value if isinstance(value, str) else ""


def _source_mentions_subagent(source):
    if isinstance(source, str):
        return "subagent" in source
    if isinstance(source, dict):
        return any(_source_mentions_subagent(key) or _source_mentions_subagent(value) for key, value in source.items())
    if isinstance(source, (list, tuple)):
        return any(_source_mentions_subagent(item) for item in source)
    return False


def _has_internal_prompt_prefix(text):
    return text.startswith(
        (
            "The following is the Codex agent history whose request action you are assessing.",
            "Reviewed Codex session id:",
        )
    )
