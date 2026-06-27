# Evaluate AgentGuard against the generated benchmark dataset.
# Usage: .\scripts\run_benchmark_evaluation.ps1

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

$adv = "benchmarks/dataset/adversarial.jsonl"
$ben = "benchmarks/dataset/benign.jsonl"

if (-not (Test-Path $adv)) {
    Write-Error "Missing $adv — run scripts/run_dataset_generation.ps1 first."
}
if (-not (Test-Path $ben)) {
    Write-Error "Missing $ben — run scripts/run_dataset_generation.ps1 first."
}

$advCount = (Get-Content $adv | Measure-Object -Line).Lines
$benCount = (Get-Content $ben | Measure-Object -Line).Lines
Write-Host "Evaluating against $advCount adversarial + $benCount benign examples..."

py -3.12 benchmarks/evaluate.py
Write-Host "Report: benchmarks/results/report.md"
