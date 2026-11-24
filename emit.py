#!/usr/bin/env python3

"""CSV and error output for asgen."""

import csv
import logging
import re
import sys

import match
import parse

ACCOUNT = 'Prime Visa'


def build_row(record, transact, orders, order_items):
    """Build the output CSV fields for one matched statement row."""
    order_id = record['order_number']
    row = {
        'Account': ACCOUNT,
        'Transaction Date': record['transaction_date'],
        'Post Date': record['transaction_date'],
        'Description': 'Amazon',
        'Withdrawal': record['withdrawal'],
        'Notes': f"Order Number {order_id}",
    }
    if record['locator']:
        row['Notes'] += f" {record['locator']}"
    if transact:
        row['Post Date'] = transact['Post Date']
        row['Notes'] += f" {transact['Transaction Date']}"

    for item in order_items[order_id]:
        # A quantity > 1 can span multiple shipments; the item total is then
        # the sum of those charges.
        quantity = f"{item['Quantity']}x " if int(item['Quantity']) > 1 else ''
        row['Description'] += f" {quantity}{item['Title']}({item['Item Total']})"
        row['Notes'] += f" {item['Category']}"

    if order_id in orders:
        row['Description'] += f" {orders[order_id]['items']}"
    row['Description'] += f" {order_id}"
    return row


def write_statements(statement_files, orders, order_items, locators, date_amounts):
    """Parse, match, and write one output CSV per statement."""
    dialect = csv.excel
    dialect.lineterminator = '\n'

    for text_path, base_name in statement_files:
        logging.debug("reading %s", text_path)
        with open(text_path, encoding="utf-8") as f:
            content = f.read()
        out_files = {}
        error_file = None
        error_filename = None

        def get_error_file():
            nonlocal error_file, error_filename
            if error_file is None:
                error_filename = f"{base_name}-{ACCOUNT}-error.txt"
                error_file = open(error_filename, 'w', encoding="utf8")
            return error_file

        for record in parse.parse_statement(content):
            transact = match.find_transaction(record, locators, date_amounts)
            date_amount = f"{record['transaction_date']} {record['withdrawal']}"
            order_id = record['order_number']

            if not transact:
                sys.stderr.write(f"Error - transaction missing {date_amount}\n")
                error = get_error_file()
                error.write(f"Missing transaction: {date_amount}\n")
                error.write(f"  Order ID: {order_id}\n")
                error.write(f"  Description: {record['description']}\n")
                for item in order_items.get(order_id, []):
                    error.write(f"  - {item.get('Title', 'Unknown')} "
                                f"(Qty: {item.get('Quantity', '1')}, "
                                f"{item.get('Item Total', 'N/A')})\n")
                if order_id in orders:
                    error.write(f"  Items: {orders[order_id].get('items', 'N/A')}\n")
                error.write("\n")

            if order_id not in order_items and order_id not in orders:
                sys.stderr.write(f"Error - order ID not in order history: {order_id}\n")
                error = get_error_file()
                error.write(f"Order ID not in order history: {order_id}\n")
                error.write(f"  Transaction Date: {record['transaction_date']}\n")
                error.write(f"  Amount: {record['withdrawal']}\n")
                error.write(f"  Description: {record['description']}\n\n")

            row = build_row(record, transact, orders, order_items)

            logging.debug("%s %s %s %s %s %s\n  %s", row['Account'],
                          row['Transaction Date'], row['Post Date'], row['Description'],
                          row['Withdrawal'], row['Notes'], record['description'])
            if row['Account'] in out_files:
                writer = csv.DictWriter(out_files[row['Account']], fieldnames=row.keys(),
                                        dialect=dialect)
            else:
                safe_account = re.sub(r'[^a-zA-Z0-9 ._-]', '', row['Account']).rstrip()
                csvfilename = f"{base_name}-{safe_account}-out.csv"
                logging.debug("%s - file - %s\n", row['Account'], csvfilename)
                csvfile = open(csvfilename, 'w', encoding="utf8")
                out_files[row['Account']] = csvfile
                writer = csv.DictWriter(csvfile, fieldnames=row.keys(), dialect=dialect)
                writer.writeheader()

            writer.writerow(row)

        if error_file is not None:
            error_file.close()
            logging.info("Error file created: %s", error_filename)
