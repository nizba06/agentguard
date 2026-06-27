# Build benchmark dataset from free public sources (zero API cost).
# Usage: .\scripts\run_public_dataset_build.ps1

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

Write-Host "Building dataset from InjectAgent + pipeline templates (no API key needed)..."
py -3.12 -m pip install datasets -q
py -3.12 benchmarks/build_dataset_from_public.py

$adv = (Get-Content benchmarks/dataset/adversarial.jsonl | Measure-Object -Line).Lines
$ben = (Get-Content benchmarks/dataset/benign.jsonl | Measure-Object -Line).Lines
Write-Host "Done: $adv adversarial + $ben benign examples"
Write-Host "Next: .\scripts\run_benchmark_evaluation.ps1"
