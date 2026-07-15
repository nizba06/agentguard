# Copy model artifacts into agentguard/models/
# Usage: .\scripts\install_model.ps1 -SourceDir .\kaggle-model-pull\agentguard\models

param(
    [Parameter(Mandatory = $true)]
    [string]$SourceDir
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
$Dest = Join-Path $Root "agentguard/models"
$Required = @("risk_scorer.onnx", "model.sha256", "tokenizer.json", "tokenizer_config.json")
$Optional = @("scorer_config.json", "spm.model", "special_tokens_map.json", "added_tokens.json")

if (-not (Test-Path $SourceDir)) {
    Write-Error "Source directory not found: $SourceDir"
}

New-Item -ItemType Directory -Path $Dest -Force | Out-Null
foreach ($name in $Required) {
    $src = Join-Path $SourceDir $name
    if (-not (Test-Path $src)) {
        Write-Error "Missing required artifact: $src"
    }
    Copy-Item $src (Join-Path $Dest $name) -Force
    Write-Host "Installed $name"
}
foreach ($name in $Optional) {
    $src = Join-Path $SourceDir $name
    if (Test-Path $src) {
        Copy-Item $src (Join-Path $Dest $name) -Force
        Write-Host "Installed $name"
    }
}

Write-Host "Verifying installed model..."
Set-Location $Root
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
$env:PYTHONPATH = $Root
py -3.12 scripts/verify_model.py
exit $LASTEXITCODE
