# Generate the 6,200-example benchmark dataset via Anthropic Batch API (ONE batch job).
# FOR v1.0 LAUNCH ONLY — see scripts/LAUNCH_CHECKLIST.md
#
# Usage:
#   $env:ANTHROPIC_API_KEY = "sk-ant-..."
#   .\scripts\run_dataset_generation.ps1 -DryRun          # plan + cost, no API calls
#   .\scripts\run_dataset_generation.ps1                  # full single-batch run
#   .\scripts\run_dataset_generation.ps1 -TopUp           # fill deficits only (if needed)
#
# Zero-cost dev alternative: .\scripts\run_public_dataset_build.ps1

param(
    [switch]$DryRun,
    [switch]$TopUp,
    [switch]$SkipConfirm
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

if (-not $env:ANTHROPIC_API_KEY) {
    Write-Error @"
ANTHROPIC_API_KEY is not set.

Manual steps:
  1. Create an API key at https://console.anthropic.com/settings/keys
  2. Add billing / prepaid credits (~`$25 recommended headroom)
  3. In PowerShell:
       `$env:ANTHROPIC_API_KEY = "sk-ant-..."
"@
}

Write-Host "Installing anthropic SDK..."
py -3.12 -m pip install "anthropic>=0.40" -q

if ($DryRun) {
    py -3.12 benchmarks/generate_dataset.py --dry-run
    exit $LASTEXITCODE
}

# Always show plan before spending money
Write-Host "`n--- Pre-flight plan ---"
py -3.12 benchmarks/generate_dataset.py --dry-run
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipConfirm -and -not $TopUp) {
    Write-Host "`nThis submits ONE Anthropic Batch job (~185 requests, ~`$15-`$35 USD)."
    Write-Host "Dataset saves partial results on count deficits; use -TopUp to fill gaps."
    $confirm = Read-Host "Type YES to proceed"
    if ($confirm.ToUpperInvariant() -ne "YES") {
        Write-Host "Aborted."
        exit 0
    }
}

# Backup existing public-source dataset before overwrite
$DatasetDir = Join-Path $Root "benchmarks/dataset"
if ((Test-Path (Join-Path $DatasetDir "adversarial.jsonl")) -and -not $TopUp) {
    $Backup = Join-Path $Root ("benchmarks/dataset_backup_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
    Write-Host "Backing up current dataset to $Backup"
    Copy-Item $DatasetDir $Backup -Recurse
}

$Args = @("benchmarks/generate_dataset.py")
if ($TopUp) { $Args += "--top-up" }

Write-Host "`nStarting generation (expect 30-120 minutes)..."
py -3.12 @Args
$genExit = $LASTEXITCODE

Write-Host "`n--- Post-generation counts ---"
if (Test-Path "benchmarks/dataset/adversarial.jsonl") {
    $adv = (Get-Content "benchmarks/dataset/adversarial.jsonl" | Measure-Object -Line).Lines
    $ben = (Get-Content "benchmarks/dataset/benign.jsonl" | Measure-Object -Line).Lines
    Write-Host "Adversarial: $adv (target 1200)"
    Write-Host "Benign:      $ben (target 5000)"
    if ($genExit -ne 0 -and ($adv -lt 1200 -or $ben -lt 5000)) {
        Write-Host "`nPartial dataset saved. Top up deficits with:"
        Write-Host "  .\scripts\run_dataset_generation.ps1 -TopUp -SkipConfirm"
        exit $genExit
    }
} elseif ($genExit -ne 0) {
    exit $genExit
}

Write-Host @"

Done. Next manual steps:
  1. Re-run benchmark:  .\scripts\run_benchmark_evaluation.ps1 -RequireModel
  2. Publish HF:        .\scripts\publish_huggingface.ps1
  3. Update docs/HUGGINGFACE_DATASET_CARD.md provenance section
  4. Commit dataset + generation_manifest.json (if policy allows) or attach to GitHub release

If validation failed, review benchmarks/dataset/generation_errors.txt
and run: .\scripts\run_dataset_generation.ps1 -TopUp
"@
