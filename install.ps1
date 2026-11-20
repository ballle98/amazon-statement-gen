# Installation script for amazon-statement-gen
# This script handles the Pillow dependency issue with amazoncaptcha

Write-Host "Creating virtual environment..."
py -m venv venv

Write-Host "Activating virtual environment..."
& venv\Scripts\activate

Write-Host "Installing dependencies first..."
py -m pip install click requests beautifulsoup4 PyYAML python-dateutil pyotp pillow

Write-Host "Installing amazoncaptcha without dependencies..."
py -m pip install amazoncaptcha --no-deps

Write-Host "Installing amazon-orders without dependencies..."
py -m pip install amazon-orders --no-deps

Write-Host "Installation complete!"
Write-Host "To use: venv\Scripts\activate then py asgen.py [options]"
