#!/usr/bin/env python3
"""校验芝梦固定版系统架构图 HTML。"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REQUIRED_SUBSTRINGS = [
    ("纸感主题色", "--paper:#F7F2E5"),
    ("赤陶橙强调色", "--accent:#C15F3C"),
    ("页面最大宽度", "max-width:1680px"),
    ("架构图外壳", "diagram-shell"),
    ("架构图容器", "diagram-wrap"),
    ("SVG viewBox", 'viewBox="0 0 1440 1060"'),
    ("Fit 控件", 'data-zoom="fit"'),
    ("100% 控件", 'data-zoom="1"'),
    ("拖拽交互", "pointerdown"),
    ("P0 或等价标签", ">P0<"),
    ("P1 或等价标签", ">P1<"),
    ("P2 或等价标签", ">P2<"),
]

REQUIRED_ANY = [
    ("固定架构图 class", ["zhimeng-fixed-arch", "project-fixed-arch"]),
    ("入口分层", ["用户入口", "入口层", "用户/入口层"]),
    ("控制分层", ["业务控制面", "控制层", "业务/API 控制层"]),
    ("运行时分层", ["智能体运行时", "运行时层", "核心服务/运行时层"]),
    ("数据分层", ["数据与存储", "数据/存储", "数据存储"]),
    ("治理分层", ["部署治理", "治理部署", "部署/治理"]),
    ("演进分层", ["企业演进", "后续演进", "演进层"]),
]

REQUIRED_PATTERNS = [
    ("inline SVG", re.compile(r"<svg\b[^>]*viewBox=\"0 0 1440 1060\"", re.I)),
    ("节点数量 >= 12", re.compile(r"class=\"node\b")),
    ("连线数量 >= 8", re.compile(r"<path class=\"(?:arrow|arrow-soft|event|policy|data|sync|async)[^\"]*\"")),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html", type=Path)
    parser.add_argument("--required-term", action="append", default=[], help="当前项目必须出现的词。")
    parser.add_argument("--forbidden-term", action="append", default=[], help="当前项目禁止出现的词。")
    args = parser.parse_args()

    if not args.html.exists():
        print(f"失败：文件不存在：{args.html}", file=sys.stderr)
        return 2

    text = args.html.read_text(encoding="utf-8")
    failures: list[str] = []

    for label, needle in REQUIRED_SUBSTRINGS:
        if needle not in text:
            failures.append(f"缺少{label}：{needle}")

    for label, options in REQUIRED_ANY:
        if not any(option in text for option in options):
            failures.append(f"缺少{label}：至少需要包含 {', '.join(options)} 之一")

    for label, pattern in REQUIRED_PATTERNS:
        matches = pattern.findall(text)
        if label == "节点数量 >= 12":
            if len(matches) < 12:
                failures.append(f"{label}：当前 {len(matches)}")
        elif label == "连线数量 >= 8":
            if len(matches) < 8:
                failures.append(f"{label}：当前 {len(matches)}")
        elif not matches:
            failures.append(f"缺少结构模式：{label}")

    for term in args.required_term:
        if term not in text:
            failures.append(f"缺少项目必备词：{term}")

    for term in args.forbidden_term:
        if term in text:
            failures.append(f"发现项目禁用词：{term}")

    if failures:
        print("失败")
        for item in failures:
            print(f"- {item}")
        return 1

    node_count = len(REQUIRED_PATTERNS[1][1].findall(text))
    connection_count = len(REQUIRED_PATTERNS[2][1].findall(text))
    print("通过")
    print(f"- 文件：{args.html}")
    print(f"- 节点数量：{node_count}")
    print(f"- 连线数量：{connection_count}")
    print(f"- 已检查必备词：{len(args.required_term)}")
    print(f"- 已检查禁用词：{len(args.forbidden_term)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
