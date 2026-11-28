# amazon-statement-gen

This tool takes a Prime Visa statement PDF, finds Amazon order IDs with `pdftotext`, enriches them with Amazon order data, and either writes a GnuCash-importable CSV or updates the `Description` field of transactions already imported into a GnuCash SQLite book.

GnuCash mode does not create transactions, change amounts, or touch splits/transfers. It only rewrites `transactions.description` for matching existing transactions.

Amazon retired Order History Tool in March 2023, Now use Amazon Order History Reporter Chrome plugin
https://chrome.google.com/webstore/detail/amazon-order-history-repo/mgkilgclilajckgnedgjgnfdokkgnibi

developed here https://github.com/philipmulcahy/azad

When an orders report CSV is not available, the tool can fetch order history directly from Amazon using the [amazon-orders](https://github.com/alexdlaird/amazon-orders) library.

# Requirements

- Python 3.12 or newer
- `pdftotext` from [Xpdf](https://www.xpdfreader.com/download.html) or Poppler on `PATH`

# Installation

Windows (recommended - use installation script):
```
powershell -ExecutionPolicy Bypass -File install.ps1
```
Or manual installation:
```
py -m venv venv
venv\Scripts\activate
py -m pip install -r requirements.txt
```
Or install directly (Windows doesn't restrict system-wide installs):
```
py -m pip install -r requirements.txt
```
Linux (recommended - use installation script):
```
chmod +x install.sh
./install.sh
```
Or manual installation:
```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
Or install system-wide with `--break-system-packages` (not recommended):
```
pip install --break-system-packages -r requirements.txt
```

# Standalone Executable (No Installation Required)

For easy distribution, you can build a standalone executable that includes all dependencies:

Windows:
```
powershell -ExecutionPolicy Bypass -File build.ps1
```

Linux:
```
chmod +x build.sh
./build.sh
```

This creates `dist/asgen.exe` (Windows) or `dist/asgen` (Linux) - a single file (~20MB) that can be run without any Python installation or virtual environment.

# usage 
```
usage: asgen.py [-h] [--verbose] [--amazon-username AMAZON_USERNAME]
                [--amazon-password AMAZON_PASSWORD] [--year YEAR]
                [--statement-text FILE] [--output-dir DIR]
                [--gnucash-book FILE] [--gnucash-account NAME] [--dry-run]
                [--csv]
                [filenames ...]

Amazon Statement Generator

positional arguments:
  filenames

options:
  -h, --help            show this help message and exit
  --verbose, -v
  --amazon-username      Amazon username (repeatable, or set AMAZON_USERNAME env var)
  --amazon-password      Amazon password (repeatable, or set AMAZON_PASSWORD env var)
  --year YEAR            Year to fetch Amazon order history for
  --statement-text FILE  Already-extracted statement text (repeatable); skips pdftotext
  --output-dir DIR       Write generated CSV, error, and report files here
  --gnucash-book FILE    Update descriptions in this GnuCash SQLite book
  --gnucash-account NAME GnuCash account to search (default: Prime Visa 2843)
  --dry-run              With --gnucash-book, report changes without writing
  --csv                  In GnuCash mode, also write legacy CSV output
```

Multiple statement PDFs and multiple Chase transaction CSVs are supported. Each statement PDF produces its own output CSV. The year(s) needed for fetching Amazon order history are automatically extracted from the statement Opening/Closing Date (including both years for January statements that span two years). The `--year` flag overrides auto-detection.

When no orders report CSV is provided, pass Amazon credentials to fetch order history automatically:
```
python asgen.py --amazon-username user@email.com --amazon-password mypass statement.pdf chase.csv
```

Multiple statements and transaction files:
```
python asgen.py --amazon-username user@email.com --amazon-password mypass statement-jan.pdf statement-feb.pdf chase-jan.csv chase-feb.csv
```

Multiple Amazon accounts are supported by repeating the flags (each username paired with the corresponding password):
```
python asgen.py --amazon-username user1@email.com --amazon-password pass1 --amazon-username user2@email.com --amazon-password pass2 statement.pdf chase.csv
```

Or use environment variables for a single account:
```
export AMAZON_USERNAME=user@email.com
export AMAZON_PASSWORD=mypass
export AMAZON_OTP_SECRET_KEY=your-totp-secret   # optional, for 2FA accounts
python asgen.py statement.pdf chase.csv
```

Use `--statement-text FILE` when you already have text extracted from a statement
(repeatable). It bypasses `pdftotext` and writes generated files next to that file,
using its basename, unless `--output-dir` is given. This is the input hook used by
the offline golden-file test.

# GnuCash description updates

Use `--gnucash-book FILE` to update the GnuCash `Description` field of existing
transactions. The default account is `Prime Visa 2843`; override it with
`--gnucash-account NAME`.

```bash
python3 asgen.py --gnucash-book /path/to/book.gnucash \
  --output-dir /path/to/output \
  statement.pdf chase.csv orders.csv
```

Close GnuCash before running this mode. The tool creates a timestamped backup,
stages the SQLite update in a temporary file, and copies the result back only
after a successful commit. It never modifies splits, amounts, dates, notes, or
transfer accounts.

Preview changes without writing:

```bash
python3 asgen.py --gnucash-book /path/to/book.gnucash --dry-run \
  --output-dir /path/to/output \
  statement.pdf chase.csv orders.csv
```

Each statement produces `<basename>-gnucash-description-updates.txt` in the output
directory. The report lists updates, unchanged transactions, and unmatched rows.
Pass `--csv` in GnuCash mode if you also want the legacy CSV output. Without
`--gnucash-book`, the legacy CSV output remains the default.

# Verification

```bash
python3 tests/run_golden.py
```

The harness copies synthetic fixtures to a scratch directory, runs the CLI with
`--statement-text`, diffs the generated CSV against `tests/expected/`, then runs GnuCash
mode against a synthetic SQLite book. It verifies that descriptions are updated, splits
are untouched, and a second run is a no-op. It needs no network, no Amazon credentials,
and no real statement data. When `venv/` exists the harness uses its interpreter so the
installed dependencies are available.

# Reference/Links
- https://www.xpdfreader.com/pdftotext-man.html
- https://www.gnucash.org/
- https://github.com/alexdlaird/amazon-orders
