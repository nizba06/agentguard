# Upload AgentGuard benchmark dataset to Hugging Face Hub.
# Requires: pip install huggingface_hub && huggingface-cli login

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

$RepoId = if ($env:HF_DATASET_REPO) { $env:HF_DATASET_REPO } else { "nizba06/agentguard-benchmark-v0.1" }

$Adv = "benchmarks/dataset/adversarial.jsonl"
$Ben = "benchmarks/dataset/benign.jsonl"
$Card = "docs/HUGGINGFACE_DATASET_CARD.md"

foreach ($f in @($Adv, $Ben, $Card)) {
    if (-not (Test-Path $f)) {
        Write-Error "Missing file: $f (run .\scripts\run_public_dataset_build.ps1 first)"
    }
}

Write-Host "Creating/updating dataset repo: $RepoId"
py -3.12 -m pip install --quiet huggingface_hub

py -3.12 -c @"
from huggingface_hub import HfApi
api = HfApi()
repo = '$RepoId'
try:
    api.create_repo(repo, repo_type='dataset', exist_ok=True)
except Exception as e:
    print(f'Repo note: {e}')
api.upload_file(
    path_or_fileobj=r'$Adv',
    path_in_repo='adversarial.jsonl',
    repo_id=repo,
    repo_type='dataset',
    commit_message='AgentGuard v0.1 adversarial benchmark',
)
api.upload_file(
    path_or_fileobj=r'$Ben',
    path_in_repo='benign.jsonl',
    repo_id=repo,
    repo_type='dataset',
    commit_message='AgentGuard v0.1 benign benchmark',
)
api.upload_file(
    path_or_fileobj=r'$Card',
    path_in_repo='README.md',
    repo_id=repo,
    repo_type='dataset',
    commit_message='Dataset card',
)
print(f'Uploaded to https://huggingface.co/datasets/{repo}')
"@

Write-Host "Done."
