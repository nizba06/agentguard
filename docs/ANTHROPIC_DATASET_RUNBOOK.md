# Anthropic Batch Dataset Generation — Manual Runbook

One-time cost (~**$15–35 USD**) to produce the v1.0 novel benchmark corpus.

## What changed (code fixes)

The original generator asked for **200–1000 examples per API call** with only **8192 output tokens**, which would truncate and fail validation. The updated pipeline:

- Submits **one Batch job** with **~185 small requests** (20 adversarial / 40 benign per request)
- **Validates exact counts** (1200 adversarial + 5000 benign) before saving
- **Does not overwrite** files if validation fails
- Supports **`--top-up`** to fill only missing rows (minimal extra cost if needed)
- Backs up your existing dataset before overwrite

---

## Manual steps (do in order)

### 1. Anthropic account setup

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. **Settings → Billing** — add payment method / credits (**$25 headroom** recommended)
3. **Settings → API keys** — create a key (`sk-ant-...`)
4. Ensure Batch API access is enabled for your account (same key as Messages API)

### 2. Set API key (PowerShell)

```powershell
cd C:\Users\ummen\OneDrive\Documents\Workspace\agentguard

$env:ANTHROPIC_API_KEY = "sk-ant-api03-..."   # your key — do NOT commit this
```

### 3. Dry run (free — no API calls)

```powershell
.\scripts\run_dataset_generation.ps1 -DryRun
```

Confirm output shows:
- **ONE batch** with ~185 requests
- Target **6200** examples (1200 + 5000)
- Estimated cost **$15–35**

### 4. Run generation (single batch, ~30–120 min)

```powershell
.\scripts\run_dataset_generation.ps1
```

When prompted, type **`YES`** to submit the batch.

The script will:
- Back up `benchmarks/dataset/` to `benchmarks/dataset_backup_<timestamp>/`
- Poll until the batch completes
- Validate counts per attack class and benign category
- Save only if perfect:
  - `benchmarks/dataset/adversarial.jsonl`
  - `benchmarks/dataset/benign.jsonl`
  - `benchmarks/dataset/README.md`
  - `benchmarks/dataset/generation_manifest.json`

### 5. If validation fails (do NOT re-run full batch first)

```powershell
# Review errors
Get-Content benchmarks\dataset\generation_errors.txt

# Fill only missing rows (cheaper)
.\scripts\run_dataset_generation.ps1 -TopUp -SkipConfirm
```

### 6. Verify benchmark still works

Requires ONNX model installed:

```powershell
.\scripts\run_benchmark_evaluation.ps1 -RequireModel
```

Review `benchmarks/results/report.md`.

### 7. Publish to Hugging Face

```powershell
# Requires: pip install huggingface_hub, HF token
$env:HF_TOKEN = "hf_..."
# Optional: $env:HF_DATASET_REPO = "Nizba/agentguard-benchmark-v1"
.\scripts\publish_huggingface.ps1
```

### 8. Update documentation

- Edit `docs/HUGGINGFACE_DATASET_CARD.md` — change provenance from v0.1 public-source to Anthropic Batch v1.0
- Update `benchmarks/dataset/README.md` (auto-generated, review provenance section)
- Refresh blog draft metrics if publishing

### 9. Commit (optional policy)

Large JSONL files may be gitignored. Options:
- Attach to **GitHub Release** as artifacts, or
- Rely on **Hugging Face** as canonical source and keep gitignore

---

## Cost control summary

| Action | Cost |
|--------|------|
| `--dry-run` / `-DryRun` | **$0** |
| Full single batch | **~$15–35 once** |
| `-TopUp` (if needed) | **Only missing chunks** |
| Hugging Face public dataset | **$0** |
| Re-running benchmarks locally | **$0** |

Anthropic is **never** called at AgentGuard runtime — only this one-time dataset job.

---

## Expected output schema

**Adversarial** (200 per class × 6 classes):

```json
{
  "message_text": "...",
  "attack_class": "INDIRECT_INJECTION",
  "target_agent": "researcher",
  "subtlety_level": 3,
  "expected_detection_layer": "both",
  "reasoning": "...",
  "source": "anthropic_batch_v1",
  "label": 1
}
```

**Benign** (1000 per category × 5 categories):

```json
{
  "message_text": "...",
  "label": 0,
  "category": "task_delegation",
  "source": "anthropic_batch_v1"
}
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `ANTHROPIC_API_KEY is not set` | Export key in same PowerShell session |
| Batch `errored` requests | Check Anthropic console → Batches → error details |
| Count short after run | Use `-TopUp`, not full re-run |
| `RequireModel` benchmark fails | Install ONNX: `.\scripts\install_model.ps1` |
| Rate / billing errors | Add credits in Anthropic console |

Check batch status in console: [console.anthropic.com/settings/batches](https://console.anthropic.com/settings/batches)
