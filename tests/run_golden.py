#!/usr/bin/env python3
"""Offline golden checks for statement parsing, matching, and GnuCash updates.

Runs asgen.py against synthetic fixtures in a scratch directory, diffs the
generated CSV with the checked-in expected CSV, then verifies that GnuCash
mode updates only transaction descriptions. No pdftotext or Amazon calls.
"""

import csv
import difflib
import os
import shutil
import sqlite3
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
REPORT = "statement-2026-01-gnucash-description-updates.txt"
INPUTS = (STATEMENT, "chase-transactions.csv", "orders.csv", "items.csv")
BOOK = "test-book.gnucash"
ACCOUNT_GUID = "a" * 32
TRANSACTIONS = (
    ("11111111111111111111111111111111", "2025-12-30 10:59:00",
     "AMZN*AB12CD3", 1499),
    ("22222222222222222222222222222222", "2026-01-05 10:59:00",
     "Amazon Prime Video", 1649),
    ("33333333333333333333333333333333", "2026-01-16 10:59:00",
     "AMZN*XY98ZW7", 751),
)


def run(command, workdir):
    result = subprocess.run(command, cwd=workdir, capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(f"command failed: {' '.join(command)}\n")
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        return None
    return result


def create_gnucash_book(path):
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE accounts (
            guid TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            account_type TEXT NOT NULL,
            commodity_guid TEXT,
            commodity_scu INTEGER NOT NULL,
            non_std_scu INTEGER NOT NULL,
            parent_guid TEXT,
            code TEXT,
            description TEXT,
            hidden INTEGER,
            placeholder INTEGER
        );
        CREATE TABLE transactions (
            guid TEXT PRIMARY KEY,
            currency_guid TEXT NOT NULL,
            num TEXT NOT NULL,
            post_date TEXT,
            enter_date TEXT,
            description TEXT
        );
        CREATE TABLE splits (
            guid TEXT PRIMARY KEY,
            tx_guid TEXT NOT NULL,
            account_guid TEXT NOT NULL,
            memo TEXT NOT NULL,
            action TEXT NOT NULL,
            reconcile_state TEXT NOT NULL,
            reconcile_date TEXT,
            value_num BIGINT NOT NULL,
            value_denom BIGINT NOT NULL,
            quantity_num BIGINT NOT NULL,
            quantity_denom BIGINT NOT NULL,
            lot_guid TEXT
        );
        """
    )
    conn.execute(
        """INSERT INTO accounts VALUES (
            ?, ?, ?, NULL, 100, 0, NULL, '', '', 0, 0)""",
        (ACCOUNT_GUID, "Prime Visa 2843", "CREDIT"))
    for index, (guid, post_date, description, cents) in enumerate(TRANSACTIONS):
        conn.execute(
            "INSERT INTO transactions VALUES (?, ?, '', ?, ?, ?)",
            (guid, "currency", post_date, post_date, description))
        conn.execute(
            """INSERT INTO splits VALUES (
                ?, ?, ?, '', '', 'n', NULL, ?, 100, ?, 100, NULL)""",
            (f"split-{index}-cc", guid, ACCOUNT_GUID, -cents, -cents))
        conn.execute(
            """INSERT INTO splits VALUES (
                ?, ?, ?, '', '', 'n', NULL, ?, 100, ?, 100, NULL)""",
            (f"split-{index}-expense", guid, "expense", cents, cents))
    conn.commit()
    conn.close()


def gnucash_state(path):
    conn = sqlite3.connect(path)
    transactions = conn.execute(
        "SELECT guid, currency_guid, num, post_date, enter_date, description "
        "FROM transactions ORDER BY guid").fetchall()
    splits = conn.execute(
        "SELECT guid, tx_guid, account_guid, memo, action, reconcile_state, "
        "reconcile_date, value_num, value_denom, quantity_num, quantity_denom, "
        "lot_guid FROM splits ORDER BY guid").fetchall()
    conn.close()
    return transactions, splits


def expected_descriptions():
    with open(EXPECTED / OUTPUT, encoding="utf-8", newline="") as f:
        return [row["Description"] for row in csv.DictReader(f)]


def check_gnucash(interpreter, workdir):
    book = workdir / BOOK
    create_gnucash_book(book)
    before_transactions, before_splits = gnucash_state(book)
    base = [interpreter, str(ROOT / "asgen.py"),
            "--statement-text", str(workdir / STATEMENT),
            "--gnucash-book", str(book)]
    inputs = [str(workdir / name) for name in INPUTS[1:]]
    report = workdir / REPORT

    if run(base + ["--dry-run"] + inputs, workdir) is None:
        return 1
    if not report.is_file():
        sys.stderr.write(f"missing report: {REPORT}\n")
        return 1
    first_line = report.read_text(encoding="utf-8").splitlines()[0]
    if first_line != "Dry run 3 GnuCash transaction description(s)":
        sys.stderr.write(f"unexpected dry-run report: {first_line}\n")
        return 1
    if gnucash_state(book) != (before_transactions, before_splits):
        sys.stderr.write("dry run changed the GnuCash book\n")
        return 1

    if run(base + inputs, workdir) is None:
        return 1
    first_line = report.read_text(encoding="utf-8").splitlines()[0]
    if first_line != "Updated 3 GnuCash transaction description(s)":
        sys.stderr.write(f"unexpected update report: {first_line}\n")
        return 1

    after_transactions, after_splits = gnucash_state(book)
    if after_splits != before_splits:
        sys.stderr.write("GnuCash splits changed\n")
        return 1
    actual_descriptions = [row[5] for row in after_transactions]
    if actual_descriptions != expected_descriptions():
        sys.stderr.write("GnuCash descriptions do not match expected CSV\n")
        return 1
    for before, after in zip(before_transactions, after_transactions):
        if before[:5] != after[:5]:
            sys.stderr.write("non-description transaction fields changed\n")
            return 1

    if run(base + inputs, workdir) is None:
        return 1
    first_line = report.read_text(encoding="utf-8").splitlines()[0]
    if first_line != "Updated 0 GnuCash transaction description(s)":
        sys.stderr.write(f"second run was not a no-op: {first_line}\n")
        return 1

    print("gnucash OK: descriptions updated, splits untouched, rerun is a no-op")
    return 0


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
        result = run(command, workdir)
        if result is None:
            return 1

        error_path = workdir / ERROR
        if error_path.exists():
            sys.stderr.write(f"unexpected unmatched orders:\n{error_path.read_text()}")
            return 1

        actual_path = workdir / OUTPUT
        if not actual_path.exists():
            sys.stderr.write(f"missing output file: {OUTPUT}\n")
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

        status = check_gnucash(interpreter, workdir)
        if status != 0:
            return status
    return 0


if __name__ == "__main__":
    sys.exit(main())
