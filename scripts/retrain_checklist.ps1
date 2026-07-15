# AgentGuard Phase 1-4 retrain / v1.0 checklist
# Usage:
#   .\scripts\retrain_checklist.ps1
#   .\scripts\retrain_checklist.ps1 -Prepare
#   .\scripts\retrain_checklist.ps1 -Prepare -TrainQuick
#   .\scripts\retrain_checklist.ps1 -AllLocal

param(
    [switch]$Prepare,
    [switch]$TrainQuick,
    [switch]$Export,
    [switch]$EvaluateHoldout,
    [switch]$AllLocal,
    [ValidateSet("anthropic", "mixed", "injectagent")]
    [string]$Source = "anthropic"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root
$env:PYTHONPATH = $Root

function Write-Step([string]$Title) {
    Write-Host ""
    Write-Host "=== $Title ===" -ForegroundColor Cyan
}

Write-Step "v1.0 gap checklist (Phase 1-4)"
# Single-quoted here-string: ASCII only, no expansion / no [ ] parsing issues
Write-Host @'
Phase 1 - ML quality (detection + FPR)
  (1) Prepare Anthropic-primary train/val + 20% holdout
      py -3.12 training/prepare_dataset.py --source anthropic
  (2) Fine-tune DeBERTa on Kaggle GPU (preferred) or local CUDA
      .\scripts\push_kaggle_kernel.ps1
      OR: poetry run python training/train.py
  (3) Export ONNX + SHA-256 pin
      poetry run python training/export_onnx.py
      py -3.12 scripts/verify_model.py
  (4) Evaluate on holdout (uncontaminated) then full corpus
      .\scripts\run_benchmark_evaluation.ps1 -Holdout -RequireModel
      py -3.12 scripts/check_v1_gates.py
      .\scripts\run_benchmark_evaluation.ps1 -RequireModel

Phase 2 - Consistency FPR
  (5) Ablate consistency (enable_consistency_check=False) on holdout
  (6) Keep consistency as gray-band / monitor-only if it dominates FPs

Phase 3 - Latency
  (7) Stage timings in evaluate report (rules / ML / consistency)
  (8) Quantized ONNX export; measure CPU P95; document GPU/async SLA

Phase 4 - Ship 1.0 when gates pass
  .\scripts\ship_v1.ps1 -Apply [-AllowCpuLatency]
  Detection gt 90%, FPR lt 3%, latency/size gates -> tag v1.0.0 + PyPI + Release assets
'@

$adv = "benchmarks/dataset/adversarial.jsonl"
$ben = "benchmarks/dataset/benign.jsonl"
if (-not (Test-Path $adv) -or -not (Test-Path $ben)) {
    Write-Error "Missing Anthropic corpus under benchmarks/dataset/. Restore from HF or regenerate."
}

Write-Step "Prerequisite check"
Write-Host "Anthropic adversarial: $((Get-Content $adv | Measure-Object -Line).Lines) lines"
Write-Host "Anthropic benign:      $((Get-Content $ben | Measure-Object -Line).Lines) lines"
$onnx = "agentguard/models/risk_scorer.onnx"
if (Test-Path $onnx) {
    $mb = [math]::Round((Get-Item $onnx).Length / 1MB, 1)
    Write-Host "ONNX present: $onnx ($mb MB)"
} else {
    Write-Host "ONNX missing - download or export before --require-ml-model eval"
}

if ($AllLocal) {
    $Prepare = $true
    $TrainQuick = $true
    $Export = $true
    $EvaluateHoldout = $true
}

if ($Prepare) {
    Write-Step "Prepare dataset (source=$Source)"
    py -3.12 training/prepare_dataset.py --source $Source
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if ($TrainQuick) {
    Write-Step "Quick train (1 epoch smoke - use Kaggle for real Phase 1)"
    py -3.12 training/train.py --quick
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if ($Export) {
    Write-Step "Export ONNX from latest checkpoint"
    py -3.12 training/export_onnx.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if ($EvaluateHoldout) {
    $hAdv = "benchmarks/dataset/holdout/adversarial.jsonl"
    $hBen = "benchmarks/dataset/holdout/benign.jsonl"
    if (-not (Test-Path $hAdv)) {
        Write-Error "Holdout missing - run with -Prepare first"
    }
    Write-Step "Evaluate holdout split"
    py -3.12 benchmarks/evaluate.py `
        --adversarial-path $hAdv `
        --benign-path $hBen `
        --report-path benchmarks/results/holdout_report.md `
        --require-ml-model
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host ""
Write-Host "Done. See docs/V1_ROADMAP.md for phase gates." -ForegroundColor Green
