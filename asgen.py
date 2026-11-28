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
import argparse
import os

from collections import defaultdict

from amazonorders.session import AmazonSession
from amazonorders.orders import AmazonOrders

import emit
import gnucash
import match
import parse


def fetch_orders(usernames, passwords, years, args, orders, order_items):
    """Fetch Amazon order history into the orders and order_items collections."""
    if not usernames and os.environ.get('AMAZON_USERNAME'):
        usernames = [os.environ['AMAZON_USERNAME']]
        passwords = [os.environ.get('AMAZON_PASSWORD', '')]
    if usernames and passwords:
        if len(usernames) != len(passwords):
            sys.stderr.write("Error - number of --amazon-username and "
                             "--amazon-password arguments must match\n")
        else:
            years_to_fetch = [args.year] if args.year else sorted(years)
            if not years_to_fetch:
                logging.warning("No year specified and no years found in statements")
            for year in years_to_fetch:
                for username, password in zip(usernames, passwords):
                    logging.info("Fetching orders from Amazon for %s year %d",
                                 username, year)
                    amazon_session = AmazonSession(
                        username, password,
                        otp_secret_key=os.environ.get('AMAZON_OTP_SECRET_KEY'))
                    amazon_session.login()
                    amazon_orders = AmazonOrders(amazon_session)
                    fetched_orders = amazon_orders.get_orders(
                        year=year, full_details=True)
                    logging.info("Successfully fetched %d orders for %s year %d",
                                 len(fetched_orders), username, year)
                    for order in fetched_orders:
                        order_id = order.order_number
                        item_titles = [item.title for item in order.items
                                       if item.title]
                        orders[order_id] = {'items': ', '.join(item_titles)}
                        for item in order.items:
                            order_items[order_id].append({
                                'order id': order_id,
                                'Title': item.title or '',
                                'Quantity': str(item.quantity)
                                    if item.quantity else '1',
                                'Item Total': f'${item.price:.2f}'
                                    if item.price else '$0.00',
                                'Category': '',
                            })
    else:
        logging.warning("No orders report found and no Amazon credentials provided. "
                        "Use --amazon-username/--amazon-password or set "
                        "AMAZON_USERNAME/AMAZON_PASSWORD environment variables.")


def main():
    """
    The main function of the program. It takes command line arguments and processes them.

    Parameters:
        None

    Returns:
        None
    """
    if sys.version_info < (3, 12):
        sys.stderr.write("Error - Python 3.12 or newer is required\n")
        return 1

    parser = argparse.ArgumentParser(description='Amazon Statement Generator')
    parser.add_argument('--verbose', '-v', action='count')
    parser.add_argument('--amazon-username', '-u', action='append', default=[],
                        help='Amazon username (repeatable, or set AMAZON_USERNAME env var)')
    parser.add_argument('--amazon-password', '-p', action='append', default=[],
                        help='Amazon password (repeatable, or set AMAZON_PASSWORD env var)')
    parser.add_argument('--year', '-y', type=int, default=None,
                        help='Year to fetch Amazon order history for')
    parser.add_argument('--statement-text', action='append', default=[], metavar='FILE',
                        help='Already-extracted statement text (repeatable); '
                             'skips pdftotext')
    parser.add_argument('--output-dir', metavar='DIR',
                        help='Write generated CSV, error, and report files here')
    parser.add_argument('--gnucash-book', metavar='FILE',
                        help='Update descriptions in this GnuCash SQLite book')
    parser.add_argument('--gnucash-account', default=gnucash.ACCOUNT_NAME,
                        metavar='NAME',
                        help='GnuCash account to search (default: %(default)s)')
    parser.add_argument('--dry-run', action='store_true',
                        help='With --gnucash-book, report changes without writing')
    parser.add_argument('--csv', action='store_true',
                        help='In GnuCash mode, also write legacy CSV output')
    parser.add_argument('filenames', nargs='*')

    args = parser.parse_args()

    if args.dry_run and not args.gnucash_book:
        parser.error('--dry-run requires --gnucash-book')

    if args.verbose:
        if args.verbose == 1:
            logging.basicConfig(level=logging.INFO)
        elif args.verbose > 1:
            logging.basicConfig(level=logging.DEBUG)

        logging.info("verbosity level = %d", args.verbose)

    statement_files = parse.collect_statement_files(
        args.filenames, args.statement_text, args.output_dir)
    orders, order_items, has_orders_report, chase_transactions = parse.load_csvs(
        args.filenames)
    years = parse.statement_years(statement_files)

    if not has_orders_report:
        fetch_orders(args.amazon_username, args.amazon_password, years, args,
                     orders, order_items)

    locators, date_amounts = match.build_indexes(chase_transactions)

    if args.gnucash_book:
        gnucash.enrich_statements(
            statement_files, orders, order_items, locators, date_amounts,
            args.gnucash_book, args.gnucash_account, args.dry_run)
        if args.csv:
            emit.write_statements(
                statement_files, orders, order_items, locators, date_amounts)
    else:
        emit.write_statements(
            statement_files, orders, order_items, locators, date_amounts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
