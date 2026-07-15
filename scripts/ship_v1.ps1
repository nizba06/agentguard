# Ship AgentGuard v1.0.0 only when holdout gates pass.
# Usage:
#   .\scripts\ship_v1.ps1
#   .\scripts\ship_v1.ps1 -Apply
#   .\scripts\ship_v1.ps1 -Apply -AllowCpuLatency

param(
    [switch]$Apply,
    [switch]$AllowCpuLatency,
    [switch]$SkipModelSize
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root
$env:PYTHONPATH = $Root

Write-Host "=== verify_model (must discriminate) ===" -ForegroundColor Cyan
py -3.12 scripts/verify_model.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not (Test-Path "benchmarks/results/holdout_report.md")) {
    Write-Host "Holdout report missing - running holdout eval..." -ForegroundColor Yellow
    .\scripts\run_benchmark_evaluation.ps1 -Holdout -RequireModel
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

$gateArgs = @("scripts/check_v1_gates.py")
if ($AllowCpuLatency) { $gateArgs += "--allow-cpu-latency" }
if ($SkipModelSize) { $gateArgs += "--skip-model-size" }

Write-Host "=== v1.0 gate check ===" -ForegroundColor Cyan
py -3.12 @gateArgs
if ($LASTEXITCODE -ne 0) {
    Write-Error "Gates failed - staying on 0.1.x. Finish Kaggle retrain/export first."
}

if (-not $Apply) {
    Write-Host "Dry-run OK. Re-run with -Apply to bump pyproject to 1.0.0." -ForegroundColor Green
    exit 0
}

$pyprojectPath = Join-Path $Root "pyproject.toml"
$pyproject = Get-Content $pyprojectPath -Raw
if ($pyproject -notmatch 'version\s*=\s*"0\.') {
    Write-Error "Unexpected version in pyproject.toml - aborting bump."
}
$updated = [regex]::Replace($pyproject, 'version\s*=\s*"0\.[^"]+"', 'version = "1.0.0"', 1)
[System.IO.File]::WriteAllText($pyprojectPath, $updated)

$notesPath = Join-Path $Root "docs/RELEASE_NOTES_v1.0.0.md"
$today = Get-Date -Format "yyyy-MM-dd"
$notes = @"
# inter-agent-guard v1.0.0 — Release Notes

**Released:** $today
**PyPI:** ``inter-agent-guard`` · **Import:** ``agentguard``

## Gates (holdout source of truth)

See ``benchmarks/results/holdout_report.md`` and ``scripts/check_v1_gates.py``.

- Holdout detection / FPR meet v1.0 targets
- Default ONNX artifact is dynamic INT8 (~164 MB)
- CPU P95 remains multi-second; production high-QPS must use rules-only, GPU, or async (see ``docs/source/latency.md``)

## Install

``````bash
pip install "inter-agent-guard==1.0.0"
# Download INT8 risk_scorer.onnx + model.sha256 from GitHub Releases into agentguard/models/
``````

"@
[System.IO.File]::WriteAllText($notesPath, $notes)

Write-Host "Bumped to 1.0.0. Next: commit, tag v1.0.0, publish PyPI, attach ONNX to GitHub release." -ForegroundColor Green
