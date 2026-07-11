# Publish inter-agent-guard to PyPI (import package remains agentguard).
# Requires: pip install build twine
# Set $env:PYPI_TOKEN before running.

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if (-not $env:PYPI_TOKEN) {
    Write-Error "Set PYPI_TOKEN environment variable (PyPI API token)."
}

# Avoid uploading stale wheels built under the old distribution name.
if (Test-Path dist) {
    Remove-Item dist -Recurse -Force
}

Write-Host "Building wheel and sdist for inter-agent-guard..."
py -3.12 -m pip install --quiet build twine
py -3.12 -m build

Write-Host "Checking dist metadata..."
py -3.12 -m twine check dist/*

Get-ChildItem dist | ForEach-Object { Write-Host "  $($_.Name)" }
if (-not (Get-ChildItem dist -Filter "inter_agent_guard-*")) {
    Write-Error "Expected dist artifacts named inter_agent_guard-*. Rebuild failed?"
}

Write-Host "Uploading to PyPI (verbose - read the Response from line if this fails)..."
py -3.12 -m twine upload dist/* --username __token__ --password $env:PYPI_TOKEN --verbose --non-interactive

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Upload failed. Common 400 causes:" -ForegroundColor Yellow
    Write-Host "  * Name too similar: distribution must be inter-agent-guard (not agentguard)" -ForegroundColor Yellow
    Write-Host "  * File already exists: bump version in pyproject.toml (e.g. 0.1.1) and rebuild" -ForegroundColor Yellow
    Write-Host "  * Email not verified: check https://pypi.org/manage/account/" -ForegroundColor Yellow
    Write-Host "  * Retry after partial upload: run verbose command above and read Response from" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Try TestPyPI first:" -ForegroundColor Yellow
    Write-Host '  $env:TESTPYPI_TOKEN = ''pypi-...''' -ForegroundColor Yellow
    Write-Host '  py -3.12 -m twine upload dist/* --repository-url https://test.pypi.org/legacy/ --username __token__ --password $env:TESTPYPI_TOKEN --verbose' -ForegroundColor Yellow
    exit $LASTEXITCODE
}

Write-Host "Done. Verify: pip install inter-agent-guard"
Write-Host 'Import check: python -c "from agentguard import AgentGuard; print(AgentGuard)"'
