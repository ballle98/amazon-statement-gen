#!/usr/bin/env python
# encoding: utf-8
'''
asgen -- Amazon Statment Generator

asgen is a description

It defines classes_and_methods

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

def main():
    parser = argparse.ArgumentParser(description='Amazon Statment Generator')
    parser.add_argument('--verbose', '-v', action='count')
    parser.add_argument('filenames', nargs='*')
    
    args = parser.parse_args()

    if args.verbose == 1:
        logging.basicConfig(level=logging.INFO)
    elif args.verbose > 1:
        logging.basicConfig(level=logging.DEBUG)
            
    logging.info("verbosity level = %d" % args.verbose)
       
    orderItems = defaultdict(list)

    for fileName in args.filenames:
        with open(fileName, 'r') as fd:
            fileBuff = fd.read()
            reader = csv.DictReader(fileBuff.splitlines())
            headers = reader.fieldnames
            if 'Title' in headers: 
                logging.info("file %s contains items" % fileName)
                items = reader
            elif 'Total Charged' in headers:
                logging.info("file %s contains shipments" % fileName)
                shipments = reader
                shipmentsFileName_w_ext = os.path.basename(fileName)
                shipmentsFileName = os.path.join(os.path.dirname(fileName),os.path.splitext(shipmentsFileName_w_ext)[0]) 
            else:
                sys.stderr.write("Error - Invalid cvs file " + fileName + ".  Not items or shipments\n")
                
    for item in items:
        orderItems[item['Order ID']].append(item)   

    outFiles = dict()    
    fieldnames = ['Account','Date', 'Description', 'Deposit', 'Notes']
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
        row['Deposit'] = shipment['Total Charged'].replace('$','')

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
        promo = float(shipment['Total Promotions'].replace('$',''))
        if promo > 0:
            # The total charge is the sum of item totals minus promos
            row['Description'] += '(promo -$%.2f)' % (promo)
        logging.debug("%s %s %s %s\n  %s" % (row['Account'], row['Date'], row['Description'], row['Deposit'], row['Notes']))

        if row['Account'] in outFiles:
            writer = csv.DictWriter(outFiles[row['Account']], fieldnames=fieldnames, dialect=dialect)
        else:
            keepcharacters = (' ','.','_')
            safeAccount = "".join(c for c in row['Account'] if c.isalnum() or c in keepcharacters).rstrip()
            csvfilename = "%s-%s-out.csv" % (shipmentsFileName, safeAccount)
            logging.debug("%s - file - %s\n" % (row['Account'], csvfilename))
            csvfile = open(csvfilename, 'w')
            outFiles[row['Account']] = csvfile
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, dialect=dialect)
            writer.writeheader()
        
        writer.writerow(row)



if __name__ == "__main__":
    sys.exit(main())