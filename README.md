# amazon-statement-gen

This tool takes a Prime Visa statement as a PDF and extracts the order IDs using pdftotext from it creates a csv file with additional details for those amazon transactions from Amazon Order History Reporter that can be imported into GNU cash.

Amazon retired Order History Tool in March 2023, Now use Amazon Order History Reporter Chrome plugin
https://chrome.google.com/webstore/detail/amazon-order-history-repo/mgkilgclilajckgnedgjgnfdokkgnibi

developed here https://github.com/philipmulcahy/azad

When an orders report CSV is not available, the tool can fetch order history directly from Amazon using the [amazon-orders](https://github.com/alexdlaird/amazon-orders) library.

# Installation
Windows (recommended - use installation script):
```
powershell -ExecutionPolicy Bypass -File install.ps1
```
Or manual installation:
```
py -m venv venv
venv\Scripts\activate
py -m pip install click requests beautifulsoup4 PyYAML python-dateutil pyotp pillow
py -m pip install amazoncaptcha --no-deps
py -m pip install amazon-orders --no-deps
```
Or install directly (Windows doesn't restrict system-wide installs):
```
py -m pip install -r requirements.txt
```
Linux (recommended - use installation script):
```
chmod +x install.sh
./install.sh
```
Or manual installation:
```
python3 -m venv venv
source venv/bin/activate
pip install click requests beautifulsoup4 PyYAML python-dateutil pyotp pillow
pip install amazoncaptcha --no-deps
pip install amazon-orders --no-deps
```
Or install system-wide with `--break-system-packages` (not recommended):
```
pip install --break-system-packages -r requirements.txt
```

# Standalone Executable (No Installation Required)

For easy distribution, you can build a standalone executable that includes all dependencies:

Windows:
```
powershell -ExecutionPolicy Bypass -File build.ps1
```

Linux:
```
chmod +x build.sh
./build.sh
```

This creates `dist/asgen.exe` (Windows) or `dist/asgen` (Linux) - a single file (~20MB) that can be run without any Python installation or virtual environment.

# usage 
```
usage: asgen.py [-h] [--verbose] [--amazon-username AMAZON_USERNAME]
                [--amazon-password AMAZON_PASSWORD] [--year YEAR]
                [filenames ...]

Amazon Statement Generator

positional arguments:
  filenames

options:
  -h, --help            show this help message and exit
  --verbose, -v
  --amazon-username      Amazon username (repeatable, or set AMAZON_USERNAME env var)
  --amazon-password      Amazon password (repeatable, or set AMAZON_PASSWORD env var)
  --year YEAR            Year to fetch Amazon order history for
```

Multiple statement PDFs and multiple Chase transaction CSVs are supported. Each statement PDF produces its own output CSV. The year(s) needed for fetching Amazon order history are automatically extracted from the statement Opening/Closing Date (including both years for January statements that span two years). The `--year` flag overrides auto-detection.

When no orders report CSV is provided, pass Amazon credentials to fetch order history automatically:
```
python asgen.py --amazon-username user@email.com --amazon-password mypass statement.pdf chase.csv
```

Multiple statements and transaction files:
```
python asgen.py --amazon-username user@email.com --amazon-password mypass statement-jan.pdf statement-feb.pdf chase-jan.csv chase-feb.csv
```

Multiple Amazon accounts are supported by repeating the flags (each username paired with the corresponding password):
```
python asgen.py --amazon-username user1@email.com --amazon-password pass1 --amazon-username user2@email.com --amazon-password pass2 statement.pdf chase.csv
```

Or use environment variables for a single account:
```
export AMAZON_USERNAME=user@email.com
export AMAZON_PASSWORD=mypass
python asgen.py statement.pdf chase.csv
```

# Reference/Links
- https://www.xpdfreader.com/pdftotext-man.html
- https://www.gnucash.org/
- https://github.com/alexdlaird/amazon-orders
