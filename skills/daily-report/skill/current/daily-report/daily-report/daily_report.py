"""AI 日报自动生成器

自动从 Cursor 对话记录、Claude Code 对话记录、Codex 对话记录、
滴答清单已完成任务、Git 提交记录采集当天信息，调用 LLM API 生成柳比歇夫格式日记，
输出到 Obsidian vault。

用法:
    python daily_report.py                      # 生成今天的日记
    python daily_report.py --date 2026-03-15    # 指定日期
    python daily_report.py --collect-only       # 仅采集不生成
    python daily_report.py --source cursor      # 仅采集某个数据源
"""

import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from collectors import cursor_collector, claude_collector, codex_collector, ticktick_collector, git_collector
from generator import format_collected_data, generate_diary


def fail(message):
    print(message, file=sys.stderr)
    raise SystemExit(1)


def load_config():
    config_path = Path(__file__).parent / "config.json"
    if not config_path.exists():
        fail(f"配置文件不存在: {config_path}\n请复制 config.example.json 为 config.json 并填写配置")
    with config_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        fail(f"日期格式错误: {date_str}（应为 YYYY-MM-DD）")


def get_today(tz_offset_hours):
    tz = timezone(timedelta(hours=tz_offset_hours))
    return datetime.now(tz=tz).date()


def collect_all(config, target_date, source_filter=None):
    """执行数据采集。"""
    cursor_data = []
    claude_data = []
    codex_data = []
    ticktick_data = []
    git_data = []

    sources = source_filter.split(",") if source_filter else ["cursor", "claude", "codex", "ticktick", "git"]

    if "cursor" in sources:
        print("[采集] Cursor 对话记录...")
        try:
            cursor_data = cursor_collector.collect(config, target_date)
            print(f"  → 找到 {len(cursor_data)} 个对话")
        except Exception as e:
            print(f"  → 采集失败: {e}")

    if "claude" in sources:
        print("[采集] Claude Code 对话记录...")
        try:
            claude_data = claude_collector.collect(config, target_date)
            print(f"  → 找到 {len(claude_data)} 个对话")
        except Exception as e:
            print(f"  → 采集失败: {e}")

    if "codex" in sources:
        print("[采集] Codex 对话记录...")
        try:
            codex_data = codex_collector.collect(config, target_date)
            print(f"  → 找到 {len(codex_data)} 个对话")
        except Exception as e:
            print(f"  → 采集失败: {e}")

    if "ticktick" in sources:
        print("[采集] 滴答清单已完成任务...")
        try:
            ticktick_data = ticktick_collector.collect(config, target_date)
            print(f"  → 找到 {len(ticktick_data)} 个任务")
        except Exception as e:
            print(f"  → 采集失败: {e}")

    if "git" in sources:
        print("[采集] Git 提交记录...")
        try:
            git_data = git_collector.collect(config, target_date)
            print(f"  → 找到 {len(git_data)} 条提交")
        except Exception as e:
            print(f"  → 采集失败: {e}")

    return cursor_data, claude_data, codex_data, ticktick_data, git_data


def resolve_output_path(output_dir, target_date, output_file=None):
    """Resolve the diary path, using the vault's year/month diary structure."""
    if output_file:
        return Path(output_file).expanduser()

    output_root = Path(output_dir).expanduser()
    year = target_date.strftime("%Y")
    month = target_date.strftime("%Y-%m")

    if output_root.name != "日记":
        return output_root / f"{target_date}.md"

    current_year_dir = output_root / f"00-当前年-{year}"
    archive_year_dir = output_root / year
    year_dir = current_year_dir if current_year_dir.exists() or not archive_year_dir.exists() else archive_year_dir

    archive_month_dir = year_dir / month
    current_month_dir = year_dir / f"00-当前月-{month}"
    month_dir = archive_month_dir if archive_month_dir.exists() else current_month_dir

    return month_dir / "日报" / f"{target_date}.md"


def write_output(content, output_dir, target_date, output_file=None):
    """写入日记文件。如果文件已存在则追加，不存在则创建。"""
    output_path = resolve_output_path(output_dir, target_date, output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists():
        existing = output_path.read_text(encoding="utf-8")
        separator = "\n\n---\n\n" if existing.strip() else ""
        output_path.write_text(
            existing + separator + content + "\n",
            encoding="utf-8",
        )
        print(f"\n[输出] 已追加到: {output_path}")
    else:
        output_path.write_text(content + "\n", encoding="utf-8")
        print(f"\n[输出] 已创建: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="AI 日报自动生成器")
    parser.add_argument("--date", help="目标日期 (YYYY-MM-DD)，默认今天")
    parser.add_argument("--collect-only", action="store_true", help="仅采集数据，不调 LLM 生成")
    parser.add_argument("--source", help="仅采集指定数据源 (cursor,claude,codex,ticktick,git)，逗号分隔")
    parser.add_argument("--dry-run", action="store_true", help="试运行，不写入文件")
    parser.add_argument("--output-file", help="指定输出文件路径，默认按日记目录结构生成 YYYY-MM-DD.md")
    parser.add_argument("--force", action="store_true", help="目标文件已存在且非空时仍继续生成")
    args = parser.parse_args()

    config = load_config()
    tz_offset = config.get("timezone_offset_hours", 8)

    target_date = parse_date(args.date) if args.date else get_today(tz_offset)
    print(f"目标日期: {target_date}")
    print(f"输出目录: {config['output_dir']}\n")

    output_dir = config.get("output_dir", "")
    output_path = resolve_output_path(output_dir, target_date, args.output_file)
    if not args.dry_run and not args.force and output_path.exists() and output_path.stat().st_size > 0:
        print(f"[跳过] 目标日报已存在且非空: {output_path}")
        return

    cursor_data, claude_data, codex_data, ticktick_data, git_data = collect_all(
        config, target_date, args.source
    )

    formatted = format_collected_data(
        cursor_data, claude_data, codex_data, ticktick_data, git_data, target_date
    )

    if args.collect_only:
        print("\n" + "=" * 60)
        print(formatted)
        return

    print("\n[生成] 调用配置的生成器生成柳比歇夫日记...")
    diary = generate_diary(formatted, config)

    if diary is None:
        if config.get("fail_on_generation_error", False):
            fail("[生成] 生成失败，未写入文件")
        print("[生成] LLM 生成失败，输出原始采集数据")
        diary = formatted

    print("\n" + "=" * 60)
    print(diary)
    print("=" * 60)

    if not args.dry_run:
        if not output_dir:
            fail("未配置 output_dir")
        if args.output_file:
            output_parent = Path(args.output_file).expanduser().parent
            if not output_parent.exists():
                fail(f"输出文件目录不存在: {output_parent}")
            write_output(diary, output_dir, target_date, args.output_file)
        else:
            if not Path(output_dir).exists():
                fail(f"输出目录不存在: {output_dir}")
            write_output(diary, output_dir, target_date)


if __name__ == "__main__":
    main()
