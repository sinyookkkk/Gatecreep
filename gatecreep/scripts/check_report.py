"""Check that a human audit report preserves the required evidence boundaries."""

import argparse
import re
import sys
from pathlib import Path


REQUIRED_SECTIONS = (
    "范围与完成状态",
    "公开功能清单",
    "主要发现",
    "非门禁问题",
    "待人工复核",
    "合理门禁摘要",
    "门禁清单",
)
FINDING_FIELDS = (
    "功能",
    "合法任务与成功标准",
    "失败场景",
    "因果链",
    "门禁与保护依据",
    "实际影响",
    "反证检查",
    "不确定性",
    "置信度",
    "调整方向",
)


def sections(text: str) -> dict[str, str]:
    headings = list(re.finditer(r"^##\s+(.+?)\s*$", text, re.MULTILINE))
    return {
        match.group(1): text[match.end() : headings[index + 1].start() if index + 1 < len(headings) else len(text)]
        for index, match in enumerate(headings)
    }


def validate_report(text: str) -> list[str]:
    errors = []
    found = sections(text)
    normalized = {re.sub(r"^\d+\.\s*", "", title): body for title, body in found.items()}
    for title in REQUIRED_SECTIONS:
        if title not in normalized:
            errors.append(f"缺少章节：{title}")

    main = normalized.get("主要发现", "")
    findings = re.split(r"(?=^###\s+)", main, flags=re.MULTILINE)
    for finding in findings:
        if not finding.strip() or finding.strip() == "无":
            continue
        if not finding.startswith("###"):
            continue
        title = finding.splitlines()[0]
        if not re.match(r"###\s+\[(契约冲突|疑似过度门禁)\]", title):
            errors.append(f"主要发现分档无效或混入待复核项：{title}")
        for field in FINDING_FIELDS:
            if not re.search(rf"^-\s*{re.escape(field)}：", finding, re.MULTILINE):
                errors.append(f"主要发现缺少字段：{field}")
        causal = re.search(
            r"^-\s*因果链：([^\n]*(?:\n(?![ \t]*-\s*[^\n：]+：|#{1,6}\s)[^\n]*)*)",
            finding, re.MULTILINE,
        )
        if causal and not re.search(r"\[(静态事实|模型推断)\]", causal.group(1)):
            errors.append("因果链必须标注 [静态事实] 或 [模型推断]")

    scope = normalized.get("范围与完成状态", "")
    coverage = re.search(r"^-\s*覆盖缺口：(.*)$", scope, re.MULTILINE)
    has_gap = bool(coverage and coverage.group(1).strip() not in {"", "无", "None", "N/A"})
    incomplete = bool(re.search(r"^-\s*完成状态：\s*(部分完成|未完成)", scope, re.MULTILINE))
    if (has_gap or incomplete) and re.search(r"项目没有门禁问题|不存在门禁问题|无门禁问题", text):
        errors.append("存在覆盖缺口或扫描未完成时，不得表述为没有门禁问题")
    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args(argv)
    try:
        text = args.report.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"无法读取报告：{exc}", file=sys.stderr)
        return 2
    errors = validate_report(text)
    for error in errors:
        print(error)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
