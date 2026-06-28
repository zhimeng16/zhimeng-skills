"""Claude Code 对话记录采集模块

通过 history.jsonl 索引筛选当天 session，
再从 projects/<encoded-path>/<sessionId>.jsonl 读取完整对话。
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


def collect(config, target_date):
    """采集 Claude Code 对话记录。

    返回: [{project, topic, session_id, start_time, end_time, message_count}]
    """
    claude_dir = Path(config["claude_dir"]).expanduser()
    tz_offset = config.get("timezone_offset_hours", 8)
    tz = timezone(timedelta(hours=tz_offset))

    day_start = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=tz)
    day_end = day_start + timedelta(days=1)

    day_start_ms = int(day_start.timestamp() * 1000)
    day_end_ms = int(day_end.timestamp() * 1000)

    results = []

    history_path = claude_dir / "history.jsonl"
    if not history_path.exists():
        print(f"[claude] 索引文件不存在: {history_path}")
        return results

    sessions = _filter_today_sessions(history_path, day_start_ms, day_end_ms)

    seen_session_ids = set()
    for session in sessions:
        sid = session["sessionId"]
        if sid in seen_session_ids:
            continue
        seen_session_ids.add(sid)

        project_raw = session.get("project", "")
        project_encoded = _encode_project_path(project_raw)
        session_file = _find_session_file(claude_dir / "projects", project_encoded, sid)

        conversation = None
        if session_file.exists():
            conversation = _parse_session(session_file, tz)

        if conversation:
            conversation["project"] = project_raw
            conversation["session_id"] = sid
            if not conversation.get("topic"):
                conversation["topic"] = session.get("display", "（无主题）")
        else:
            ts = datetime.fromtimestamp(session["timestamp"] / 1000, tz=tz)
            conversation = {
                "project": project_raw,
                "session_id": sid,
                "topic": session.get("display", "（无主题）"),
                "start_time": ts.strftime("%H:%M"),
                "end_time": "",
                "message_count": 1,
            }

        results.append(conversation)

    results.sort(key=lambda x: x.get("start_time", ""))
    return results


def _filter_today_sessions(history_path, start_ms, end_ms):
    """从 history.jsonl 筛选目标日期范围的 session。"""
    sessions = []
    try:
        with open(history_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    ts = entry.get("timestamp", 0)
                    if start_ms <= ts < end_ms:
                        sessions.append(entry)
                except json.JSONDecodeError:
                    continue
    except (OSError, UnicodeDecodeError):
        pass
    return sessions


def _find_session_file(projects_dir, encoded_name, session_id):
    """查找 session 文件，支持大小写不敏感匹配。"""
    direct = projects_dir / encoded_name / f"{session_id}.jsonl"
    if direct.exists():
        return direct

    if not projects_dir.exists():
        return direct

    encoded_lower = encoded_name.lower()
    for d in projects_dir.iterdir():
        if d.is_dir() and d.name.lower() == encoded_lower:
            candidate = d / f"{session_id}.jsonl"
            if candidate.exists():
                return candidate

    return direct


def _encode_project_path(project_path):
    """将项目路径编码为 Claude Code 的目录名格式。

    Windows: E:\\Code\\foo -> E--Code-foo
      - 盘符保留，冒号去掉
      - 第一个反斜杠变 --
      - 后续反斜杠变 -

    macOS/Linux: /home/user/Code/foo -> -home-user-Code-foo
      - 所有 / 替换为 -
    """
    if not project_path:
        return ""
    p = project_path
    # Windows 盘符格式: E:\Code\foo
    if len(p) >= 2 and p[1] == ":":
        p = p.replace("/", "\\")
        drive = p[0].upper()
        rest = p[2:].lstrip("\\")
        return drive + "--" + rest.replace("\\", "-").replace(" ", "-")
    # macOS/Linux 格式: /home/user/Code/foo
    return p.replace("/", "-").replace(" ", "-")


def _parse_session(session_path, tz):
    """解析完整 session JSONL，提取主题和时间。"""
    messages = []
    first_user_text = ""
    timestamps = []

    try:
        with open(session_path, "r", encoding="utf-8") as f:
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

    user_count = 0
    assistant_count = 0

    for msg in messages:
        msg_type = msg.get("type", "")
        ts_str = msg.get("timestamp", "")
        if ts_str:
            timestamps.append(ts_str)

        if msg_type == "user":
            user_count += 1
            if not first_user_text:
                content = msg.get("message", {}).get("content", "")
                if isinstance(content, str):
                    first_user_text = content[:200]
                elif isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            first_user_text = block.get("text", "")[:200]
                            break
        elif msg_type == "assistant":
            assistant_count += 1

    start_time = ""
    end_time = ""
    if timestamps:
        try:
            first_dt = datetime.fromisoformat(timestamps[0].replace("Z", "+00:00")).astimezone(tz)
            start_time = first_dt.strftime("%H:%M")
        except (ValueError, IndexError):
            pass
        try:
            last_dt = datetime.fromisoformat(timestamps[-1].replace("Z", "+00:00")).astimezone(tz)
            end_time = last_dt.strftime("%H:%M")
        except (ValueError, IndexError):
            pass

    return {
        "topic": first_user_text.strip() if first_user_text else "",
        "start_time": start_time,
        "end_time": end_time,
        "message_count": user_count + assistant_count,
    }
