# AgentGuard Benchmark Dataset (Anthropic Batch v1.0)

Total adversarial: 1200 across 6 attack classes
Total benign: 5000 across 5 categories
Subtlety distribution: {1: 12, 2: 150, 3: 429, 4: 440, 5: 169}
Generation date: 2026-07-05
Batch id: msgbatch_01Mqsiry38ceBD8MLcxzL2pK
Models: claude-haiku-4-5-20251001 (benign + simpler adversarial), claude-sonnet-4-5-20250929 (high-subtlety adversarial classes)
Source tag: anthropic_batch_v1

## Provenance

- Generated via Anthropic Messages Batch API (single batch job)
- Novel inter-agent messages for AgentGuard v1.0 launch
- Chunk sizes: 20 adversarial / 40 benign per API request
