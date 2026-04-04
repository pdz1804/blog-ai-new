param(
    [string]$BaseUrl
)

$ErrorActionPreference = "Stop"

if (-not $BaseUrl) {
    Write-Error "Please pass -BaseUrl, e.g. -BaseUrl https://items-service-v2-xxxx-uc.a.run.app"
}

$env:ITEMS_SERVICE_BASE_URL = $BaseUrl.TrimEnd("/")

Write-Host "Running integration test against $env:ITEMS_SERVICE_BASE_URL"
.\.venv\Scripts\python.exe -m pytest -q tests/test_items_service_integration.py
