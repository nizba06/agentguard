# Publish agentguard to PyPI. Requires: pip install build twine
# Set $env:PYPI_TOKEN before running.

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if (-not $env:PYPI_TOKEN) {
    Write-Error "Set PYPI_TOKEN environment variable (PyPI API token)."
}

Write-Host "Building wheel and sdist..."
py -3.12 -m pip install --quiet build twine
py -3.12 -m build

Write-Host "Uploading to PyPI..."
py -3.12 -m twine upload dist/* --username __token__ --password $env:PYPI_TOKEN

Write-Host "Done. Verify: pip install agentguard"
