#!/usr/bin/env python3

"""Input detection and statement parsing for asgen."""

import csv
import glob
import logging
import os
import re
import subprocess
import sys

from collections import defaultdict

OPENING_CLOSING_PATTERN = r'^\s*Opening/Closing Date\s+(\d+)/\d+/(\d+) - \d+/\d+/(\d+)'
DATE_PATTERN = r'^\s*(\d\d)/(\d\d)\s+'
AMAZON_PATTERN = r'(AMZN|Amazon|Prime Video|AMAZON|Kindle|Audible).*'
DESCRIPT_PATTERN = rf'({AMAZON_PATTERN})\s+'
WITHDRAW_PATTERN = r'(-?\d*\.\d\d)'
ORDER_PATTERN = r'\s+Order Number\s+(\S+-\d+-\d+)'


def collect_statement_files(filenames, statement_texts):
    """Return (text filename, output basename) pairs for every statement.

    PDFs are converted with pdftotext; --statement-text files are used as-is.
    """
    statement_files = []
    for text_path in statement_texts:
        for filename in glob.glob(text_path):
            logging.info("statement text file specified: %s", filename)
            base_name = os.path.splitext(filename)[0]
            statement_files.append((filename, base_name))

    for pattern in filenames:
        for filename in glob.glob(pattern):
            logging.debug("file %s", filename)
            if os.path.splitext(filename)[1] == '.pdf':
                logging.info("file is pdf")
                subprocess.run(["pdftotext", "-table", "-enc", "UTF-8", filename], check=False)
                base_name = os.path.splitext(filename)[0]
                statement_files.append((f"{base_name}.txt", base_name))
    return statement_files


def load_csvs(filenames):
    """Classify input CSVs by header and return their contents.

    Returns orders, order_items, has_orders_report, and raw Chase transactions.
    Building the transaction lookup indexes is the matcher's job.
    """
    orders = defaultdict()
    order_items = defaultdict(list)
    has_orders_report = False
    chase_transactions = []

    for pattern in filenames:
        for filename in glob.glob(pattern):
            if os.path.splitext(filename)[1] == '.pdf':
                continue
            with open(filename, 'r', encoding="utf-8-sig") as fd:
                file_buff = fd.read()
                reader = csv.DictReader(file_buff.splitlines())
                headers = reader.fieldnames
                if 'payments' in headers:  # History Reporter plugin orders
                    logging.info("file %s contains History Reporter orders", filename)
                    has_orders_report = True
                    for order in reader:
                        orders[order['order id']] = order
                elif 'item url' in headers:  # History Reporter plugin items
                    logging.info("file %s contains History Reporter items", filename)
                    has_orders_report = True
                    for item in reader:
                        order_items[item['order id']].append(item)
                elif 'Post Date' in headers:  # Chase transactions .csv
                    logging.info("file %s contains credit card Transaction and Post Dates",
                                 filename)
                    chase_transactions = list(reader)
                else:
                    sys.stderr.write(
                        "Error - Invalid csv file " + filename + ".  Not items or shipments\n")
    return orders, order_items, has_orders_report, chase_transactions


def statement_years(statement_files):
    """Collect the years mentioned in each statement's Opening/Closing Date."""
    years = set()
    for pdf_text_file, _ in statement_files:
        try:
            with open(pdf_text_file, encoding="utf-8") as f:
                content = f.read()
                match = re.search(OPENING_CLOSING_PATTERN, content, re.M)
                if match:
                    years.add(int(f'20{match[2]}'))
                    years.add(int(f'20{match[3]}'))
        except FileNotFoundError:
            pass
    logging.info("Years found in statements: %s", sorted(years))
    return years


def parse_statement(content):
    """Extract order rows from already-read statement text.

    Each record has transaction_date, description, withdrawal, order_number,
    and locator keys. Field construction for output is the emitter's job.
    """
    orig_file_buff = content.replace('`', '')
    match = re.search(OPENING_CLOSING_PATTERN, orig_file_buff, re.M)
    if match:
        open_month = match[1]
        open_year = match[2]
        close_year = match[3]
        logging.debug("Opening/Closing %s %s %s", open_month, open_year, close_year)

    # Get rid of page breaks and other lines that carry no order data.
    file_buff = "\n".join(
        line for line in orig_file_buff.split('\n')
            if re.search(
                f'{DATE_PATTERN}{DESCRIPT_PATTERN}{WITHDRAW_PATTERN}|{ORDER_PATTERN}',
                line)
    )
    logging.debug(file_buff)

    records = []
    matches = re.findall(
        rf'{DATE_PATTERN}{DESCRIPT_PATTERN}{WITHDRAW_PATTERN}$\s+{ORDER_PATTERN}',
        file_buff, re.M)
    for match in matches:
        if match[0] == open_month:
            transaction_date = f'{match[0]}/{match[1]}/20{open_year}'
        else:
            transaction_date = f'{match[0]}/{match[1]}/20{close_year}'
        description = match[2]
        locator_match = re.search(rf'^{AMAZON_PATTERN}\*(\w+)', description)
        records.append({
            'transaction_date': transaction_date,
            'description': description,
            'withdrawal': match[4],
            'order_number': match[5],
            'locator': locator_match.group(2) if locator_match else None,
        })
    return records
