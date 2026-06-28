"""滴答清单已完成任务采集模块

调用 ticktick_cli.py 的 completed 命令获取当天已完成任务。
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


def collect(config, target_date):
    """采集滴答清单当天已完成任务。

    返回: [{title, completed_time, project_name, content}]
    """
    cli_path = config.get("ticktick_cli", "")
    if not cli_path:
        print("[ticktick] 未配置 ticktick_cli 路径")
        return []

    tz_offset = config.get("timezone_offset_hours", 8)
    tz = timezone(timedelta(hours=tz_offset))

    day_start_local = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=tz)
    day_end_local = day_start_local + timedelta(days=1) - timedelta(seconds=1)

    day_start_utc = day_start_local.astimezone(timezone.utc)
    day_end_utc = day_end_local.astimezone(timezone.utc)

    start_str = day_start_utc.strftime("%Y-%m-%dT%H:%M:%S+0000")
    end_str = day_end_utc.strftime("%Y-%m-%dT%H:%M:%S+0000")

    cache_path = _cache_path(config, target_date)
    raw = _load_cache(cache_path)
    if raw is not None:
        print(f"[ticktick] 使用缓存: {cache_path}")
        return _parse_tasks(raw, tz)

    raw, auth_failed = _run_cli(cli_path, "completed", start_str, end_str)

    if raw is None and auth_failed:
        print("[ticktick] 尝试刷新 token 后重试...")
        _run_cli(cli_path, "refresh-token", "", "")
        raw, _ = _run_cli(cli_path, "completed", start_str, end_str)

    if raw is None:
        print("[ticktick] 采集失败")
        return []

    _write_cache(cache_path, raw)

    return _parse_tasks(raw, tz)


def _cache_path(config, target_date):
    cache_dir = config.get(
        "ticktick_cache_dir",
        ".claude/skills/daily-report/daily-report/cache/ticktick",
    )
    return Path(cache_dir).expanduser() / f"completed-{target_date}.json"


def _load_cache(cache_path):
    if not cache_path.exists() or cache_path.stat().st_size == 0:
        return None
    try:
        raw = cache_path.read_text(encoding="utf-8").strip()
        data = json.loads(raw)
        if not isinstance(data, list):
            print(f"[ticktick] 缓存不是任务列表，忽略: {cache_path}")
            return None
        return raw
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(f"[ticktick] 缓存读取失败，忽略: {cache_path} ({exc})")
        return None


def _write_cache(cache_path, raw):
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(raw.strip() + "\n", encoding="utf-8")
        print(f"[ticktick] 已写入缓存: {cache_path}")
    except OSError as exc:
        print(f"[ticktick] 写入缓存失败: {exc}")


def _run_cli(cli_path, command, start_str, end_str):
    """调用 ticktick_cli.py 命令。"""
    cmd = [sys.executable, cli_path]

    if command == "refresh-token":
        cmd.append("refresh-token")
    elif command == "completed":
        cmd.extend(["completed", "--start-date", start_str, "--end-date", end_str])
    else:
        return None

    try:
        env = dict(__import__("os").environ)
        env["PYTHONIOENCODING"] = "utf-8"

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
            env=env,
        )

        if result.returncode != 0:
            stderr = result.stderr.strip()
            if "401" in stderr or "Unauthorized" in stderr:
                return None, True
            print(f"[ticktick] 命令失败: {stderr}")
            return None, False

        return result.stdout.strip(), False
    except subprocess.TimeoutExpired:
        print("[ticktick] 命令超时")
        return None, False
    except FileNotFoundError:
        print(f"[ticktick] 找不到 CLI: {cli_path}")
        return None, False


def _parse_tasks(raw_output, tz):
    """解析 CLI 输出的 JSON 任务列表。"""
    try:
        data = json.loads(raw_output)
    except json.JSONDecodeError:
        print(f"[ticktick] 无法解析输出: {raw_output[:200]}")
        return []

    if not isinstance(data, list):
        data = [data] if isinstance(data, dict) else []

    results = []
    for task in data:
        completed_time = ""
        comp_date = task.get("completedTime", "")
        if comp_date:
            try:
                dt = datetime.fromisoformat(comp_date.replace("Z", "+00:00")).astimezone(tz)
                completed_time = dt.strftime("%H:%M")
            except ValueError:
                completed_time = comp_date

        results.append({
            "title": task.get("title", ""),
            "completed_time": completed_time,
            "project_name": task.get("projectName", task.get("projectId", "")),
            "content": task.get("content", ""),
        })

    results.sort(key=lambda x: x.get("completed_time", ""))
    return results
