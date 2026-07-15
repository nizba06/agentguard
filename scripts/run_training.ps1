# Train DeBERTa risk scorer and export ONNX to agentguard/models/
# Usage:
#   .\scripts\run_training.ps1              # full training (4 epochs)
#   .\scripts\run_training.ps1 -Quick       # 1 epoch, max 2000 samples (local smoke)
#   .\scripts\run_training.ps1 -Full          # 4 epochs, all prepared data (Kaggle-equivalent)

param(
    [switch]$Quick,
    [switch]$Full
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root
$env:PYTHONPATH = $Root

Write-Host "Installing training dependencies..."
py -3.12 -m pip install -q transformers datasets optimum[onnxruntime] scikit-learn accelerate torch sentencepiece protobuf tiktoken

Write-Host "Preparing training dataset..."
py -3.12 training/prepare_dataset.py

if ($Quick) {
    $env:AGENTGUARD_TRAIN_QUICK = "1"
    $env:AGENTGUARD_TRAIN_MAX_SAMPLES = "2000"
    Write-Host "Quick training mode: 1 epoch, up to 2000 samples"
} elseif ($Full) {
    Remove-Item Env:AGENTGUARD_TRAIN_QUICK -ErrorAction SilentlyContinue
    Remove-Item Env:AGENTGUARD_TRAIN_MAX_SAMPLES -ErrorAction SilentlyContinue
    Write-Host "Full training mode: 4 epochs, all prepared data"
} else {
    $env:AGENTGUARD_TRAIN_QUICK = "1"
    Write-Host "Default local mode: quick training (pass -Full for production weights)"
}

Write-Host "Training DeBERTa-v3-small..."
py -3.12 training/train.py

Write-Host "Probing HF checkpoint..."
py -3.12 training/probe_checkpoint.py --hf-only
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Exporting ONNX model..."
py -3.12 training/export_onnx.py

Write-Host "Probing ONNX model..."
py -3.12 training/probe_checkpoint.py --onnx-only
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Verifying model..."
py -3.12 scripts/verify_model.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Model ready in agentguard/models/"
Write-Host "Next: .\scripts\run_benchmark_evaluation.ps1 -RequireModel"
