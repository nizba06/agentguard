## AgentGuard Benchmark Results
Generated: 2026-07-15T14:05:20.120583+00:00
ML Model Loaded: Yes

## Summary
| Metric | Value |
|--------|-------|
| Overall detection rate | 99.4% |
| False positive rate | 0.0% |
| P95 inspection latency | 3356.1ms |
| Total adversarial examples | 160 |
| Total benign examples | 1000 |

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
| GOAL_HIJACK | 37 | 36 | 97.3% | 1271.0ms |
| INDIRECT_INJECTION | 43 | 43 | 100.0% | 1084.1ms |
| MCP_POISONING | 46 | 46 | 100.0% | 1357.8ms |
| PROPAGATION | 34 | 34 | 100.0% | 1186.3ms |

## Detection by Layer
| Layer | Attacks Caught | % of Total Detected |
|-------|----------------|---------------------|
| Rule Filter | 8 | 5.0% |
| Ml Scorer | 151 | 95.0% |
| Trust Layer | 0 | 0.0% |
| Capability Layer | 0 | 0.0% |
| Consistency | 0 | 0.0% |

## Comparison: Unprotected vs AgentGuard
| Attack Class | Without AgentGuard | With AgentGuard |
|--------------|-------------------|-----------------|
| GOAL_HIJACK | 100% success | 2.7% success |
| INDIRECT_INJECTION | 100% success | 0.0% success |
| MCP_POISONING | 100% success | 0.0% success |
| PROPAGATION | 100% success | 0.0% success |
