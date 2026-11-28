# AGENTS.md

## What this is

`asgen.py` is the CLI entrypoint; `parse.py` handles input detection and statement parsing, `match.py` looks up Chase transactions, `emit.py` builds rows and writes CSV/error files, and `gnucash.py` updates descriptions on existing GnuCash transactions. Amazon fetching stays in the CLI. The default output is still a GnuCash-importable CSV; `--gnucash-book` switches to direct SQLite description updates. There is no package layout, CI, linter, or formatter config, and the golden harness is the only test.

## Run and verify

```bash
python3 asgen.py --help
python3 asgen.py -vv statement.pdf [orders.csv] [items.csv] [transactions.csv]
python3 asgen.py --gnucash-book book.gnucash --dry-run --output-dir out/ statement.pdf chase.csv orders.csv
```

- **Python 3.12+ is required** — the CLI and `emit.py` use PEP 701 nested same-quote f-strings, and `main()` exits on older versions. The install scripts check this up front.
- `pdftotext` (Xpdf or Poppler) must be on `PATH`.
- The only test is `python3 tests/run_golden.py`: synthetic fixtures in `tests/fixtures/`, checked-in expected CSV in `tests/expected/`, plus a synthetic GnuCash SQLite book. It runs fully offline (no Amazon calls, no `pdftotext`) and uses `venv/bin/python3` when `venv/` exists. Also run `python3 -m py_compile asgen.py parse.py match.py emit.py gnucash.py`, `--help`, and a real statement run when changing matching or GnuCash matching. Do not claim tests pass without running them.
- `-v` enables INFO, `-vv` enables DEBUG logging.

## Install and build traps

- `install.sh` / `install.ps1` both install from `requirements.txt`. A new dependency must be added to `requirements.txt` and the README.
- `requirements.txt` pins `amazon-orders>=6.0,<7`. `asgen.py` uses `get_orders()`; `get_order_history()` was removed in 5.0 and must not be reintroduced.
- `amazoncaptcha` is obsolete (amazon-orders 6 / amazon-auth 1.1 removed legacy image-captcha auto-solve) and has been removed from the scripts. Do not add it back as an auth fix.
- `build.sh` / `build.ps1` run `install` if `venv/` is missing, then `pyinstaller --onefile --name asgen asgen.py` (Windows: `py -m PyInstaller`) and write `dist/asgen[.exe]`. They do not pass `asgen.spec`; PyInstaller regenerates it.

## Data flow

1. `parse.collect_statement_files` globs `filenames`; `.pdf` inputs run `pdftotext -table -enc UTF-8 <file>`, which writes `<file>.txt` beside the PDF. `--statement-text FILE` (repeatable) reads already-extracted text instead, so the golden test needs no PDF or `pdftotext`. `parse.load_csvs` classifies other files by header: `payments` = History Reporter orders, `item url` = History Reporter items, `Post Date` = Chase transactions.
2. Amazon fetching runs only when no History Reporter CSV was seen. Years come from the statement's `Opening/Closing Date` (both years for a January statement); `--year` overrides. Repeated `--amazon-username`/`--amazon-password` pairs are zipped and must be equal length, or fetching is skipped.
3. `parse.parse_statement` filters statement text by regex; `match.find_transaction` matches each `Order Number` row to a Chase transaction by Amazon locator (`AMZN*XXXX`) first, then by transaction date + amount. `match.build_indexes` owns the Chase lookup tables and negates `Amount` on read.
4. Default mode calls `emit.write_statements`, writing beside each statement (PDF or `--statement-text` file) as `<basename>-Prime Visa-out.csv`; unmatched items go to `<basename>-Prime Visa-error.txt`. The `Account` value is hardcoded to `Prime Visa`. `--output-dir` redirects generated files.
5. With `--gnucash-book`, `gnucash.enrich_statements` builds locator and post-date+amount indexes from the `Prime Visa 2843` account, then updates only `transactions.description` for matched rows. It creates a timestamped backup, stages SQLite writes in a local temp file, and copies the staged book back only after a successful commit. Unmatched/ambiguous/conflict rows go to `<basename>-gnucash-description-updates.txt`.

## Editing gotchas

- Chase CSV `Amount` is negated on read to match the positive PDF `Withdrawal`. Keep the two signs consistent when touching matching.
- A missing `pdftotext` binary crashes at the `subprocess.run` call; a run that yields no `.txt` is swallowed by the later `except FileNotFoundError`. Bad PDFs can silently produce no years and no output.
- Parsing assumes the Chase Prime Visa layout: `MM/DD` dates, 2-digit years interpreted as 20xx, and a literal `Order Number`. Re-run against a real statement after regex edits.
- Preserve the stderr messages and `*-error.txt` reporting for unmatched orders/transactions when refactoring.
- GnuCash mode must never create transactions or modify splits, amounts, dates, notes, or transfer accounts. The only write is `transactions.description`.
- SQLite commits on Windows-mounted paths such as `/mnt/o` can fail with `database is locked`; `gnucash.py` stages writes in a local temp file and copies back after commit. Keep that behavior.
- An already-enriched GnuCash description is a conflict, not an overwrite target; generic imported Amazon descriptions are safe to replace.
- Statement `Order Number` lines may have no leading whitespace in real `pdftotext` output; keep `ORDER_PATTERN` tolerant of both.
- Relative paths resolve against the current directory. Without `--output-dir`, output lands next to the input PDF, not necessarily in the CWD.

## Commits

- Lowercase imperative subject; body explains behavior or environment assumptions.
- Required trailers:
  `Assisted-by: <Tool>:<Model>` and `Signed-off-by: <Name> <email>`

## OpenCode

- `.opencode/opencode.json` enables the `opencode-planner` plugin. Plan files are per-session scratch in `.opencode/plans/*.md`, which is gitignored; they describe proposed work (GnuCash/`piecash`, Cloudflare app), not implemented behavior.
- `docs/roadmap.md` is the durable scope. The GitHub Phase 1 epic and its linked issues are the canonical task list; keep both in sync.
