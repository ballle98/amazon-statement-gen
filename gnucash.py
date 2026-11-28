#!/usr/bin/env python3

"""Update descriptions on existing GnuCash transactions.

This module deliberately does not create transactions or touch splits.  The
only supported write is `transactions.description` for a transaction that was
already imported from Chase.
"""

import datetime
import logging
import os
import re
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

import emit
import match
import parse

ACCOUNT_NAME = 'Prime Visa 2843'
DESCRIPTION_COLUMN_LIMIT = 2048
AMAZON_DESCRIPTION_PATTERN = (
    r'^(AMZN|Amazon|Prime Video|AMAZON|Kindle|Audible)')
ORDER_ID_PATTERN = re.compile(r'\d{3}-\d{7}-\d{7}')
LOCATOR_PATTERN = re.compile(r'\*([A-Z0-9]+)\b', re.IGNORECASE)


def _amazon_description(description):
    """Return True when a GnuCash description still looks freshly imported."""
    return bool(re.search(AMAZON_DESCRIPTION_PATTERN, description or '', re.I))


def _generic_description(description):
    """Return True when it is safe to replace an imported Amazon description."""
    if not _amazon_description(description):
        return False
    lowered = (description or '').lower()
    if 'order number' in lowered:
        return False
    return ORDER_ID_PATTERN.search(description or '') is None


def _date_iso(mmddyyyy):
    """Convert MM/DD/YYYY from the Chase CSV to YYYY-MM-DD."""
    return datetime.datetime.strptime(mmddyyyy, '%m/%d/%Y').date().isoformat()


def _amount_cents(amount):
    """Convert a dollar string into integer cents for exact comparison."""
    return int(round(float(amount) * 100))


def _split_cents(value_num, value_denom):
    """Convert a GnuCash rational split value into integer cents."""
    return int(round((value_num / value_denom) * 100))


def account_guid(conn, account_name=ACCOUNT_NAME):
    """Return the GUID for a named GnuCash account."""
    row = conn.execute(
        'SELECT guid FROM accounts WHERE name = ?', (account_name,)).fetchone()
    if row is None:
        raise ValueError(f'GnuCash account not found: {account_name}')
    return row[0]


def build_index(conn, guid):
    """Build locator and post-date+amount indexes for one account, once."""
    locators = {}
    date_amounts = {}
    rows = conn.execute(
        '''
        SELECT DISTINCT t.guid, t.description, t.post_date,
                        s.value_num, s.value_denom
          FROM transactions t
          JOIN splits s ON s.tx_guid = t.guid
         WHERE s.account_guid = ?
        ''',
        (guid,)).fetchall()
    for row in rows:
        description = row[1] or ''
        if not _amazon_description(description):
            continue
        candidate = {
            'guid': row[0],
            'description': description,
            'post_date': row[2],
            'cents': abs(_split_cents(row[3], row[4])),
        }
        locator_match = LOCATOR_PATTERN.search(description)
        if locator_match:
            key = locator_match.group(1).upper()
            locators.setdefault(key, []).append(candidate)
        key = (str(row[2])[:10], candidate['cents'])
        date_amounts.setdefault(key, []).append(candidate)
    return locators, date_amounts


def _candidate_rows(index, record, transact):
    """Return (candidate, match_method) for one statement record."""
    locators, date_amounts = index
    amount = _amount_cents(record['withdrawal'])
    locator = record.get('locator')

    if locator:
        rows = [row for row in locators.get(locator.upper(), [])
                if row['cents'] == amount]
        if len(rows) == 1:
            return rows[0], f'locator {locator}'
        if len(rows) > 1:
            return None, f'ambiguous locator {locator} ({len(rows)} matches)'

    if transact and transact.get('Post Date'):
        post_date = _date_iso(transact['Post Date'])
        rows = [row for row in date_amounts.get((post_date, amount), [])
                if _amazon_description(row['description'])]
        if len(rows) == 1:
            return rows[0], f'post date {post_date} + amount {amount / 100:.2f}'
        if len(rows) > 1:
            return None, (f'ambiguous post date {post_date} + amount '
                          f'{amount / 100:.2f} ({len(rows)} matches)')

    reason = f'locator {locator} and amount {amount / 100:.2f}' if locator else \
        f'amount {amount / 100:.2f}'
    return None, f'no GnuCash transaction matched {reason}'


def build_description(record, transact, orders, order_items):
    """Use the CSV Description field as the new GnuCash Description."""
    return emit.build_row(record, transact, orders, order_items)['Description']


