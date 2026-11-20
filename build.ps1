# Build script to create standalone executable
# This creates a single .exe file that includes all dependencies

Write-Host "Building standalone executable..."
Write-Host "This may take a few minutes..."

# Ensure we're in a virtual environment with all dependencies
if (-not (Test-Path "venv")) {
    Write-Host "Virtual environment not found. Running install.ps1 first..."
    & .\install.ps1
}

& venv\Scripts\activate

# Install PyInstaller if not already installed
py -m pip install pyinstaller

# Build the executable
py -m PyInstaller --onefile --name asgen asgen.py

Write-Host "Build complete!"
Write-Host "Executable created: dist\asgen.exe ($( [math]::Round((Get-Item 'dist\asgen.exe').Length / 1MB, 2) ) MB)"
Write-Host "You can now run asgen.exe directly without any installation!"
