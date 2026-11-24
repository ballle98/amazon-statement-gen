#!/usr/bin/env python3
"""Offline golden-file check for statement parsing and matching.

Runs asgen.py against synthetic fixtures in a scratch directory and diffs the
generated CSV with the checked-in expected CSV. No pdftotext or Amazon calls.
"""

import difflib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTS = Path(__file__).resolve().parent
FIXTURES = TESTS / "fixtures"
EXPECTED = TESTS / "expected"
STATEMENT = "statement-2026-01.txt"
OUTPUT = "statement-2026-01-Prime Visa-out.csv"
ERROR = "statement-2026-01-Prime Visa-error.txt"
INPUTS = (STATEMENT, "chase-transactions.csv", "orders.csv", "items.csv")


def main():
    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)
        for name in INPUTS:
            shutil.copy(FIXTURES / name, workdir / name)

        venv_python = (ROOT / "venv/Scripts/python.exe" if os.name == "nt"
                       else ROOT / "venv/bin/python3")
        interpreter = str(venv_python) if venv_python.is_file() else sys.executable
        command = [interpreter, str(ROOT / "asgen.py"),
                   "--statement-text", str(workdir / STATEMENT)]
        command += [str(workdir / name) for name in INPUTS[1:]]
        result = subprocess.run(command, cwd=workdir, capture_output=True, text=True)

        if result.returncode != 0:
            sys.stderr.write(f"asgen.py exited {result.returncode}\n")
            sys.stderr.write(result.stdout)
            sys.stderr.write(result.stderr)
            return 1

        error_path = workdir / ERROR
        if error_path.exists():
            sys.stderr.write(f"unexpected unmatched orders:\n{error_path.read_text()}")
            return 1

        actual_path = workdir / OUTPUT
        if not actual_path.exists():
            sys.stderr.write(f"missing output file: {OUTPUT}\n{result.stderr}")
            return 1

        expected = (EXPECTED / OUTPUT).read_text(encoding="utf-8").splitlines()
        actual = actual_path.read_text(encoding="utf-8").splitlines()
        if actual != expected:
            diff = difflib.unified_diff(expected, actual,
                                        fromfile="expected", tofile="actual",
                                        lineterm="")
            sys.stderr.write("\n".join(diff) + "\n")
            return 1

    print(f"golden OK: {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
