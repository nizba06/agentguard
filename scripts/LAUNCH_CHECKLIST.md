# AgentGuard v1.0 Launch Checklist

Items deferred from development to launch.

## Benchmark dataset — Anthropic Batch (novel research dataset)

**When:** v1.0 launch (Phase 5)  
**Why:** REQUIREMENTS §12.3 — first publicly available *novel* inter-agent injection dataset  
**Cost:** ~$15–40 (6 Batch API jobs)

### Steps

1. Set API key:
   ```powershell
   $env:ANTHROPIC_API_KEY = "sk-ant-..."
   ```

2. Generate full dataset:
   ```powershell
   .\scripts\run_dataset_generation.ps1
   ```
   Produces 1,200 adversarial + 5,000 benign via Claude Batch API.

3. Re-run evaluation:
   ```powershell
   .\scripts\run_benchmark_evaluation.ps1
   ```

4. Publish to Hugging Face:
   - Upload `benchmarks/dataset/adversarial.jsonl` and `benign.jsonl`
   - Dataset card citing generation methodology (claude-haiku 1–3, claude-sonnet 4–5)

5. Update `benchmarks/dataset/README.md` provenance section.

### Until launch

Use the zero-cost public-source builder:

```powershell
.\scripts\run_public_dataset_build.ps1
.\scripts\run_benchmark_evaluation.ps1
```

## Other launch items (from REQUIREMENTS §12)

- [ ] GitHub v1.0 public release
- [ ] PyPI publish (`pip install agentguard`)
- [ ] Technical blog post — draft: [docs/BLOG_POST_DRAFT.md](../docs/BLOG_POST_DRAFT.md) (fill metrics from `report.md`)
- [ ] Hugging Face dataset — card: [docs/HUGGINGFACE_DATASET_CARD.md](../docs/HUGGINGFACE_DATASET_CARD.md)
- [ ] Release notes — draft: [docs/RELEASE_NOTES_v0.1.0-draft.md](../docs/RELEASE_NOTES_v0.1.0-draft.md)
- [ ] ONNX model + SHA-256 pinned in release artifacts
