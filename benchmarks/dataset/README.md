# AgentGuard Benchmark Dataset (Public Sources v0.1)

Total adversarial: 1200 across 6 attack classes
Total benign: 5000 across 5 categories
Subtlety distribution: {3: 410, 2: 438, 4: 124, 1: 228}
Generation date: 2026-06-27

## Provenance

- Adversarial payloads: InjectAgent (Hugging Face) + Agent-IPI (optional)
- Inter-agent framing: AgentGuard template library
- Benign messages: pipeline-style templates (LangGraph/CrewAI patterns)
- Cost: $0 (no LLM API calls)

## Launch upgrade

For v1.0, regenerate with Anthropic Batch API — see `scripts/LAUNCH_CHECKLIST.md`.

InjectAgent payloads used: 62
Agent-IPI payloads used: 0
