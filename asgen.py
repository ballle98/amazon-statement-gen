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
    parser = argparse.ArgumentParser(description='Amazon Statement Generator')
    parser.add_argument('--verbose', '-v', action='count')
    parser.add_argument('filenames', nargs='*')

    args = parser.parse_args()

    if args.verbose:
        if args.verbose == 1:
            logging.basicConfig(level=logging.INFO)
        elif args.verbose > 1:
            logging.basicConfig(level=logging.DEBUG)

        logging.info("verbosity level = %d" % args.verbose)

    orders = defaultdict()
    orderHistory = list()
    orderItems = defaultdict(list)
    chaseTransactions = list()
    pdfTextFiles = list()
    locatorTransactions = defaultdict()
    dateAmountTransactions = defaultdict()

    globFileNames = list()
    for item in args.filenames:
        globFileNames += glob.glob(item)
    for fileName in globFileNames:
        logging.debug("file %s" % fileName)
        if os.path.splitext(fileName)[1] == '.pdf':
            logging.info("file is pdf")
            subprocess.run(["pdftotext", "-table", fileName])
            pdfTextFiles.append("%s.txt" % os.path.splitext(fileName)[0])
            chaseTransactionsFileName = os.path.splitext(fileName)[0]
        else:
            with open(fileName, 'r', encoding="utf-8-sig") as fd:
                fileBuff = fd.read()
                reader = csv.DictReader(fileBuff.splitlines())
                headers = reader.fieldnames
                if 'payments' in headers:  # History Reporter plugin orders
                    logging.info("file %s contains History Reporter orders" % fileName)
                    orderHistory = reader
                    for order in orderHistory:
                        orders[order['order id']] = order
                elif 'item url' in headers:  # History Reporter plugin items
                    logging.info("file %s contains History Reporter items" % fileName)
                    items = reader
                    for item in items:
                        orderItems[item['order id']].append(item)
                elif 'Post Date' in headers:  # Chase transactions .csv
                    logging.info("file %s contains credit card Transaction and Post Dates" % fileName)
                    chaseTransactions = reader
                    for transact in chaseTransactions:
                        match = re.search(r'^(AMZN|Amazon\.com|Prime Video|AMAZON).*', transact['Description'])
                        if match:
                            match2 = re.search(r'^(AMZN|Amazon\.com|Prime Video|AMAZON).*\*(\w+)', transact['Description'])
                            transact['Amount'] = str(-float(transact['Amount']))
                            if match2:
                                amznLocator = match2.group(2)
                                logging.info("amznLocator %s %s %s %s %s" % (amznLocator, transact['Transaction Date'], transact['Post Date'], transact['Description'], transact['Amount']))
                                locatorTransactions[amznLocator] = transact
                            else:
                                logging.info("date amount %s %s %s" % (("%s %s" % (transact['Transaction Date'], transact['Amount'])), transact['Post Date'], transact['Description']))
                                dateAmountTransactions["%s %s" % (transact['Transaction Date'], transact['Amount'])] = transact
                        else:
                            continue
                else:
                    sys.stderr.write("Error - Invalid csv file " + fileName + ".  Not items or shipments\n")

    outFiles = dict()
    dialect = csv.excel
    dialect.lineterminator = '\n'

    for pdfTextFile in pdfTextFiles:
        logging.debug("reading %s" % pdfTextFile)
        with open(pdfTextFile) as f:
            origFileBuff = f.read().replace('`', '')
            match = re.search(r'^\s*Opening/Closing Date\s+(\d+)/\d+/(\d+) - \d+/\d+/(\d+)',
                              origFileBuff, re.M)  # @UndefinedVariable
            if match:
                openMonth = match[1]
                openYear = match[2]
                closeYear = match[3]
                logging.debug("Opening/Closing %s %s %s" % (openMonth, openYear, closeYear))
            # Clean up the filebuff to
            fileBuff = ""

            # regex patterns
            date_pattern = r'^\s*(\d\d)/(\d\d)\s+'
            amazon_pattern = r'(AMZN|Amazon|Prime Video|AMAZON|Kindle|Audible).*'
            descript_pattern = rf'({amazon_pattern})\s+'
            withdraw_pattern = r'(-?\d*\.\d\d)'
            order_pattern = r'\s+Order Number\s+(\S+-\d+-\d+)'

            # get rid of any extra stuff like page breaks etc.
            fileBuff = "\n".join(
                line for line in origFileBuff.split('\n')
                    if re.search(
                        f'{date_pattern}{descript_pattern}{withdraw_pattern}|{order_pattern}',
                        line)
            )

            logging.debug(fileBuff)
            matches = re.findall(
                rf'{date_pattern}{descript_pattern}{withdraw_pattern}$\s+{order_pattern}',
                fileBuff, re.M)
            for match in matches:
                row = dict()
                row['Account'] = 'Prime Visa'
                if match[0] == openMonth:
                    row['Transaction Date'] = '%s/%s/20%s' % (match[0], match[1], openYear)
                else:
                    row['Transaction Date'] = '%s/%s/20%s' % (match[0], match[1], closeYear)
                origDescription = match[2]
                row['Post Date'] = row['Transaction Date']
                row['Description'] = 'Amazon'
                row['Withdrawal'] = match[4]
                row['Notes'] = 'Order Number %s' % (match[5])

                match2 = re.search(rf'^{amazon_pattern}\*(\w+)', origDescription)
                if match2:
                    amznLocator = match2.group(2)
                    logging.info("amznLocator %s" % amznLocator)
                    row['Notes'] += ' %s' % (amznLocator)
                    transact = locatorTransactions.get(amznLocator)
                else:
                    transact = dateAmountTransactions.get("%s %s" % (row['Transaction Date'], row['Withdrawal']))

                if transact:
                    row['Post Date'] = transact['Post Date']
                    row['Notes'] += ' %s' % transact['Transaction Date']
                else:
                    sys.stderr.write("Error - tansaction missing " + "%s %s " % (row['Transaction Date'], row['Withdrawal']) + origDescription + "\n")

                # Old Amazon Order Report
                for item in orderItems[match[5]]:
                    # Note: if the quanity is > 1 it is possible 1 item can come
                    # in multiple shipments in that case the item total will be
                    # the sum of the total charges.
                    quantity = ''
                    if int(item['Quantity']) > 1:
                        quantity = '%sx ' % item['Quantity']
                    row['Description'] += ' %s%s(%s)' % (quantity, item['Title'], item['Item Total'])
                    row['Notes'] += ' %s' % (item['Category'])

                # :TODO: Put New logic here
                if match[5] in orders:
                    order = orders[match[5]]
                    row['Description'] += ' %s' % (order['items'])

                row['Description'] += ' %s' % match[5]
                logging.debug("%s %s %s %s %s %s\n  %s" % (row['Account'], row['Transaction Date'], row['Post Date'], row['Description'], row['Withdrawal'], row['Notes'], origDescription))

                if row['Account'] in outFiles:
                    writer = csv.DictWriter(outFiles[row['Account']], fieldnames=row.keys(), dialect=dialect)
                else:
                    keepcharacters = (' ', '.', '_')
                    safeAccount = "".join(c for c in row['Account'] if c.isalnum() or c in keepcharacters).rstrip()
                    csvfilename = "%s-%s-out.csv" % (chaseTransactionsFileName, safeAccount)
                    logging.debug("%s - file - %s\n" % (row['Account'], csvfilename))
                    csvfile = open(csvfilename, 'w', encoding="utf8")
                    outFiles[row['Account']] = csvfile
                    writer = csv.DictWriter(csvfile, fieldnames=row.keys(), dialect=dialect)
                    writer.writeheader()

                writer.writerow(row)


if __name__ == "__main__":
    sys.exit(main())
