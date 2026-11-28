# Roadmap

Status: Phase 1 in progress. Phase 2 is gated on [ADR-0001](adr/0001-ledger-and-bank-sync.md).

The canonical task list is the GitHub Phase 1 epic and its linked issues. This file holds the durable scope and the rules that keep the project from turning into a Swiss army knife.

## Constraints

- Deterministic, agent-free logic. No LLM calls or agent loops at runtime.
- No abstraction until there are two real, active callers.
- Every migration issue includes deleting the path it replaces.
- Never commit real statements, account numbers, order data, or credentials.

## Phase 1 — Local engine (GnuCash + Amazon)

Goal: one command takes a Chase Prime Visa statement PDF, enriches it with Amazon order data, and updates the `Description` field of already-imported GnuCash transactions.

End state:
- `asgen.py` is a thin CLI over parse → match → enrich/emit modules.
- GnuCash SQLite is updated in place, idempotently, with backups.
- GnuCash writes only touch `transactions.description`; splits, transfers, amounts, dates, notes, and account assignments are never modified.
- Amazon order data comes from `amazon-orders` 6.x using persisted per-account sessions.
- Chase CSV input remains for transaction and post dates.
- The legacy CSV output remains available only as a transition path until one clean GnuCash statement cycle is recorded.

Non-goals: bank sync, web UI, Cloudflare/D1, creating or rebalancing GnuCash transactions, new input formats without a named failure mode.

Completed:
1. Restore a reproducible baseline (dependencies, API compatibility, install scripts).
2. Add a golden-file harness with synthetic or redacted fixtures.
3. Split the script into parse, match, and emit modules without changing behavior.
4. Spike updating one existing GnuCash transaction description through SQLite.
5. Enrich descriptions for all matched rows, with `--dry-run` and backup/rollback.

Planned:
6. Modernize Amazon auth (persisted sessions, per-account, explicit failure).
7. Decommission History Reporter CSV input and the CSV output emitter.

Deletion rule: keep the CSV emitter behind `--csv` for one full statement cycle after the GnuCash Description path is verified, then remove it.

## Phase 2 — Cloud app (deferred)

Gated by [ADR-0001](adr/0001-ledger-and-bank-sync.md). Candidate scope, not yet approved:

- Read-only cash-flow dashboard.
- Cloudflare Pages/Workers + D1 + Zero Trust Access.
- One bank-sync provider (SimpleFIN recommended over Plaid for personal use).
- Only the endpoints and tables the dashboard actually reads.
