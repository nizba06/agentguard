# Push training code as a Kaggle dataset, then push the notebook kernel.
# Usage:
#   1. Edit scripts/kaggle/kernel-metadata.json - set your Kaggle username in "id"
#   2. Authenticate: py -3.12 -m kaggle auth login
#   3. .\scripts\push_kaggle_kernel.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

$KaggleDir = Join-Path $env:USERPROFILE ".kaggle"
$HasLegacyCreds = Test-Path (Join-Path $KaggleDir "kaggle.json")
$HasAccessTokenFile = Test-Path (Join-Path $KaggleDir "access_token")
$HasOAuthCreds = Test-Path (Join-Path $KaggleDir "credentials.json")
$HasAccessTokenEnv = -not [string]::IsNullOrWhiteSpace($env:KAGGLE_API_TOKEN)

if (-not ($HasLegacyCreds -or $HasAccessTokenFile -or $HasOAuthCreds -or $HasAccessTokenEnv)) {
    Write-Error "Kaggle credentials not found. Run: py -3.12 -m kaggle auth login"
}

py -3.12 -m pip install kaggle nbformat -q

$KernelMeta = Get-Content "scripts/kaggle/kernel-metadata.json" -Raw | ConvertFrom-Json
$Username = ($KernelMeta.id -split "/")[0]
$DatasetId = "$Username/agentguard-training-code"
$KernelSlug = "$Username/agentguard-deberta-risk-scorer-training"

function Invoke-Kaggle {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$KaggleArgs)
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $output = & py -3.12 -m kaggle @KaggleArgs 2>&1 | Out-String
    $exit = $LASTEXITCODE
    $ErrorActionPreference = $previous
    return [PSCustomObject]@{ Output = $output; ExitCode = $exit }
}

function Copy-TreeNoCache {
    param([string]$Source, [string]$Dest)
    robocopy $Source $Dest /E /XD __pycache__ /NFL /NDL /NJH /NJS /nc /ns /np | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "robocopy failed for $Source" }
}

Write-Host "Normalizing notebook cell IDs..."
py -3.12 -c @"
import uuid
import nbformat
from pathlib import Path
path = Path('training/kaggle_notebook.ipynb')
nb = nbformat.read(path.open(encoding='utf-8'), as_version=4)
for cell in nb.cells:
    if 'id' not in cell:
        cell['id'] = uuid.uuid4().hex[:8]
nbformat.write(nb, path.open('w', encoding='utf-8'))
"@

Write-Host "Uploading training code dataset: $DatasetId"

$BundleRoot = Join-Path $env:TEMP "agentguard-kaggle-bundle"
if (Test-Path $BundleRoot) { Remove-Item $BundleRoot -Recurse -Force }
New-Item -ItemType Directory -Path $BundleRoot | Out-Null

Copy-TreeNoCache "training" (Join-Path $BundleRoot "training")
Copy-TreeNoCache "agentguard" (Join-Path $BundleRoot "agentguard")
if (Test-Path "benchmarks") {
    Copy-TreeNoCache "benchmarks" (Join-Path $BundleRoot "benchmarks")
} else {
    New-Item -ItemType Directory -Path (Join-Path $BundleRoot "benchmarks/dataset") -Force | Out-Null
}

$AdvJsonl = Join-Path $BundleRoot "benchmarks/dataset/adversarial.jsonl"
$BenJsonl = Join-Path $BundleRoot "benchmarks/dataset/benign.jsonl"
if (-not (Test-Path $AdvJsonl) -or -not (Test-Path $BenJsonl)) {
    Write-Error @"
Anthropic benchmark JSONL missing from the Kaggle bundle.
Expected:
  benchmarks/dataset/adversarial.jsonl
  benchmarks/dataset/benign.jsonl
Restore the corpus (HF download or local copy), then re-run this script.
"@
}
$AdvLines = (Get-Content $AdvJsonl | Measure-Object -Line).Lines
$BenLines = (Get-Content $BenJsonl | Measure-Object -Line).Lines
Write-Host "Bundling Anthropic corpus: $AdvLines adversarial + $BenLines benign"

$DatasetStage = Join-Path $env:TEMP "agentguard-kaggle-dataset"
if (Test-Path $DatasetStage) { Remove-Item $DatasetStage -Recurse -Force }
New-Item -ItemType Directory -Path $DatasetStage | Out-Null

$CodeZip = Join-Path $DatasetStage "agentguard-code.zip"
if (Test-Path $CodeZip) { Remove-Item $CodeZip -Force }
Compress-Archive -Path (Join-Path $BundleRoot "*") -DestinationPath $CodeZip -Force

