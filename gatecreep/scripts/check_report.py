"""Check that a human audit report preserves the required evidence boundaries."""

import argparse
import re
import json
import hashlib
import sys
from pathlib import Path, PureWindowsPath


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


def validate_evidence(facts, evidence, target, report, used_evidence=()):
    """Validate references only; causal interpretation remains a reviewer judgment."""
    errors = []
    if not isinstance(facts, dict) or not isinstance(evidence, dict):
        return ["facts and evidence must be objects"]
    if facts.get("schema_version") != 3:
        return ["snapshot verification requires facts schema_version 3; regenerate facts"]
    manifest = facts.get("manifest", [])
    snapshot = hashlib.sha256(json.dumps(manifest, sort_keys=True, ensure_ascii=True).encode()).hexdigest()
    if facts.get("snapshot_id") != snapshot or evidence.get("snapshot_id") != snapshot:
        errors.append("snapshot identity mismatch")
    entries = {item["path"]: item for item in manifest}
    citations = evidence.get("citations")
    steps = evidence.get("steps")
    links = evidence.get("links")
    if not isinstance(citations, list) or not isinstance(steps, list) or not isinstance(links, list):
        return errors + ["citations, steps and links must be lists"]
    if any(not isinstance(item, dict) for group in (citations, steps, links) for item in group):
        return errors + ["evidence entries must be objects"]
    ids = set()
    fact_ids = {item["id"] for key in ("capabilities", "gates", "flows") for item in facts.get(key, []) if "id" in item}
    root = Path(target).resolve()
    if root != Path(facts["root"]).resolve():
        errors.append("target differs from facts root")
    for ref in citations:
        try:
            rid, name = ref["id"], ref["path"]
            if not isinstance(rid, str) or not rid or rid in ids:
                raise ValueError("citation id missing or duplicated")
            ids.add(rid)
            path = Path(name)
            if path.is_absolute() or PureWindowsPath(name).drive or ".." in path.parts or ".." in PureWindowsPath(name).parts:
                raise ValueError("unsafe reference path")
            resolved = (root / path).resolve()
            if not resolved.is_relative_to(root):
                raise ValueError("reference escapes target")
            entry = entries.get(name)
            if not entry or entry.get("status") not in {"read", "parse-error"}:
                raise ValueError("reference missing from readable manifest")
            data = resolved.read_bytes()
            if hashlib.sha256(data).hexdigest() != entry["sha256"]:
                raise ValueError("content changed; reanalyse affected conclusions")
            start, end = ref["start"], ref["end"]
            if type(start) is not int or type(end) is not int or not 1 <= start <= end <= len(data.splitlines()):
                raise ValueError("invalid line range")
            if ref.get("fact_id") and ref["fact_id"] not in fact_ids:
                raise ValueError("unknown fact id")
            if f"[evidence:{rid}]" not in report and rid not in used_evidence:
                raise ValueError("citation is not associated with report")
        except (KeyError, TypeError, ValueError, OSError) as exc:
            errors.append(f"citation: {exc}")
    mentioned = set(re.findall(r"\[evidence:([^\]]+)\]", report))
    if mentioned - ids:
        errors.append("report references unknown evidence ids")
    step_ids = set()
    for step in steps:
        if not isinstance(step.get("id"), str) or step["id"] in step_ids:
            errors.append("step id missing or duplicated")
        step_ids.add(step.get("id"))
        if not step.get("claim") or step.get("provenance") not in {"static-fact", "supplied-runtime-record", "inference"}:
            errors.append("step requires claim and explicit provenance")
        refs = step.get("evidence", [])
        if not isinstance(refs, list) or any(ref not in ids for ref in refs) or (step.get("provenance") != "inference" and not refs):
            errors.append("step evidence missing or unknown")
    for link in links:
        if link.get("from") not in step_ids or link.get("to") not in step_ids or link.get("provenance") not in {"static-fact", "supplied-runtime-record", "inference"}:
            errors.append("link endpoints or provenance invalid")
        refs = link.get("evidence", [])
        if not isinstance(refs, list) or any(ref not in ids for ref in refs) or (link.get("provenance") != "inference" and not refs):
            errors.append("link evidence missing or unknown")
    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--facts", type=Path)
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--target", type=Path)
    args = parser.parse_args(argv)
    try:
        text = args.report.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"无法读取报告：{exc}", file=sys.stderr)
        return 2
    errors = validate_report(text)
    supplied = (args.facts, args.evidence, args.target)
    if any(supplied):
        if not all(supplied):
            errors.append("--facts, --evidence and --target must be supplied together")
        else:
            try:
                errors.extend(validate_evidence(json.loads(args.facts.read_text(encoding="utf-8")), json.loads(args.evidence.read_text(encoding="utf-8")), args.target, text))
            except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
                errors.append(f"invalid evidence input: {exc}")
        print("Validation scope: report structure and source references; semantics/runtime not verified")
    else:
        print("Validation scope: report structure only; source references/semantics/runtime not verified")
    for error in errors:
        print(error)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
