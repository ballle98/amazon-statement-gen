# AGENTS.md

## What this is

`asgen.py` is a single-file Python CLI (all logic in `main()`). It combines Chase Prime Visa statement PDFs with Amazon order data and emits GnuCash-importable CSVs. There is no package layout, test suite, CI, linter, or formatter config.

## Run and verify

```bash
python3 asgen.py --help
python3 asgen.py -vv statement.pdf [orders.csv] [items.csv] [transactions.csv]
```

- **Python 3.12+ is required** — `asgen.py` uses PEP 701 nested same-quote f-strings, and `main()` exits on older versions. The install scripts check this up front.
- `pdftotext` (Xpdf or Poppler) must be on `PATH`.
- No tests exist. Verify changes with `python3 -m py_compile asgen.py`, `--help`, and a real statement run. Do not claim tests pass.
- `-v` enables INFO, `-vv` enables DEBUG logging.

## Install and build traps

- `install.sh` / `install.ps1` both install from `requirements.txt`. A new dependency must be added to `requirements.txt` and the README.
- `requirements.txt` pins `amazon-orders>=6.0,<7`. `asgen.py` uses `get_orders()`; `get_order_history()` was removed in 5.0 and must not be reintroduced.
- `amazoncaptcha` is obsolete (amazon-orders 6 / amazon-auth 1.1 removed legacy image-captcha auto-solve) and has been removed from the scripts. Do not add it back as an auth fix.
- `build.sh` / `build.ps1` run `install` if `venv/` is missing, then `pyinstaller --onefile --name asgen asgen.py` (Windows: `py -m PyInstaller`) and write `dist/asgen[.exe]`. They do not pass `asgen.spec`; PyInstaller regenerates it.

## Data flow

1. `filenames` are globbed. `.pdf` inputs run `pdftotext -table -enc UTF-8 <file>`, which writes `<file>.txt` beside the PDF. Other files are classified by CSV header: `payments` = History Reporter orders, `item url` = History Reporter items, `Post Date` = Chase transactions.
2. Amazon fetching runs only when no History Reporter CSV was seen. Years come from the statement's `Opening/Closing Date` (both years for a January statement); `--year` overrides. Repeated `--amazon-username`/`--amazon-password` pairs are zipped and must be equal length, or fetching is skipped.
3. Statement text is filtered by regex; each `Order Number` row is matched to a Chase transaction by Amazon locator (`AMZN*XXXX`) first, then by transaction date + amount.
4. Output is written beside each PDF as `<pdf-basename>-Prime Visa-out.csv`; unmatched items go to `<pdf-basename>-Prime Visa-error.txt`. The `Account` value is hardcoded to `Prime Visa`.

## Editing gotchas

- Chase CSV `Amount` is negated on read to match the positive PDF `Withdrawal`. Keep the two signs consistent when touching matching.
- A missing `pdftotext` binary crashes at the `subprocess.run` call; a run that yields no `.txt` is swallowed by the later `except FileNotFoundError`. Bad PDFs can silently produce no years and no output.
- Parsing assumes the Chase Prime Visa layout: `MM/DD` dates, 2-digit years interpreted as 20xx, and a literal `Order Number`. Re-run against a real statement after regex edits.
- Preserve the stderr messages and `*-error.txt` reporting for unmatched orders/transactions when refactoring.
- Relative paths resolve against the current directory. Output lands next to the input PDF, not necessarily in the CWD.

## OpenCode

- `.opencode/opencode.json` enables the `opencode-planner` plugin. Design specs live in `.opencode/plans/*.md`; they describe proposed work (GnuCash/`piecash`, Cloudflare app), not implemented behavior.
- `docs/roadmap.md` is the durable scope. The GitHub Phase 1 epic and its linked issues are the canonical task list; keep both in sync.
