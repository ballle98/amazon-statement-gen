# amazon-statement-gen

This tool takes a Prime Visa statement as a PDF and extracts the order IDs using pdftotext from it creates a csv file with additional details for those amazon transactions from Amazon Order History Reporter that can be imported into GNU cash.

Amazon retired Order History Tool in March 2023, Now use Amazon Order History Reporter Chrome plugin
https://chrome.google.com/webstore/detail/amazon-order-history-repo/mgkilgclilajckgnedgjgnfdokkgnibi

# usage 
```
usage: asgen.py [-h] [--verbose] [filenames ...]

Amazon Statement Generator

positional arguments:
  filenames

options:
  -h, --help     show this help message and exit
  --verbose, -v
```

# Reference/Links
- https://www.xpdfreader.com/pdftotext-man.html
- https://www.gnucash.org/
