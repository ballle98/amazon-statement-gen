#!/usr/bin/env python
# encoding: utf-8
'''
asgen -- Amazon Statement Generator

asgen statements from a Amazon Prime Visa card and combines them with order
history from Amazon

Download Xpdf command line tools from https://www.xpdfreader.com/download.html

Amazon retired Order History Tool in March 2023, Now use Amazon Order History
Reporter Chrome plugin
https://chrome.google.com/webstore/detail/amazon-order-history-repo/mgkilgclilajckgnedgjgnfdokkgnibi

@author:     lee Ballard

@copyright:  2016. All rights reserved.

@license:    license

@contact:    ballle98@gmail.com
@deffield    updated: Updated
'''

import sys
import logging
import csv
from collections import defaultdict
import argparse
import os
import glob
import re
import subprocess


def main():
    """
    The main function of the program. It takes command line arguments and processes them.

    Parameters:
        None

    Returns:
        None
    """
    parser = argparse.ArgumentParser(description='Amazon Statement Generator')
    parser.add_argument('--verbose', '-v', action='count')
    parser.add_argument('filenames', nargs='*')

    args = parser.parse_args()

    if args.verbose:
        if args.verbose == 1:
            logging.basicConfig(level=logging.INFO)
        elif args.verbose > 1:
            logging.basicConfig(level=logging.DEBUG)

        logging.info("verbosity level = %d", args.verbose)

    orders = defaultdict()
    order_history = []
    order_items = defaultdict(list)
    chase_transactions = []
    pdf_text_files = []
    locator_transactions = defaultdict()
    date_amount_transactions = defaultdict()
    glob_file_names = []
    chase_transactions_filename = ""

    for item in args.filenames:
        glob_file_names += glob.glob(item)
    for filename in glob_file_names:
        logging.debug("file %s", filename)
        if os.path.splitext(filename)[1] == '.pdf':
            logging.info("file is pdf")
            subprocess.run(["pdftotext", "-table", "-enc", "UTF-8", filename], check=False)
            pdf_text_files.append(f"{os.path.splitext(filename)[0]}.txt")
            chase_transactions_filename = os.path.splitext(filename)[0]
        else:
            with open(filename, 'r', encoding="utf-8-sig") as fd:
                file_buff = fd.read()
                reader = csv.DictReader(file_buff.splitlines())
                headers = reader.fieldnames
                if 'payments' in headers:  # History Reporter plugin orders
                    logging.info("file %s contains History Reporter orders", filename)
                    order_history = reader
                    for order in order_history:
                        orders[order['order id']] = order
                elif 'item url' in headers:  # History Reporter plugin items
                    logging.info("file %s contains History Reporter items", filename)
                    items = reader
                    for item in items:
                        order_items[item['order id']].append(item)
                elif 'Post Date' in headers:  # Chase transactions .csv
                    logging.info("file %s contains credit card Transaction and Post Dates",
                                 filename)
                    chase_transactions = reader
                    for transact in chase_transactions:
                        match = re.search(r'^(AMZN|Amazon\.com|Prime Video|AMAZON).*',
                                          transact['Description'])
                        if match:
                            match2 = re.search(r'^(AMZN|Amazon\.com|Prime Video|AMAZON).*\*(\w+)',
                                               transact['Description'])
                            transact['Amount'] = str(-float(transact['Amount']))
                            if match2:
                                amzn_locator = match2.group(2)
                                logging.info("amznLocator %s %s %s %s %s", amzn_locator,
                                             transact['Transaction Date'], transact['Post Date'],
                                             transact['Description'], transact['Amount'])
                                locator_transactions[amzn_locator] = transact
                            else:
                                logging.info("date amount %s %s %s",
                                             f"{transact['Transaction Date']} {transact['Amount']}",
                                             transact['Post Date'], transact['Description'])
                                date_amount = f"{transact['Transaction Date']} {transact['Amount']}"
                                date_amount_transactions[date_amount] = transact
                        else:
                            continue
                else:
                    sys.stderr.write(
                        "Error - Invalid csv file " + filename + ".  Not items or shipments\n")

    out_files = {}
    dialect = csv.excel
    dialect.lineterminator = '\n'

    for pdf_text_file in pdf_text_files:
        logging.debug("reading %s", pdf_text_file)
        with open(pdf_text_file, encoding="utf-8") as f:
            orig_file_buff = f.read().replace('`', '')
            match = re.search(r'^\s*Opening/Closing Date\s+(\d+)/\d+/(\d+) - \d+/\d+/(\d+)',
                              orig_file_buff, re.M)  # @UndefinedVariable
            if match:
                open_month = match[1]
                open_year = match[2]
                close_year = match[3]
                logging.debug("Opening/Closing %s %s %s", open_month, open_year, close_year)
            # Clean up the filebuff to
            file_buff = ""

            # regex patterns
            date_pattern = r'^\s*(\d\d)/(\d\d)\s+'
            amazon_pattern = r'(AMZN|Amazon|Prime Video|AMAZON|Kindle|Audible).*'
            descript_pattern = rf'({amazon_pattern})\s+'
            withdraw_pattern = r'(-?\d*\.\d\d)'
            order_pattern = r'\s+Order Number\s+(\S+-\d+-\d+)'

            # get rid of any extra stuff like page breaks etc.
            file_buff = "\n".join(
                line for line in orig_file_buff.split('\n')
                    if re.search(
                        f'{date_pattern}{descript_pattern}{withdraw_pattern}|{order_pattern}',
                        line)
            )

            logging.debug(file_buff)
            matches = re.findall(
                rf'{date_pattern}{descript_pattern}{withdraw_pattern}$\s+{order_pattern}',
                file_buff, re.M)
            for match in matches:
                row = dict()
                row['Account'] = 'Prime Visa'
                if match[0] == open_month:
                    row['Transaction Date'] = f'{match[0]}/{match[1]}/20{open_year}'
                else:
                    row['Transaction Date'] = f'{match[0]}/{match[1]}/20{close_year}'
                orig_description = match[2]
                row['Post Date'] = row['Transaction Date']
                row['Description'] = 'Amazon'
                row['Withdrawal'] = match[4]
                row['Notes'] = f'Order Number {match[5]}'

                match2 = re.search(rf'^{amazon_pattern}\*(\w+)', orig_description)
                if match2:
                    amzn_locator = match2.group(2)
                    logging.info("amznLocator %s", amzn_locator)
                    row['Notes'] += f' {amzn_locator}'
                    transact = locator_transactions.get(amzn_locator)
                else:
                    date_amount = f'{row["Transaction Date"]} {row["Withdrawal"]}'
                    transact = date_amount_transactions.get(date_amount)

                if transact:
                    row['Post Date'] = transact['Post Date']
                    row['Notes'] += f' {transact['Transaction Date']}'
                else:
                    date_amount = f'{row["Transaction Date"]} {row["Withdrawal"]}'
                    sys.stderr.write(f"Error - transaction missing {date_amount}\n")

                # Old Amazon Order Report
                for item in order_items[match[5]]:
                    # Note: if the quality is > 1 it is possible 1 item can come
                    # in multiple shipments in that case the item total will be
                    # the sum of the total charges.
                    quantity = ''
                    if int(item['Quantity']) > 1:
                        quantity = f'{item["Quantity"]}x '
                    row['Description'] += f' {quantity}{item["Title"]}({item["Item Total"]})'
                    row['Notes'] += f' {item['Category']}'

                # :TODO: Put New logic here
                if match[5] in orders:
                    order = orders[match[5]]
                    row['Description'] += f' {order['items']}'

                row['Description'] += f' {match[5]}'

                logging.debug("%s %s %s %s %s %s\n  %s", row['Account'], row['Transaction Date'],
                              row['Post Date'], row['Description'], row['Withdrawal'], row['Notes'],
                              orig_description)
                if row['Account'] in out_files:
                    writer = csv.DictWriter(out_files[row['Account']], fieldnames=row.keys(),
                                            dialect=dialect)
                else:
                    safe_account = re.sub(r'[^a-zA-Z0-9 ._-]', '', row['Account']).rstrip()
                    csvfilename = f"{chase_transactions_filename}-{safe_account}-out.csv"
                    logging.debug("%s - file - %s\n", row['Account'], csvfilename)
                    csvfile = open(csvfilename, 'w', encoding="utf8")
                    out_files[row['Account']] = csvfile
                    writer = csv.DictWriter(csvfile, fieldnames=row.keys(), dialect=dialect)
                    writer.writeheader()

                writer.writerow(row)


if __name__ == "__main__":
    sys.exit(main())
