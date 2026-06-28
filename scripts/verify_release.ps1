# Pre-release verification for AgentGuard v0.1.0 / v1.0 launch
$ErrorActionPreference = "Stop"

Set-Location (Split-Path $PSScriptRoot -Parent)

function Invoke-Step($label, $command) {
    Write-Host "`n=== $label ===" -ForegroundColor Cyan
    Invoke-Expression $command
    if ($LASTEXITCODE -ne 0) {
        Write-Error "FAILED: $label (exit $LASTEXITCODE)"
    }
    Write-Host "OK: $label" -ForegroundColor Green
}

$python = $null
foreach ($candidate in @("py -3.12", "py -3.11", "python")) {
    try {
        $version = Invoke-Expression "$candidate --version" 2>$null
        if ($LASTEXITCODE -eq 0 -and $version -match "3\.(11|12)") {
            $python = $candidate
            break
        }
    } catch { }
}
if (-not $python) {
    Write-Error "Python 3.11 or 3.12 not found"
}

Write-Host "Using: $python"

Invoke-Step "ruff lint" "$python -m ruff check ."
Invoke-Step "mypy" "$python -m mypy agentguard"
Invoke-Step "pytest" "$python -m pytest -q"

Invoke-Step "benchmark smoke (200 examples)" "$python benchmarks/evaluate.py --quick"

$onnx = Join-Path (Get-Location) "agentguard/models/risk_scorer.onnx"
if (Test-Path $onnx) {
    Invoke-Step "verify ONNX model" "$python scripts/verify_model.py"
    Write-Host "`nOptional: full benchmark with model:" -ForegroundColor Yellow
    Write-Host "  .\scripts\run_benchmark_evaluation.ps1 -RequireModel"
} else {
    Write-Host "`nSKIP: verify_model.py — risk_scorer.onnx not installed" -ForegroundColor Yellow
    Write-Host "  Install via: .\scripts\run_training.ps1 -Full"
    Write-Host "           or: .\scripts\download_kaggle_model.ps1"
    Write-Host "           or: .\scripts\install_model.ps1 -SourceDir <path>"
}

Write-Host "`nAll runnable verification steps passed." -ForegroundColor Green
Write-Host "See scripts/LAUNCH_CHECKLIST.md for remaining launch gaps (PyPI, HF, Anthropic dataset)."
