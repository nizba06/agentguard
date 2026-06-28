# Download trained model artifacts from Kaggle kernel output.
# Usage:
#   1. py -3.12 -m kaggle auth login
#   2. .\scripts\download_kaggle_model.ps1
#   3. .\scripts\download_kaggle_model.ps1 -KernelSlug "youruser/agentguard-deberta-risk-scorer-training"

param(
    [string]$KernelSlug = "nizbau/agentguard-deberta-risk-scorer-training",
    [string]$OutputDir = "kaggle-model-pull"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

# Kaggle CLI is Python; avoid Windows cp1252 failures on unicode log/output paths
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

$KaggleDir = Join-Path $env:USERPROFILE ".kaggle"
$HasLegacyCreds = Test-Path (Join-Path $KaggleDir "kaggle.json")
$HasAccessTokenFile = Test-Path (Join-Path $KaggleDir "access_token")
$HasOAuthCreds = Test-Path (Join-Path $KaggleDir "credentials.json")
$HasAccessTokenEnv = -not [string]::IsNullOrWhiteSpace($env:KAGGLE_API_TOKEN)

if (-not ($HasLegacyCreds -or $HasAccessTokenFile -or $HasOAuthCreds -or $HasAccessTokenEnv)) {
    Write-Error "Kaggle credentials not found. Run: py -3.12 -m kaggle auth login"
}

py -3.12 -m pip install kaggle -q

if (Test-Path $OutputDir) { Remove-Item $OutputDir -Recurse -Force }
New-Item -ItemType Directory -Path $OutputDir | Out-Null

Write-Host "Downloading kernel output: $KernelSlug"
py -3.12 -m kaggle kernels output $KernelSlug -p $OutputDir
$KaggleExit = $LASTEXITCODE

$OnnxCandidates = @(
    (Join-Path $OutputDir "agentguard/models/risk_scorer.onnx"),
    (Join-Path $OutputDir "risk_scorer.onnx")
)
$FoundOnnxEarly = $OnnxCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($KaggleExit -ne 0 -and -not $FoundOnnxEarly) {
    exit $KaggleExit
}
if ($KaggleExit -ne 0 -and $FoundOnnxEarly) {
    Write-Host "Kaggle exited with code $KaggleExit (often a Windows unicode console issue)."
    Write-Host "Model artifacts are present - continuing with install."
}

$FoundOnnx = $FoundOnnxEarly

if (-not $FoundOnnx) {
    $Checkpoint = Join-Path $OutputDir "training/checkpoints/best"
    if (Test-Path $Checkpoint) {
        Write-Host "ONNX not in kernel output; exporting from checkpoint..."
        py -3.12 -m pip install -q transformers optimum[onnxruntime] onnxruntime
        Push-Location $OutputDir
        py -3.12 training/export_onnx.py
        Pop-Location
        $FoundOnnx = Join-Path $OutputDir "agentguard/models/risk_scorer.onnx"
    }
}

if (-not (Test-Path $FoundOnnx)) {
    Write-Error 'risk_scorer.onnx not found. Re-run Kaggle training or use .\scripts\run_training.ps1'
}

Write-Host "Installing model artifacts into agentguard/models/..."
& (Join-Path $PSScriptRoot "install_model.ps1") -SourceDir (Split-Path $FoundOnnx -Parent)
