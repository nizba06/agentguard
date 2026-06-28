## AgentGuard Benchmark Results
Generated: 2026-06-30T17:38:58.702297+00:00
ML Model Loaded: Yes

## Summary
| Metric | Value |
|--------|-------|
| Overall detection rate | 97.1% |
| False positive rate | 0.0% |
| P95 inspection latency | 1059.9ms |
| Total adversarial examples | 1200 |
| Total benign examples | 5000 |

## False Positives by Layer
| Layer | Benign Flagged |
|-------|----------------|
| Rule Filter | 0 |
| Ml Scorer | 0 |
| Trust Layer | 0 |
| Consistency | 0 |
| Unknown | 0 |

## Detection Rate by Attack Class
| Attack Class | Examples | Detected | Detection Rate | P95 Latency |
|--------------|----------|----------|----------------|-------------|
| CAPABILITY_ESCALATION | 200 | 200 | 100.0% | 1.5ms |
| GOAL_HIJACK | 200 | 200 | 100.0% | 1039.4ms |
| IMPERSONATION | 200 | 200 | 100.0% | 960.6ms |
| INDIRECT_INJECTION | 200 | 190 | 95.0% | 964.1ms |
| MCP_POISONING | 200 | 186 | 93.0% | 1035.7ms |
| PROPAGATION | 200 | 189 | 94.5% | 899.4ms |

## Detection by Layer
| Layer | Attacks Caught | % of Total Detected |
|-------|----------------|---------------------|
| Rule Filter | 467 | 40.1% |
| Ml Scorer | 474 | 40.7% |
| Trust Layer | 1 | 0.1% |
| Capability Layer | 200 | 17.2% |
| Consistency | 23 | 2.0% |

## Comparison: Unprotected vs AgentGuard
| Attack Class | Without AgentGuard | With AgentGuard |
|--------------|-------------------|-----------------|
| CAPABILITY_ESCALATION | 100% success | 0.0% success |
| GOAL_HIJACK | 100% success | 0.0% success |
| IMPERSONATION | 100% success | 0.0% success |
| INDIRECT_INJECTION | 100% success | 5.0% success |
| MCP_POISONING | 100% success | 7.0% success |
| PROPAGATION | 100% success | 5.5% success |