def backup_book(book_path):
    """Create a timestamped backup beside the book and return its path."""
    source = Path(book_path)
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    backup = source.with_name(
        f'{source.stem}-backup-{stamp}{source.suffix}')
    shutil.copy2(source, backup)
    return str(backup)


def _stage_book(book_path):
    """Copy the book to a local temp file for reliable SQLite commits."""
    fd, staged_path = tempfile.mkstemp(prefix='asgen-gnucash-', suffix='.gnucash')
    os.close(fd)
    shutil.copy2(book_path, staged_path)
    return staged_path


def _connect(book_path, dry_run):
    """Open the book read-only for dry runs, read/write otherwise."""
    if dry_run:
        uri = Path(book_path).resolve().as_uri() + '?mode=ro'
        return sqlite3.connect(uri, uri=True, timeout=30)
    return sqlite3.connect(book_path, timeout=30)


def _write_report(base_name, plans, errors, dry_run):
    """Write a readable report of every planned or applied change."""
    report_path = f'{base_name}-gnucash-description-updates.txt'
    mode = 'Dry run' if dry_run else 'Updated'
    updates = [plan for plan in plans if plan[0] == 'update']
    with open(report_path, 'w', encoding='utf-8') as report:
        report.write(f'{mode} {len(updates)} GnuCash transaction description(s)\n\n')
        for action, guid, description, detail in plans:
            report.write(f'{action}: {guid} [{detail}]\n')
            report.write(f'  {description}\n')
        if errors:
            report.write(f'\n{len(errors)} problem(s)\n\n')
            for error in errors:
                report.write(f'{error}\n')
    logging.info('GnuCash update report: %s', report_path)
    return report_path


def enrich_statements(statement_files, orders, order_items, locators,
                      date_amounts, book_path, account_name=ACCOUNT_NAME,
                      dry_run=False):
    """Update existing GnuCash transaction descriptions from statement rows."""
    staged = None
    work_path = book_path
    if not dry_run:
        backup = backup_book(book_path)
        logging.info('GnuCash backup created: %s', backup)
        staged = _stage_book(book_path)
        work_path = staged

    conn = _connect(work_path, dry_run)
    success = False
    total_updates = 0
    try:
        guid = account_guid(conn, account_name)
        index = build_index(conn, guid)
        if not dry_run:
            conn.execute('BEGIN IMMEDIATE')

        for text_path, base_name in statement_files:
            logging.debug('reading %s for GnuCash description updates', text_path)
            with open(text_path, encoding='utf-8') as f:
                content = f.read()

            plans = []
            errors = []
            for record in parse.parse_statement(content):
                transact = match.find_transaction(record, locators, date_amounts)
                candidate, detail = _candidate_rows(index, record, transact)
                if candidate is None:
                    message = (f'No GnuCash match: order {record["order_number"]}, '
                               f'{detail}')
                    logging.warning(message)
                    sys.stderr.write(f'Error - {message}\n')
                    errors.append(message)
                    continue

                description = build_description(
                    record, transact, orders, order_items)[:DESCRIPTION_COLUMN_LIMIT]
                current = candidate['description']
                if current == description:
                    action = 'unchanged'
                elif _generic_description(current):
                    action = 'update'
                    plans.append((action, candidate['guid'], description, detail))
                else:
                    message = (f'Description conflict: {candidate["guid"]} currently '
                               f'{current!r}; refusing to overwrite')
                    logging.warning(message)
                    sys.stderr.write(f'Error - {message}\n')
                    errors.append(message)
                    continue

                if action == 'unchanged':
                    plans.append((action, candidate['guid'], description, detail))

            _write_report(base_name, plans, errors, dry_run)

            if not dry_run:
                updates = [plan for plan in plans if plan[0] == 'update']
                if updates:
                    for _, tx_guid, description, _ in updates:
                        cursor = conn.execute(
                            'UPDATE transactions SET description = ? WHERE guid = ?',
                            (description, tx_guid))
                        if cursor.rowcount != 1:
                            raise RuntimeError(
                                f'failed to update transaction {tx_guid}')
                    total_updates += len(updates)
                    logging.info('Staged %d GnuCash description(s)', len(updates))
                conn.commit()

        success = True
    except Exception:
        if not dry_run:
            conn.rollback()
        raise
    finally:
        conn.close()
        if staged is not None:
            if success and total_updates:
                shutil.copy2(staged, book_path)
                logging.info('Copied %d GnuCash description update(s) into %s',
                             total_updates, book_path)
            os.unlink(staged)
