# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | -------------------- |
| 0.1.x   | :white_check_mark:   |

## Reporting a Vulnerability

If you discover a security vulnerability in AgentGuard, please report it responsibly.

1. **Do not** open a public GitHub issue for exploitable vulnerabilities.
2. Open a [private security advisory](https://github.com/nizba06/agentguard/security/advisories/new) on GitHub, or email **nizba06@users.noreply.github.com** with the details below.
3. Include:
   - A description of the issue and affected components (Message Inspector, Trust Verifier, Capability Enforcer)
   - Steps to reproduce, including sample messages or manifests if applicable
   - Impact assessment (bypass, false negative, false positive, audit tampering)
   - Your suggested fix, if any

We aim to acknowledge reports within **5 business days** and provide a remediation timeline within **14 business days** for confirmed issues.

## Scope

In scope:

- Runtime bypass of `AgentGuard.inspect_message`, trust verification, or capability enforcement
- Audit log hash-chain integrity failures
- ONNX model integrity bypass
- Adapter integration issues that allow unsigned or over-privileged agent actions

Out of scope:

- Vulnerabilities in upstream LLM providers or agent frameworks themselves
- Attacks requiring full compromise of the host operating system outside AgentGuard's control
- Issues in training datasets not shipped with the runtime package

## Safe Harbor

Good-faith security research that follows this policy will not be pursued as a terms-of-service violation. Do not access data you do not own, disrupt production systems, or exfiltrate user data when testing.
