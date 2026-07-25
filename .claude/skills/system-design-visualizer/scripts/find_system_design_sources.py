#!/usr/bin/env python3
"""Find repository-local Markdown files eligible as system-design sources.

Exit 0 when at least one eligible source is found; exit 3 otherwise.
The output is intentionally plain text so a coding agent can surface it verbatim.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

EXCLUDED_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "vendor", "dist", "build", "coverage",
    ".next", ".cache", ".venv", "venv", "target", ".claude", "__pycache__",
    "site-packages",
}
PATH_HINTS = (
    "system-design", "system_design", "system design", "architecture",
    "technical-design", "design-doc", "design_doc",
    "spec", "specs", "rfc", "proposal", "design", "hld", "high-level-design",
    "tech-spec", "technical-spec", "designdoc", "dd",
)
SIGNALS = {
    "requirements": ("requirement", "functional requirement", "non-goal", "non goal", "success criteria"),
    "constraints": ("constraint", "assumption", "latency", "throughput", "scale", "cost", "compliance"),
    "architecture": ("architecture", "component", "service", "datastore", "database", "queue", "topic", "deployment"),
    "interfaces": ("api", "endpoint", "rpc", "event", "contract", "schema", "interface"),
    "data": ("data model", "entity", "ownership", "retention", "pii", "privacy"),
    "operations": ("reliability", "availability", "timeout", "retry", "backpressure", "observability", "performance"),
    "decisions": ("tradeoff", "alternative", "decision", "open question", "rollout"),
}
TITLE_HINTS = (
    "system design", "architecture", "technical design", "design proposal",
    "design document",
    "spec", "specification", "rfc", "proposal", "hld", "high level design",
    "technical specification", "design",
)


def normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower())


def headings(text: str) -> str:
    return "\n".join(line[1:].strip() for line in text.splitlines() if line.lstrip().startswith("#"))


def score_file(path: Path, text: str) -> tuple[int, list[str]]:
    lower = normalized(text)
    path_lower = str(path).lower().replace("_", "-")
    heading_text = normalized(headings(text))
    reasons: list[str] = []
    score = 0

    has_path_hint = any(hint in path_lower for hint in PATH_HINTS)
    has_title_hint = any(hint in heading_text for hint in TITLE_HINTS)
    if has_path_hint:
        score += 2
        reasons.append("design-oriented filename or directory")
    if has_title_hint:
        score += 2
        reasons.append("design-oriented title or heading")

    matched_groups = []
    for group, terms in SIGNALS.items():
        if any(term in lower for term in terms):
            matched_groups.append(group)
    score += len(matched_groups)
    if matched_groups:
        reasons.append("evidence: " + ", ".join(matched_groups))

    # A file qualifies when it has strong substantive content and either a
    # design indicator with corroborating evidence, or overwhelming evidence
    # on its own (escape hatch to avoid false negatives on docs whose name or
    # title does not obviously read as "design").
    named_path = (has_path_hint or has_title_hint) and len(matched_groups) >= 2
    strong_evidence = len(matched_groups) >= 4
    qualifies = score >= 4 and (named_path or strong_evidence)
    if qualifies and strong_evidence and not named_path:
        reasons.append("strong evidence (>=4 groups)")
    return (score if qualifies else 0), reasons


def iter_markdown(root: Path):
    for path in root.rglob("*.md"):
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        if path.is_file():
            yield path


def main() -> int:
    target = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    if not target.exists() or not target.is_dir():
        print(f"ERROR: repository root does not exist or is not a directory: {target}")
        return 2

    candidates: list[tuple[int, Path, list[str]]] = []
    scanned = 0
    for path in iter_markdown(target):
        scanned += 1
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        score, reasons = score_file(path.relative_to(target), text)
        if score:
            candidates.append((score, path, reasons))

    print(f"Scanned {scanned} Markdown file(s) under {target}.")
    if not candidates:
        print("No eligible system-design Markdown source was found.")
        print("Checked for design-oriented filenames/titles plus at least two substantive evidence groups: requirements, constraints, architecture, interfaces, data, operations, or decisions.")
        return 3

    candidates.sort(key=lambda item: (-item[0], str(item[1])))
    print("Eligible system-design source(s):")
    for score, path, reasons in candidates:
        rel = path.relative_to(target)
        print(f"- {rel} [score {score}] — {'; '.join(reasons)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
