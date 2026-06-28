# Evaluate AgentGuard against the benchmark dataset.
# Usage:
#   .\scripts\run_benchmark_evaluation.ps1
#   .\scripts\run_benchmark_evaluation.ps1 -Quick
#   .\scripts\run_benchmark_evaluation.ps1 -RequireModel

param(
    [switch]$Quick,
    [switch]$RequireModel
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

$adv = "benchmarks/dataset/adversarial.jsonl"
$ben = "benchmarks/dataset/benign.jsonl"

if (-not (Test-Path $adv)) {
    Write-Error "Missing $adv — run .\scripts\run_public_dataset_build.ps1 first."
}
if (-not (Test-Path $ben)) {
    Write-Error "Missing $ben — run .\scripts\run_public_dataset_build.ps1 first."
}

$advCount = (Get-Content $adv | Measure-Object -Line).Lines
$benCount = (Get-Content $ben | Measure-Object -Line).Lines
Write-Host "Evaluating against $advCount adversarial + $benCount benign examples..."

$Args = @("benchmarks/evaluate.py")
if ($Quick) { $Args += "--quick" }
if ($RequireModel) { $Args += "--require-ml-model" }

py -3.12 @Args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Report: benchmarks/results/report.md"
