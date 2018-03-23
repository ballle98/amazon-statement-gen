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
import os
import logging
import csv
from collections import defaultdict

from optparse import OptionParser

__all__ = []
__version__ = 0.1
__date__ = '2016-09-26'
__updated__ = '2016-09-26'

DEBUG = 1
TESTRUN = 0
PROFILE = 0

def main(argv=None):
    '''Command line options.'''

    program_name = os.path.basename(sys.argv[0])
    program_version = "v0.1"
    program_build_date = "%s" % __updated__

    program_version_string = '%%prog %s (%s)' % (program_version, program_build_date)
    program_usage = '''usage: %prog [options] csv-files'''
    program_longdesc = '''''' # optional - give further explanation about what the program does
    program_license = "Copyright 2016 lee Ballard                                            \
                Licensed under the Apache License 2.0\nhttp://www.apache.org/licenses/LICENSE-2.0"

    if argv is None:
        argv = sys.argv[1:]
    try:
        # setup option parser
        parser = OptionParser(version=program_version_string, epilog=program_longdesc, description=program_license, usage=program_usage)
        parser.add_option("-v", "--verbose", dest="verbose", action="count", help="set verbosity level [default: %default]")

        # set defaults
        parser.set_defaults(verbose=0)

        # process options
        (opts, args) = parser.parse_args(argv)

        if opts.verbose == 1:
            logging.basicConfig(level=logging.INFO)
        elif opts.verbose > 1:
            logging.basicConfig(level=logging.DEBUG)
            
        logging.info("verbosity level = %d" % opts.verbose)

        # MAIN BODY #
        if len(args) < 1:
            sys.stderr.write(program_name + ": Error - must specify at least one input cvs file\n")
            return 2
        
        orderItems = defaultdict(list)

        for fileName in args:
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
                else:
                    sys.stderr.write(program_name + ": Error - Invalid cvs file " + fileName + ".  Not items or shipments\n")
                
        for item in items:
            orderItems[item['Order ID']].append(item)   
            
        with open('out.csv', 'w') as csvfile:
            fieldnames = ['Date', 'Description', 'Deposit', 'Notes']
            dialect = csv.excel
            dialect.lineterminator = '\n' 
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, dialect=dialect)
            writer.writeheader()
            for shipment in shipments:
                row = dict()
                row['Date'] = shipment['Shipment Date']
                row['Description'] = 'Amazon'
                row['Deposit'] = shipment['Total Charged'].replace('$','')
                row['Notes'] = shipment['Order ID'] + ' ' + shipment['Carrier Name & Tracking Number']
                for item in orderItems[shipment['Order ID']]:
                    row['Description'] += ' %s(%s)' % (item['Title'], item['Item Total'])
                logging.debug("%s %s %s\n  %s" % (row['Date'], row['Description'], row['Deposit'], row['Notes']))
                writer.writerow(row)
            
                 
        # 4) order 104-7065965-1464218 has 1 item with 2 shipments
        # 5) sum of purchace price in items equals subtotal (price without tax).  Use Total Charge


    except Exception, e:
        indent = len(program_name) * " "
        sys.stderr.write(program_name + ": " + repr(e) + "\n")
        sys.stderr.write(indent + "  for help use --help")
        return 2


if __name__ == "__main__":
    if DEBUG:
        pass
        # sys.argv.append("-h")
    if TESTRUN:
        import doctest
        doctest.testmod()
    if PROFILE:
        import cProfile
        import pstats
        profile_filename = 'asgen_profile.txt'
        cProfile.run('main()', profile_filename)
        statsfile = open("profile_stats.txt", "wb")
        p = pstats.Stats(profile_filename, stream=statsfile)
        stats = p.strip_dirs().sort_stats('cumulative')
        stats.print_stats()
        statsfile.close()
        sys.exit(0)
    sys.exit(main())