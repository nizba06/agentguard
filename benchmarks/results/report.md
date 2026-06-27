## AgentGuard Benchmark Results
Generated: 2026-06-26T20:58:59.135839+00:00
ML Model Loaded: No

## Summary
| Metric | Value |
|--------|-------|
| Overall detection rate | 100.0% |
| False positive rate | 0.0% |
| P95 inspection latency | 4.9ms |
| Total adversarial examples | 30 |
| Total benign examples | 100 |

## Detection Rate by Attack Class
| Attack Class | Examples | Detected | Detection Rate | P95 Latency |
|--------------|----------|----------|----------------|-------------|
| CAPABILITY_ESCALATION | 5 | 5 | 100.0% | 1.1ms |
| GOAL_HIJACK | 5 | 5 | 100.0% | 5.6ms |
| IMPERSONATION | 5 | 5 | 100.0% | 4.3ms |
| INDIRECT_INJECTION | 5 | 5 | 100.0% | 1.9ms |
| MCP_POISONING | 5 | 5 | 100.0% | 4.3ms |
| PROPAGATION | 5 | 5 | 100.0% | 3.9ms |

## Detection by Layer
| Layer | Attacks Caught | % of Total Detected |
|-------|----------------|---------------------|
| Rule Filter | 30 | 100.0% |
| Ml Scorer | 0 | 0.0% |
| Trust Layer | 0 | 0.0% |
| Capability Layer | 0 | 0.0% |
| Consistency | 0 | 0.0% |

## Comparison: Unprotected vs AgentGuard
| Attack Class | Without AgentGuard | With AgentGuard |
|--------------|-------------------|-----------------|
| CAPABILITY_ESCALATION | 100% success | 0.0% success |
| GOAL_HIJACK | 100% success | 0.0% success |
| IMPERSONATION | 100% success | 0.0% success |
| INDIRECT_INJECTION | 100% success | 0.0% success |
| MCP_POISONING | 100% success | 0.0% success |
| PROPAGATION | 100% success | 0.0% success |