Write-Host "Verifying bundle before upload..."
$TrainPy = Join-Path $BundleRoot "training/train.py"
$ProbePy = Join-Path $BundleRoot "training/probe_checkpoint.py"
$ScoringPy = Join-Path $BundleRoot "training/scoring.py"
$TokPy = Join-Path $BundleRoot "training/tokenizer_utils.py"
foreach ($Required in @($TrainPy, $ProbePy, $ScoringPy, $TokPy)) {
    if (-not (Test-Path $Required)) {
        Write-Error "Bundle incomplete: missing $Required"
    }
}
$TrainText = Get-Content $TrainPy -Raw
if ($TrainText -match '\(r for r in train_rows') {
    Write-Error "Stale generator-slice bug still present in bundle training/train.py — aborting upload."
}
$ProbeText = Get-Content $ProbePy -Raw
if ($ProbeText -notmatch 'mean_injection_probability') {
    Write-Error "Bundle probe_checkpoint.py is missing mean_injection_probability — aborting upload."
}
$env:PYTHONPATH = $BundleRoot
$ImportCheck = & py -3.12 -c @"
from training.scoring import resolve_probe_texts, PROBE_MIN_GAP
from training import probe_checkpoint, export_onnx, train
assert callable(probe_checkpoint.resolve_probe_texts)
print('bundle-import-ok', PROBE_MIN_GAP)
"@ 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "Bundle import smoke failed:`n$ImportCheck"
}
Write-Host $ImportCheck

$DatasetMetaPath = Join-Path $DatasetStage "dataset-metadata.json"
$DatasetMetaText = (Get-Content "scripts/kaggle/dataset-metadata.json" -Raw) -replace '"id": "[^"]+"', "`"id`": `"$DatasetId`""
[System.IO.File]::WriteAllText($DatasetMetaPath, $DatasetMetaText)

Set-Location $DatasetStage
$Create = Invoke-Kaggle datasets create -p . -q
if ($Create.ExitCode -ne 0 -or $Create.Output -match 'Dataset creation error|already in use|already exists|409|duplicate') {
    if ($Create.Output -match 'already in use|already exists|409|duplicate|Dataset creation error') {
        Write-Host "Dataset exists - uploading new version..."
        $Version = Invoke-Kaggle datasets version -p . -q -m "Update AgentGuard training code bundle"
        if ($Version.ExitCode -ne 0) { Write-Error $Version.Output }
        Write-Host $Version.Output
    } else {
        Write-Error $Create.Output
    }
} else {
    Write-Host $Create.Output
}

Write-Host "Waiting 90s for the new dataset version to become attachable..."
Start-Sleep -Seconds 90

Set-Location $Root

$KernelStage = Join-Path $env:TEMP "agentguard-kaggle-kernel"
if (Test-Path $KernelStage) { Remove-Item $KernelStage -Recurse -Force }
New-Item -ItemType Directory -Path $KernelStage | Out-Null

Copy-Item -Path "training/kaggle_notebook.ipynb" -Destination (Join-Path $KernelStage "kaggle_notebook.ipynb")
$KernelMetaPath = Join-Path $KernelStage "kernel-metadata.json"
$KernelMetaText = (Get-Content "scripts/kaggle/kernel-metadata.json" -Raw) -replace '"dataset_sources": \[[^\]]*\]', "`"dataset_sources`": [`"$DatasetId`"]"
[System.IO.File]::WriteAllText($KernelMetaPath, $KernelMetaText)

Set-Location $KernelStage
$Push = Invoke-Kaggle kernels push -p . --accelerator NvidiaTeslaT4
Write-Host $Push.Output
if ($Push.Output -match 'not valid dataset sources|could not be added') {
    Write-Error "Kernel push did not attach dataset $DatasetId. Wait 1-2 min and re-run this script."
}
if ($Push.ExitCode -ne 0) { Write-Error "Kernel push failed.`n$($Push.Output)" }

Write-Host ""
Write-Host "Kernel pushed with dataset $DatasetId attached."
Write-Host "Watch progress: https://www.kaggle.com/code/$KernelSlug"
Write-Host ""
Write-Host "CLI push already starts a background run. Cancel duplicate Active Events if any."
Write-Host "After success (logs must show HF/ONNX probe PASS):"
Write-Host "  .\scripts\download_kaggle_model.ps1"
Write-Host "  py -3.12 scripts/verify_model.py"
