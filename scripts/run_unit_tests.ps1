$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv/Scripts/python.exe")) {
    Write-Error "Python virtual environment not found at .venv. Create it first."
}

Write-Host "Installing/refreshing dependencies..."
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

Write-Host "Running unit tests..."
.\.venv\Scripts\python.exe -m pytest -q
