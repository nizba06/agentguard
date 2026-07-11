# AgentGuard vs Microsoft Agent Governance Toolkit

**Status:** Positioning + shared-attack methodology for REQUIREMENTS §12.3.  
**Toolkit:** [microsoft/agent-governance-toolkit](https://github.com/microsoft/agent-governance-toolkit) (MIT)  
**AgentGuard:** [nizba06/agentguard](https://github.com/nizba06/agentguard) — `pip install inter-agent-guard`

The tools are **complementary**. AGT is a broad governance/policy platform;
AgentGuard is a pip-installable **content-aware inter-agent firewall**.

## Feature matrix

| Capability | AgentGuard | Microsoft AGT |
|------------|------------|---------------|
| Inter-agent message **semantic** inspection (ML + rules) | Yes (DeBERTa ONNX + Aho-Corasick) | Policy/metadata focused; not a content ML firewall |
| Capability / tool allow–deny manifests | Yes (YAML + JSON Schema) | Yes (YAML policy engine) |
| Cryptographic agent identity | Ephemeral Ed25519 (PyNaCl) | DIDs / Ed25519 trust stack |
| MCP tool-return poisoning inspection | Yes (`wrap_mcp_tool`) | MCP gateway / governance (policy) |
| Zero-infra `pip install` + `guard.wrap(graph)` | Yes | Richer stack; multi-package / sidecar options |
| OWASP Agentic Top 10 compliance CLI | Partial (security controls) | First-class (`agt verify`, 10/10 mapping) |
| Multi-language SDKs | Python | Python, TS, .NET, Rust, Go |
| Sub-ms policy decisions | N/A (ML path ~1 s CPU) | Designed for deterministic sub-ms policy |

## What each catches on the AgentGuard corpus

Shared attack classes from [Nizba/agentguard-benchmark-v1](https://huggingface.co/datasets/Nizba/agentguard-benchmark-v1):

| Attack class | Metadata / tool policy (AGT-style) | Content inspection (AgentGuard) |
|--------------|------------------------------------|----------------------------------|
| CAPABILITY_ESCALATION | Strong (deny `publish_external`) | Strong (manifest + rules) |
| IMPERSONATION | Strong if identity/trust enforced | Strong (trust verifier) |
| GOAL_HIJACK | Weak unless policy matches text patterns | Rules + ML + consistency |
| INDIRECT_INJECTION | Weak on novel phrasing | Rules + ML |
| MCP_POISONING | Policy on tool *calls*; weak on poisoned *returns* unless return inspection exists | Dedicated MCP output inspector |
| PROPAGATION | Depends on hop policies | Inspect every hop via adapters |

**Takeaway:** AGT excels at identity, rings, and declarative action policy.
AgentGuard excels when the attack is **inside an otherwise-allowed message**
(goal hijack, indirect injection, poisoned tool output text).

## Empirical methodology (shared dataset)

1. Sample adversarial + benign rows from `benchmarks/dataset/*.jsonl` or HF.
2. **Baseline:** unprotected pipeline (see `examples/vulnerable_pipeline`).
3. **AgentGuard:** `.\scripts\run_benchmark_evaluation.ps1 -RequireModel` → ASR / FPR / P95.
4. **AGT:** wrap the same tools with `agentmesh.governance.govern(..., policy=...)`
   using tool allowlists only (no message body ML). Record allow/deny per case.
5. Report attack success rate by class for: unprotected | AGT-policy | AgentGuard | both.

Helper that runs the AgentGuard side and prints the class positioning table:

```powershell
py -3.12 scripts/run_toolkit_comparison.py
```

Full dual-stack numbers require installing AGT separately:

```bash
pip install "agent-governance-toolkit[full]"
```

## Recommended joint deployment

```text
[Agent framework]
      │
      ├─ AGT policy / identity  →  tool & action allow–deny
      │
      └─ AgentGuard wrap()      →  message + MCP return content inspection
```

Use AGT for enterprise governance and OWASP mapping; add AgentGuard where
semantic injection between agents is the residual risk.

## References

- Microsoft Open Source Blog (2026-04-02): Introducing the Agent Governance Toolkit  
- Docs: https://microsoft.github.io/agent-governance-toolkit/  
- AgentGuard blog: [blog](blog.md)  
- REQUIREMENTS §3.1, §12.3
