"""Git 提交记录采集模块

扫描代码目录下的 git 仓库，提取当天提交记录。
"""

import subprocess
from datetime import date
from pathlib import Path


def collect(config, target_date):
    """采集 Git 当天提交记录。

    返回: [{project, hash, message, time}]
    """
    code_dirs = config.get("code_dirs", [])
    results = []

    since = target_date.isoformat()
    until = (target_date + __import__("datetime").timedelta(days=1)).isoformat()

    for code_dir in code_dirs:
        code_path = Path(code_dir)
        if not code_path.exists():
            continue

        for sub in code_path.iterdir():
            if not sub.is_dir():
                continue
            git_dir = sub / ".git"
            if not git_dir.exists():
                continue

            commits = _get_commits(sub, since, until)
            for commit in commits:
                commit["project"] = sub.name
                results.append(commit)

    results.sort(key=lambda x: x.get("time", ""))
    return results


def _get_commits(repo_path, since, until):
    """获取指定仓库在日期范围内的提交。"""
    try:
        result = subprocess.run(
            [
                "git", "log",
                f"--since={since}",
                f"--until={until}",
                "--format=%H|%s|%ai",
                "--no-merges",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=10,
            cwd=str(repo_path),
        )

        if result.returncode != 0:
            return []

        commits = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("|", 2)
            if len(parts) >= 3:
                commits.append({
                    "hash": parts[0][:8],
                    "message": parts[1],
                    "time": parts[2],
                })
        return commits
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []
