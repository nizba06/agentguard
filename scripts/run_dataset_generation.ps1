# Generate the 6,200-example benchmark dataset via Anthropic Batch API.
# FOR v1.0 LAUNCH ONLY — see scripts/LAUNCH_CHECKLIST.md
# For zero-cost development, use: .\scripts\run_public_dataset_build.ps1
# Usage: $env:ANTHROPIC_API_KEY = "sk-ant-..."; .\scripts\run_dataset_generation.ps1
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if (-not $env:ANTHROPIC_API_KEY) {
    Write-Error "ANTHROPIC_API_KEY is not set. Export it before running this script."
}

Write-Host "Starting adversarial + benign dataset generation (expect 30-90 min)..."
py -3.12 -m pip install anthropic -q
py -3.12 benchmarks/generate_dataset.py
Write-Host "Done. Output: benchmarks/dataset/adversarial.jsonl, benchmarks/dataset/benign.jsonl"
