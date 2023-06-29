#!/usr/bin/env python
# encoding: utf-8
'''
asgen -- Amazon Statement Generator

asgen statements from a Amazon Prime Visa card and combines them with order history from Amazon

Download Xpdf command line tools from https://www.xpdfreader.com/download.html

Amazon retired Order History Tool in March 2023, Now use Amazon Order History Reporter Chrome plugin
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
from datetime import datetime, timedelta
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
    shipments = list()
    chaseTransactions = list()
    pdfTextFiles = list()

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
                if 'order id' in headers:
                    logging.info("file %s contains order history" % fileName)
                    orderHistory = reader
                    for order in orderHistory:
                        orders[order['order id']] = order
                elif 'Transaction Date' in headers:
                    logging.info("file %s contains transactions" % fileName)
                    chaseTransactions = reader
                    chaseTransactionsFileName_w_ext = os.path.basename(fileName)
                    chaseTransactionsFileName = os.path.join(os.path.dirname(fileName), os.path.splitext(chaseTransactionsFileName_w_ext)[0])
                elif 'Title' in headers:
                    logging.info("file %s contains items" % fileName)
                    items = reader
                    for item in items:
                        orderItems[item['Order ID']].append(item)
                elif 'Total Charged' in headers:
                    logging.info("file %s contains shipments" % fileName)
                    shipments = reader
                    shipmentsFileName_w_ext = os.path.basename(fileName)
                    shipmentsFileName = os.path.join(os.path.dirname(fileName), os.path.splitext(shipmentsFileName_w_ext)[0])
                else:
                    sys.stderr.write("Error - Invalid csv file " + fileName + ".  Not items or shipments\n")

    outFiles = dict()
    fieldnames = ['Account', 'Date', 'Description', 'Withdrawal', 'Notes']
    dialect = csv.excel
    dialect.lineterminator = '\n'

    for shipment in shipments:
        row = dict()
        row['Account'] = shipment['Payment Instrument Type']
        # transaction date is at least 1 day after shipping
        transactionDate = datetime.strptime(shipment['Shipment Date'], '%m/%d/%y') + timedelta(days=1)
        row['Date'] = transactionDate.strftime('%m/%d/%y')
        # logging.debug("%s %s" % (shipment['Shipment Date'], row['Date']))
        row['Description'] = 'Amazon'
        row['Withdrawal'] = shipment['Total Charged'].replace('$', '')

        row['Notes'] = shipment['Order ID'] + ' ' + shipment['Carrier Name & Tracking Number']
        for item in orderItems[shipment['Order ID']]:
            # Note: if the quanity is > 1 it is possible 1 item can come
            # in multiple shipments in that case the item total will be
            # the sum of the total charges.
            quantity = ''
            if int(item['Quantity']) > 1:
                quantity = '%sx ' % item['Quantity']
            row['Description'] += ' %s%s(%s)' % (quantity, item['Title'], item['Item Total'])
            row['Notes'] += ' %s' % (item['Category'])
        promo = float(shipment['Total Promotions'].replace('$', ''))
        if promo > 0:
            # The total charge is the sum of item totals minus promos
            row['Description'] += '(promo -$%.2f)' % (promo)
        logging.debug("%s %s %s %s\n  %s" % (row['Account'], row['Date'], row['Description'], row['Withdrawal'], row['Notes']))

        if row['Account'] in outFiles:
            writer = csv.DictWriter(outFiles[row['Account']], fieldnames=fieldnames, dialect=dialect)
        else:
            keepcharacters = (' ', '.', '_')
            safeAccount = "".join(c for c in row['Account'] if c.isalnum() or c in keepcharacters).rstrip()
            csvfilename = "%s-%s-out.csv" % (shipmentsFileName, safeAccount)
            logging.debug("%s - file - %s\n" % (row['Account'], csvfilename))
            csvfile = open(csvfilename, 'w', encoding="utf8")
            outFiles[row['Account']] = csvfile
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, dialect=dialect)
            writer.writeheader()

        writer.writerow(row)

    for transact in chaseTransactions:
        match = re.search(r'^(AMZN|Amazon\.com).*\*(\w+)', transact['Description'])
        if match:
            amznLocator = match.group(2)
            logging.info("amznLocator %s" % amznLocator)
        else:
            continue

        row = dict()
        row['Account'] = 'Prime Visa'
        row['Date'] = transact['Post Date']
        # logging.debug("%s %s" % (shipment['Shipment Date'], row['Date']))
        row['Description'] = 'Amazon'
        row['Withdrawal'] = transact['Amount'].replace('-', '')

        row['Notes'] = amznLocator
#         for item in orderItems[shipment['Order ID']]:
#             # Note: if the quanity is > 1 it is possible 1 item can come
#             # in multiple shipments in that case the item total will be
#             # the sum of the total charges.
#             quantity = ''
#             if int(item['Quantity']) > 1:
#                 quantity = '%sx ' % item['Quantity']
#             row['Description'] += ' %s%s(%s)' % (quantity, item['Title'], item['Item Total'])
#             row['Notes'] += ' %s' % (item['Category'])

        logging.debug("%s %s %s %s\n  %s" % (row['Account'], row['Date'], row['Description'], row['Withdrawal'], row['Notes']))

        if row['Account'] in outFiles:
            writer = csv.DictWriter(outFiles[row['Account']], fieldnames=fieldnames, dialect=dialect)
        else:
            keepcharacters = (' ', '.', '_')
            safeAccount = "".join(c for c in row['Account'] if c.isalnum() or c in keepcharacters).rstrip()
            csvfilename = "%s-%s-out.csv" % (chaseTransactionsFileName, safeAccount)
            logging.debug("%s - file - %s\n" % (row['Account'], csvfilename))
            csvfile = open(csvfilename, 'w', encoding="utf8")
            outFiles[row['Account']] = csvfile
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, dialect=dialect)
            writer.writeheader()

        writer.writerow(row)

    for pdfTextFile in pdfTextFiles:
        logging.debug("reading %s" % pdfTextFile)
        with open(pdfTextFile) as f:
            fileBuff = f.read().replace('`', '')
            match = re.search(r'^\s*Opening/Closing Date\s+(\d+)/\d+/(\d+) - \d+/\d+/(\d+)', fileBuff, re.M)  # @UndefinedVariable
            if match:
                openMonth = match[1]
                openYear = match[2]
                closeYear = match[3]
                logging.debug("Opening/Closing %s %s %s" % (openMonth, openYear, closeYear))
            matches = re.findall(r'^\s*(\d\d)/(\d\d)\s+(AMZN|Amazon\.com|Prime Video).*\s+(-?\d*\.\d\d)$\s+Order Number\s+(\S+-\d+-\d+)', fileBuff, re.M)  # @UndefinedVariable
            for match in matches:
                row = dict()
                row['Account'] = 'Prime Visa'
                if match[0] == openMonth:
                    row['Date'] = '%s/%s/%s' % (match[0], match[1], openYear)
                else:
                    row['Date'] = '%s/%s/%s' % (match[0], match[1], closeYear)
                row['Description'] = 'Amazon'
                row['Withdrawal'] = match[3]
                row['Notes'] = 'Order Number %s' % (match[4])

                # Old Amazon Order Report
                for item in orderItems[match[4]]:
                    # Note: if the quanity is > 1 it is possible 1 item can come
                    # in multiple shipments in that case the item total will be
                    # the sum of the total charges.
                    quantity = ''
                    if int(item['Quantity']) > 1:
                        quantity = '%sx ' % item['Quantity']
                    row['Description'] += ' %s%s(%s)' % (quantity, item['Title'], item['Item Total'])
                    row['Notes'] += ' %s' % (item['Category'])

                # :TODO: Put New logic here
                if match[4] in orders:
                    order = orders[match[4]]
                    row['Description'] += ' %s' % (order['items'])

                row['Description'] += ' %s' % match[4]
                logging.debug("%s %s %s %s\n  %s" % (row['Account'], row['Date'], row['Description'], row['Withdrawal'], row['Notes']))

                if row['Account'] in outFiles:
                    writer = csv.DictWriter(outFiles[row['Account']], fieldnames=fieldnames, dialect=dialect)
                else:
                    keepcharacters = (' ', '.', '_')
                    safeAccount = "".join(c for c in row['Account'] if c.isalnum() or c in keepcharacters).rstrip()
                    csvfilename = "%s-%s-out.csv" % (chaseTransactionsFileName, safeAccount)
                    logging.debug("%s - file - %s\n" % (row['Account'], csvfilename))
                    csvfile = open(csvfilename, 'w', encoding="utf8")
                    outFiles[row['Account']] = csvfile
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames, dialect=dialect)
                    writer.writeheader()

                writer.writerow(row)


if __name__ == "__main__":
    sys.exit(main())
