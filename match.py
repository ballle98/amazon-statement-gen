#!/usr/bin/env python3

"""Match parsed statement rows to Chase transactions."""

import logging
import re

from collections import defaultdict

AMAZON_TRANSACTION_PATTERN = r'^(AMZN|Amazon|Prime Video|AMAZON|Audible).*'


def build_indexes(chase_transactions):
    """Build the locator and date+amount lookup tables from Chase transactions."""
    locators = defaultdict()
    date_amounts = defaultdict()
    for transact in chase_transactions:
        if not re.search(AMAZON_TRANSACTION_PATTERN, transact['Description']):
            continue
        locator_match = re.search(
            rf'{AMAZON_TRANSACTION_PATTERN}\*(\w+)', transact['Description'])
        transact['Amount'] = str(-float(transact['Amount']))
        if locator_match:
            amzn_locator = locator_match.group(2)
            logging.info("amznLocator %s %s %s %s %s", amzn_locator,
                         transact['Transaction Date'], transact['Post Date'],
                         transact['Description'], transact['Amount'])
            locators[amzn_locator] = transact
        else:
            logging.info("date amount %s %s %s",
                         f"{transact['Transaction Date']} {transact['Amount']}",
                         transact['Post Date'], transact['Description'])
            date_amount = f"{transact['Transaction Date']} {transact['Amount']}"
            date_amounts[date_amount] = transact
    return locators, date_amounts


def find_transaction(record, locators, date_amounts):
    """Return the Chase transaction for a record, locator first.

    A record with a locator but no matching transaction is not retried by
    date and amount, matching the original CLI behavior.
    """
    if record['locator']:
        logging.info("amznLocator %s", record['locator'])
        return locators.get(record['locator'])
    date_amount = f"{record['transaction_date']} {record['withdrawal']}"
    return date_amounts.get(date_amount)
