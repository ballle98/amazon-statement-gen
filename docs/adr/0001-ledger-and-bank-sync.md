# ADR-0001: Ledger source of truth and bank-sync provider

- Status: Proposed
- Date: 2026-11-22
- Deciders: repo owner

## Context

The project has two candidate ledgers and two candidate bank-sync providers:

- **GnuCash SQLite** is the existing accounting workflow; `piecash` can update it in place. It is local, file-based, and requires backups/locking.
- **Cloudflare D1** is the intended home of the Phase 2 web app. It is remote and needs its own ingest and auth.

Keeping both writable would require sync and conflict handling that the project does not need. The plan also names both Plaid and SimpleFIN as possible bank integrations; Plaid requires app registration, OAuth, and production approval, while SimpleFIN is token-based and read-only.

## Decision

Proposed (recommended), pending owner confirmation:

1. **GnuCash remains the ledger of record.** The Phase 2 app is a read-only dashboard fed by a versioned JSON export (and, optionally, bank data). D1 is a mirror, never the authoritative ledger.
2. **SimpleFIN is the bank-sync provider**, unless a concrete requirement rules it out. One provider only.

## Consequences

- Phase 1 is the core product; Phase 2 cannot block it.
- The cloud app needs an export/import contract and a schema, not write access to GnuCash.
- No conflict resolution between two ledgers.
- If the goal later becomes "stop using GnuCash," this ADR must be revisited and Phase 1 becomes a migration tool.

## Alternatives considered

- **D1 as the ledger, GnuCash transitional.** More product work up front; abandons a working accounting workflow.
- **Both ledgers writable.** Rejected: unbounded sync complexity for a personal tool.
- **Plaid.** Rejected for now: integration and approval overhead exceeds the value for one household.
