## AgentGuard Benchmark Results
Generated: 2026-07-11T20:45:37.681542+00:00
ML Model Loaded: Yes

## Summary
| Metric | Value |
|--------|-------|
| Overall detection rate | 40.2% |
| False positive rate | 42.2% |
| P95 inspection latency | 805.3ms |
| Total adversarial examples | 1200 |
| Total benign examples | 5000 |

## False Positives by Layer
| Layer | Benign Flagged |
|-------|----------------|
| Rule Filter | 2 |
| Ml Scorer | 1457 |
| Trust Layer | 0 |
| Consistency | 650 |
| Unknown | 0 |

## Detection Rate by Attack Class
| Attack Class | Examples | Detected | Detection Rate | P95 Latency |
|--------------|----------|----------|----------------|-------------|
| CAPABILITY_ESCALATION | 200 | 200 | 100.0% | 1.2ms |
| GOAL_HIJACK | 200 | 34 | 17.0% | 845.0ms |
| IMPERSONATION | 200 | 200 | 100.0% | 1041.1ms |
| INDIRECT_INJECTION | 200 | 22 | 11.0% | 741.4ms |
| MCP_POISONING | 200 | 19 | 9.5% | 896.8ms |
| PROPAGATION | 200 | 8 | 4.0% | 781.0ms |

## Detection by Layer
| Layer | Attacks Caught | % of Total Detected |
|-------|----------------|---------------------|
| Rule Filter | 29 | 6.0% |
| Ml Scorer | 33 | 6.8% |
| Trust Layer | 200 | 41.4% |
| Capability Layer | 200 | 41.4% |
| Consistency | 21 | 4.3% |

## Comparison: Unprotected vs AgentGuard
| Attack Class | Without AgentGuard | With AgentGuard |
|--------------|-------------------|-----------------|
| CAPABILITY_ESCALATION | 100% success | 0.0% success |
| GOAL_HIJACK | 100% success | 83.0% success |
| IMPERSONATION | 100% success | 0.0% success |
| INDIRECT_INJECTION | 100% success | 89.0% success |
| MCP_POISONING | 100% success | 90.5% success |
| PROPAGATION | 100% success | 96.0% success |
