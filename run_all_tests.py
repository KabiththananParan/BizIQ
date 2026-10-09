"""Comprehensive Test Suite Runner for BizIQ Multi-Agent Platform.
Runs all test suites across the 4 individual agents and the integrated gateway.
"""

import os
import subprocess
import sys
from pathlib import Path

# Fix Windows console UTF-8 encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).resolve().parent
PYTHON_EXE = ROOT_DIR / "security-agent" / "venv" / "Scripts" / "python.exe"
if not PYTHON_EXE.exists():
    PYTHON_EXE = Path(sys.executable)

SUITES = [
    ("Integrated System & Contracts", ROOT_DIR, ["-m", "pytest", "tests"]),
    ("Security & Compliance Agent", ROOT_DIR / "security-agent", ["-m", "pytest", "tests"]),
    ("Information Retrieval (IR) Agent", ROOT_DIR / "ir-agent", ["-m", "pytest", "tests"]),
    ("LLM Insight Agent", ROOT_DIR / "insight_agent", ["-m", "pytest", "tests"]),
    ("NLP Query Agent", ROOT_DIR / "nlp-agent", ["-m", "pytest", "tests"]),
]

def main():
    print("=" * 70)
    print("BizIQ Multi-Agent Platform -- Running All Test Suites")
    print("=" * 70)

    total_suites = len(SUITES)
    passed_suites = 0
    failures = []

    for name, cwd, args in SUITES:
        print(f"\n>> Running suite: {name} (cwd: {cwd.name})...")
        cmd = [str(PYTHON_EXE)] + args
        res = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace")
        if res.returncode == 0:
            print(f"  [PASS] {name}")
            passed_suites += 1
            for line in res.stdout.strip().split("\n"):
                if "passed" in line and ("warning" in line or "in " in line):
                    print(f"         {line.strip()}")
        else:
            print(f"  [FAIL] {name} (exit code {res.returncode})")
            print(res.stdout)
            print(res.stderr)
            failures.append(name)

    print("\n" + "=" * 70)
    print(f"Test Run Results: {passed_suites}/{total_suites} suites passed.")
    if failures:
        print(f"Failed suites: {', '.join(failures)}")
        print("=" * 70)
        sys.exit(1)
    else:
        print("ALL 140+ TESTS PASSED SUCCESSFULLY!")
        print("=" * 70)
        sys.exit(0)

if __name__ == "__main__":
    main()
