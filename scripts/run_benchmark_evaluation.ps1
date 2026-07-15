# Evaluate AgentGuard against the benchmark dataset.
# Usage:
#   .\scripts\run_benchmark_evaluation.ps1 -Holdout -RequireModel   # source of truth for v1.0
#   .\scripts\run_benchmark_evaluation.ps1 -RequireModel            # full corpus (may overlap train)
#   .\scripts\run_benchmark_evaluation.ps1 -Quick -RequireModel

param(
    [switch]$Quick,
    [switch]$RequireModel,
    [switch]$Holdout
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root
$env:PYTHONPATH = $Root

if ($Holdout) {
    $adv = "benchmarks/dataset/holdout/adversarial.jsonl"
    $ben = "benchmarks/dataset/holdout/benign.jsonl"
    $report = "benchmarks/results/holdout_report.md"
    if (-not (Test-Path $adv)) {
        Write-Error "Missing holdout — run .\scripts\retrain_checklist.ps1 -Prepare first."
    }
} else {
    $adv = "benchmarks/dataset/adversarial.jsonl"
    $ben = "benchmarks/dataset/benign.jsonl"
    $report = "benchmarks/results/report.md"
}

if (-not (Test-Path $adv)) {
    Write-Error "Missing $adv — run .\scripts\run_public_dataset_build.ps1 first."
}
if (-not (Test-Path $ben)) {
    Write-Error "Missing $ben — run .\scripts\run_public_dataset_build.ps1 first."
}

$advCount = (Get-Content $adv | Measure-Object -Line).Lines
$benCount = (Get-Content $ben | Measure-Object -Line).Lines
$scope = if ($Holdout) { "HOLDOUT (v1.0 source of truth)" } else { "FULL corpus (may include train overlap)" }
Write-Host "Evaluating $scope — $advCount adversarial + $benCount benign examples..."

$Args = @(
    "benchmarks/evaluate.py",
    "--adversarial-path", $adv,
    "--benign-path", $ben,
    "--report-path", $report
)
if ($Quick) { $Args += "--quick" }
if ($RequireModel) { $Args += "--require-ml-model" }

py -3.12 @Args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Report: $report"
if (-not $Holdout) {
    Write-Host "Note: for v1.0 gating use -Holdout. Full-corpus 100% scores are not reliable if the model trained on this corpus."
}
