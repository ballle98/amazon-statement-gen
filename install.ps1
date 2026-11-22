# Installation script for amazon-statement-gen

$ErrorActionPreference = "Stop"

Write-Host "Checking Python version..."
py -c "import sys; sys.exit(0) if sys.version_info >= (3, 12) else sys.exit('Python 3.12 or newer is required')"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Creating virtual environment..."
py -m venv venv

Write-Host "Activating virtual environment..."
& venv\Scripts\activate

Write-Host "Installing dependencies..."
py -m pip install -r requirements.txt

Write-Host "Installation complete!"
Write-Host "To use: venv\Scripts\activate then py asgen.py [options]"
