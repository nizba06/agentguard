# Create GitHub release and attach ONNX model artifacts.
# Prerequisites: gh auth login
#
# Usage:
#   .\scripts\create_github_release.ps1
#   .\scripts\create_github_release.ps1 -Tag v1.0.0

param(
    [string]$Tag = "v1.0.0"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

$gh = "$env:ProgramFiles\GitHub CLI\gh.exe"
if (-not (Test-Path $gh)) {
    $gh = (Get-Command gh -ErrorAction Stop).Source
}

& $gh auth status
if ($LASTEXITCODE -ne 0) {
    Write-Error "Not logged in. Run: gh auth login"
}

$onnx = Join-Path $Root "agentguard/models/risk_scorer.onnx"
$hashFile = Join-Path $Root "agentguard/models/model.sha256"
$notes = Join-Path $Root "docs/RELEASE_NOTES_v1.0.0.md"

foreach ($path in @($onnx, $hashFile, $notes)) {
    if (-not (Test-Path $path)) {
        Write-Error "Missing required file: $path"
    }
}

$expected = (Get-Content $hashFile -Raw).Trim().ToLowerInvariant()
$actual = (Get-FileHash $onnx -Algorithm SHA256).Hash.ToLowerInvariant()
if ($expected -ne $actual) {
    Write-Error "ONNX hash mismatch. expected=$expected actual=$actual"
}

$git = "C:\Program Files\Git\bin\git.exe"
$existing = & $git tag -l $Tag
if (-not $existing) {
    & $git tag $Tag
    Write-Host "Created local tag $Tag"
}
& $git push origin $Tag

Write-Host "Creating GitHub release $Tag with ONNX artifacts..."
& $gh release create $Tag `
    --title "AgentGuard $Tag" `
    --notes-file $notes `
    $onnx `
    $hashFile

Write-Host "Done. Open: https://github.com/nizba06/agentguard/releases/tag/$Tag"
