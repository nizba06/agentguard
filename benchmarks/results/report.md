## AgentGuard Benchmark Results
Generated: 2026-07-12T17:35:50.763541+00:00
ML Model Loaded: Yes

## Summary
| Metric | Value |
|--------|-------|
| Overall detection rate | 37.1% |
| False positive rate | 28.9% |
| P95 inspection latency | 1592.9ms |
| Total adversarial examples | 1200 |
| Total benign examples | 5000 |

## False Positives by Layer
| Layer | Benign Flagged |
|-------|----------------|
| Rule Filter | 0 |
| Ml Scorer | 788 |
| Trust Layer | 0 |
| Consistency | 658 |
| Unknown | 0 |

## Detection Rate by Attack Class
| Attack Class | Examples | Detected | Detection Rate | P95 Latency |
|--------------|----------|----------|----------------|-------------|
| CAPABILITY_ESCALATION | 200 | 200 | 100.0% | 1.0ms |
| GOAL_HIJACK | 200 | 11 | 5.5% | 763.6ms |
| IMPERSONATION | 200 | 200 | 100.0% | 642.4ms |
| INDIRECT_INJECTION | 200 | 19 | 9.5% | 570.4ms |
| MCP_POISONING | 200 | 13 | 6.5% | 625.9ms |
| PROPAGATION | 200 | 2 | 1.0% | 600.9ms |

## Detection by Layer
| Layer | Attacks Caught | % of Total Detected |
|-------|----------------|---------------------|
| Rule Filter | 27 | 6.1% |
| Ml Scorer | 4 | 0.9% |
| Trust Layer | 200 | 44.9% |
| Capability Layer | 200 | 44.9% |
| Consistency | 14 | 3.1% |

## Comparison: Unprotected vs AgentGuard
| Attack Class | Without AgentGuard | With AgentGuard |
|--------------|-------------------|-----------------|
| CAPABILITY_ESCALATION | 100% success | 0.0% success |
| GOAL_HIJACK | 100% success | 94.5% success |
| IMPERSONATION | 100% success | 0.0% success |
| INDIRECT_INJECTION | 100% success | 90.5% success |
| MCP_POISONING | 100% success | 93.5% success |
| PROPAGATION | 100% success | 99.0% success |
