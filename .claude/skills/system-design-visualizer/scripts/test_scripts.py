#!/usr/bin/env python3
"""Self-contained stdlib smoke test for find_system_design_sources.py.

Runs the finder against temporary repositories via subprocess and asserts on
its exit codes and output. No third-party dependencies (no pytest).

Run with: python3 scripts/test_scripts.py
Exits 0 when every case passes, nonzero otherwise.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

FINDER = Path(__file__).resolve().parent / "find_system_design_sources.py"


def run_finder(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(FINDER), str(root)],
        capture_output=True,
        text=True,
    )


def write(root: Path, rel: str, content: str) -> None:
    dest = root / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")


RICH_DESIGN = """# Jobs System Design

## Functional Requirements
The jobs service must schedule work and meet its success criteria.

## Architecture
Components: a scheduler service, a database datastore, and a queue.

## API
Endpoints expose an RPC contract and event schema.

## Reliability
We target high availability with retry, timeout, and backpressure and
observability for performance.
"""

SPEC_DOC = """# Payment Specification

## Requirements
Functional requirement: process payments; non-goal: refunds.

## Architecture
A payment service backed by a database and a queue topic.

## Interfaces
Public API endpoints with an rpc contract and schema.

## Operations
Reliability and availability with retry, timeout, and observability.
"""

MARKETING = """# Awesome Product

Welcome! Our product is the best. Sign up today and love it.
We are passionate about delighting customers with beautiful experiences.
"""


def check(name: str, got_code: int, want_code: int, listed_ok: bool = True) -> bool:
    ok = (got_code == want_code) and listed_ok
    status = "PASS" if ok else "FAIL"
    detail = f"exit {got_code} (want {want_code})"
    if not listed_ok:
        detail += " [expected file not listed]"
    print(f"[{status}] {name}: {detail}")
    return ok


def main() -> int:
    results: list[bool] = []

    # Case 1: rich design doc -> exit 0, file listed.
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        write(root, "docs/system-design/jobs.md", RICH_DESIGN)
        proc = run_finder(root)
        listed = "docs/system-design/jobs.md" in proc.stdout
        results.append(check("rich design doc", proc.returncode, 0, listed))

    # Case 2: spec (escape hatch / new hints) -> exit 0, file listed.
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        write(root, "docs/specs/payment.md", SPEC_DOC)
        proc = run_finder(root)
        listed = "docs/specs/payment.md" in proc.stdout
        results.append(check("spec doc", proc.returncode, 0, listed))

    # Case 3: marketing README -> exit 3 (not eligible).
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        write(root, "README.md", MARKETING)
        proc = run_finder(root)
        results.append(check("marketing README", proc.returncode, 3))

    # Case 4: empty dir -> exit 3.
    with tempfile.TemporaryDirectory() as d:
        proc = run_finder(Path(d))
        results.append(check("empty directory", proc.returncode, 3))

    passed = sum(results)
    total = len(results)
    if passed == total:
        print(f"ALL PASS ({passed}/{total})")
        return 0
    print(f"FAILURES: {total - passed} of {total} cases failed")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
