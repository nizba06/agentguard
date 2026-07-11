# Fail fast if common pre-public mistakes are present.
# Usage: .\scripts\pre_public_check.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

$fail = @()

function Fail($msg) { $script:fail += $msg }

foreach ($name in @("LICENSE", "README.md")) {
    if (-not (Test-Path $name)) { Fail "Missing $name" }
}

$secretPatterns = @(
    "\.env$",
    "\.pem$",
    "credentials\.json$",
    "secrets\.json$",
    "\.pypirc$"
)
$tracked = git ls-files
foreach ($path in $tracked) {
    foreach ($pat in $secretPatterns) {
        if ($path -match $pat) { Fail "Tracked secret/credential file: $path" }
    }
    if ($path -match "\.onnx$") { Fail "Tracked ONNX (use GitHub Release): $path" }
    if ($path -match "benchmarks/dataset/.*\.jsonl$") { Fail "Tracked benchmark JSONL: $path" }
    if ($path -match "kaggle-model-pull/") { Fail "Tracked Kaggle pull dir: $path" }
}

$large = @()
$fiftyMb = 50 * 1024 * 1024
foreach ($path in $tracked) {
    if (-not (Test-Path -LiteralPath $path)) { continue }
    $len = (Get-Item -LiteralPath $path).Length
    if ($len -gt $fiftyMb) {
        $large += [PSCustomObject]@{ MB = [math]::Round($len / 1MB, 1); Path = $path }
    }
}
if ($large.Count -gt 0) {
    $parts = $large | ForEach-Object { "$($_.Path) ($($_.MB) MB)" }
    Fail ("Large tracked files (>50 MB): " + ($parts -join ", "))
}

$keyHits = git grep -I -E "sk-ant-api03-[A-Za-z0-9]{20,}|hf_[A-Za-z0-9]{30,}" HEAD 2>$null
if ($keyHits) {
    Fail "Possible real API key/token in tracked files (git grep matched)"
}

Write-Host "Pre-public check for $Root"
Write-Host "Tracked files: $($tracked.Count)"
if ($large.Count -gt 0) {
    Write-Host "Large tracked files (review):"
    $large | Format-Table -AutoSize
}

if ($fail.Count -eq 0) {
    Write-Host "PASS - no blocking issues found."
    Write-Host "Manual: GitHub Settings -> Collaborators; Actions secrets; Change visibility."
    exit 0
}

Write-Host "FAIL - $($fail.Count) issue(s):"
$fail | ForEach-Object { Write-Host "  - $_" }
exit 1
