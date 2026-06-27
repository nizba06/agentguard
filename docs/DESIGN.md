**AgentGuard**

Inter-Agent Security Firewall

Design Document & Developer Setup Guide

Version 1.0 • June 2026 • 3-Week Build Sprint

<table style="width:62%;">
<colgroup>
<col style="width: 20%" />
<col style="width: 20%" />
<col style="width: 20%" />
</colgroup>
<tbody>
<tr>
<td style="text-align: center;"><p>IDE</p>
<p><strong>Cursor</strong></p></td>
<td style="text-align: center;"><p>Language</p>
<p><strong>Python 3.11</strong></p></td>
<td style="text-align: center;"><p>Target</p>
<p><strong>3 weeks</strong></p></td>
</tr>
</tbody>
</table>

**1. Project Overview**

AgentGuard is an open-source security middleware library for multi-agent
AI systems. It intercepts every message passing between agents in a
LangGraph, CrewAI, or AutoGen pipeline and enforces three runtime
security controls: message inspection, cryptographic trust attestation,
and capability containment. It ships alongside a purpose-built benchmark
— the first published evaluation suite specifically targeting
inter-agent injection attacks.

This document covers the complete technical design and the step-by-step
setup guide to go from zero to a running development environment in
under 30 minutes.

<table style="width:96%;">
<colgroup>
<col style="width: 96%" />
</colgroup>
<tbody>
<tr>
<td><p><strong>What makes this different from everything that
exists</strong></p>
<p>Every existing guardrails tool — LLM Guard, NeMo Guardrails, Rebuff —
operates at the user-to-model boundary. None inspect messages between
agents. AgentGuard is the first open-source tool to treat inter-agent
messages as untrusted inputs requiring independent inspection, signing,
and scope enforcement at every hop.</p></td>
</tr>
</tbody>
</table>

**1.1 Three Core Security Layers**

|  |  |
|----|----|
| **Layer** | **What it does** |
| Layer 1 — Message Inspector | Hybrid rule-and-ML classifier scores every inter-agent message (and MCP tool outputs) for injection risk before delivery. Three stages: rule pre-filter (\<0.5ms), DeBERTa ML scorer (~12ms), contextual consistency check (~4ms). |
| Layer 2 — Trust Verifier | Each agent is issued an ephemeral Ed25519 keypair at pipeline initialisation. Every message is signed by the sender and verified before the recipient acts on it. Keys are rotated per run — no replay attacks. |
| Layer 3 — Capability Enforcer | Each agent declares a YAML capability manifest specifying permitted tools, forbidden tools, allowed data sources, and external contact rules. Violations are blocked at runtime, not logged after the fact. |
| Audit Logger | Every processed message is written to an append-only cryptographically chained JSONL audit log. Each entry includes the SHA-256 hash of the previous entry — tampering is detectable. Optional OpenTelemetry export. |
| Benchmark Suite | The first published inter-agent injection benchmark. 1,200 adversarial messages crafted specifically to exploit inter-agent trust assumptions. Reusable by any researcher evaluating their own defences. |

**2. Technology Stack**

Every technology choice below is made for three reasons specific to this
project: it minimises friction in a 3-week solo build, it is the best
tool for the specific technical job, and it avoids dependencies that
would complicate open-source adoption.

**2.1 IDE & AI Tooling**

**Primary IDE: Cursor**

Cursor is a VS Code fork with native multi-file agent mode. For
AgentGuard specifically, you will frequently need to edit the inspector
module, its integration test, and the LangGraph adapter simultaneously
in a single logical change. Cursor's Agent Mode handles this in one
instruction. Every VS Code extension works out of the box — no migration
cost.

|  |  |
|----|----|
| **Feature** | **Why it matters for this build** |
| Multi-file Agent Mode | AgentGuard has ~15 Python modules that frequently need coordinated changes. Edit all of them in one instruction rather than file by file. |
| VS Code fork | All Python, Pylance, Ruff, and Docker extensions work identically. No re-learning. |
| Background Agents | Can clone your repo and work autonomously while you review — useful for writing tests and benchmark scripts in parallel. |
| .cursorrules file | Configure project-specific rules (e.g. always use PyNaCl for crypto, never use os.system) that Cursor enforces on every suggestion. |
| Cost | Free tier sufficient for a solo project of this size. No paid plan required. |

**Terminal Companion: Claude Code**

Claude Code is Anthropic's terminal-based coding agent, included with
Claude Pro. Use it for heavier generation tasks: writing full modules
from a spec, generating the benchmark dataset (1,200 adversarial
messages), writing the complete test suite, and producing the README and
blog post draft. It operates on your local file system and is faster
than chat for bulk code generation.

<table style="width:96%;">
<colgroup>
<col style="width: 96%" />
</colgroup>
<tbody>
<tr>
<td><p><strong>How to split the work</strong></p>
<p>Use Cursor for: day-to-day coding, debugging, multi-file edits,
running tests. Use Claude Code (terminal) for: generating entire new
modules from scratch, bulk dataset generation, writing 500+ line test
files, documentation drafts. They complement each other and share the
same Claude Pro subscription.</p></td>
</tr>
</tbody>
</table>

**2.2 Language & Package Management**

|  |  |
|----|----|
| **Tool** | **Choice & Reasoning** |
| Python version | 3.11 specifically. LangGraph 0.2, CrewAI 0.70, and AutoGen 0.4 all have the most stable support on 3.11. Python 3.12 works but introduces minor asyncio changes that cause intermittent issues with LangGraph's StateGraph — not worth the debugging time on a 3-week sprint. |
| Version management | pyenv. Lets you install and switch Python versions without touching the system Python. Critical when your machine may have 3.9 or 3.10 as the system default. |
| Package management | Poetry. Two reasons: (1) pyproject.toml-native dependency locking means your exact environment is reproducible, (2) poetry publish pushes to PyPI in one command with no separate setup.py or twine configuration. This matters for Week 3 when you launch. |
| Linting & formatting | Ruff. Replaces flake8 + isort + black in a single tool running in milliseconds. Configured once in pyproject.toml. Pre-commit hook runs it automatically so the codebase stays clean without thinking about it. |
| Type checking | mypy with strict mode on the core modules (firewall.py, inspector/, trust/, capability/). Catches bugs that tests miss. Not required everywhere — just the security-critical paths. |

**2.3 Agent Framework Targets**

AgentGuard wraps three frameworks. Build in this order — LangGraph first
because it has the largest user base and the clearest interception
points.

|  |  |  |
|----|----|----|
| **Framework** | **Version** | **Integration approach** |
| LangGraph | \>=0.2 | Wrap the compiled StateGraph with guard.wrap(graph). Intercepts at the node execution boundary using LangGraph's custom node wrapper pattern. This is the primary adapter — build in Week 1. |
| CrewAI | \>=0.70 | Hook into the agent.execute_task lifecycle and the tool execution pipeline. CrewAI's architecture makes tool-call interception straightforward. Build in Week 2. |
| AutoGen | \>=0.4 | Middleware on the GroupChat.run_chat message passing interface. AutoGen's message bus is well-structured for interception. Build in Week 3. |

**2.4 Security & Cryptography**

|  |  |
|----|----|
| **Library** | **Choice & Reasoning** |
| PyNaCl (Ed25519 signing) | libsodium bindings for Python. Ed25519 chosen over RSA because: 64-byte signatures (vs 256+ for RSA), constant-time verification (side-channel resistant), and the PyNaCl API is simple enough that the signing layer can be implemented in under 100 lines. pip install pynacl. |
| pyahocorasick (rule filter) | Aho-Corasick multi-pattern string matching. Searches for all injection signature patterns simultaneously in O(n) time — critical for keeping the rule-filter under 0.5ms even with 200+ patterns. Pure C with Python bindings. pip install pyahocorasick. |
| hashlib (audit log chaining) | Python standard library. SHA-256 for message hashes and log entry chaining. No external dependency needed. |
| jsonschema (manifest validation) | Validates YAML capability manifests against the published JSON Schema at registration time. Fails fast with descriptive errors before the pipeline starts. pip install jsonschema. |
| PyYAML (manifest loading) | Standard YAML parser for capability manifest files. pip install pyyaml. |

**2.5 ML Classifier Stack**

|  |  |
|----|----|
| **Component** | **Choice & Reasoning** |
| Model: DeBERTa-v3-small | Microsoft's DeBERTa-v3-small via Hugging Face. Chosen over DistilBERT (lower accuracy on adversarial text) and full DeBERTa-base (too large at 180MB, too slow at ~40ms CPU). The -small variant hits the right trade-off: 91MB ONNX, ~12ms CPU inference, 94%+ injection detection precision on the InjectAgent benchmark. |
| Fine-tuning: Hugging Face Trainer | Standard transformers Trainer API. Familiar to the research community, easy to reproduce, and the training script is simple enough to fit in a single notebook. Run on Kaggle free GPU (30 hrs/week) — no local GPU required. |
| Export: Hugging Face Optimum | Exports the fine-tuned model to ONNX format via optimum-cli. The ONNX file is framework-independent — no PyTorch or TensorFlow required at deployment time. pip install optimum\[onnxruntime\]. |
| Inference: onnxruntime | Runs the ONNX model in-process, CPU-only by default, with optional GPU acceleration via onnxruntime-gpu. The model loads once at pipeline initialisation and stays in memory. pip install onnxruntime. |
| Consistency check: sentence-transformers | all-MiniLM-L6-v2 for semantic similarity between message intent and declared task objective. Fast (384-dim embeddings), small (80MB), and runs in-process. pip install sentence-transformers. |
| GPU for training | Kaggle (free, 30 GPU hrs/week) or Google Colab Pro (\$12/month). Training takes 2-4 hours. No local GPU needed. |

**2.6 Testing Stack**

|  |  |
|----|----|
| **Tool** | **Purpose & Reasoning** |
| pytest | Standard Python test runner. pytest-asyncio extension for testing async agent pipelines. Target: \>85% line coverage across all core modules. |
| hypothesis | Property-based testing. Generates random message variants automatically and checks that the firewall's behaviour is consistent. Particularly useful for the rule filter — catches edge cases that hand-written tests miss. |
| pytest-cov | Coverage measurement and reporting. Integrated with GitHub Actions to block PRs that drop coverage below 85%. |
| Custom attack fixtures | A set of pytest fixtures that fire all five attack classes (indirect injection, propagation, impersonation, capability escalation, MCP poisoning) against the reference vulnerable pipeline. These fixtures become the benchmark evaluation harness. |

**2.7 Packaging, CI/CD & Deployment**

|  |  |
|----|----|
| **Tool** | **Purpose & Reasoning** |
| GitHub Actions | CI/CD pipeline: runs Ruff lint, mypy type check, pytest suite, ONNX model integrity check, and benchmark regression on every PR. Publishes to PyPI automatically on version tags. Free for public repositories. |
| PyPI | pip install agentguard. Poetry handles the build and publish steps. The PyPI download count becomes one of your measurable adoption metrics. |
| Docker Hub | Multi-stage Docker image for teams who prefer a sidecar deployment pattern rather than pip install. The image is \< 400MB including the ONNX model. |
| pre-commit | Runs Ruff and mypy automatically before every git commit. Enforces code quality without a CI round-trip. pip install pre-commit. |
| structlog | Structured JSONL logging for the audit trail. Produces machine-readable log entries with consistent field names. pip install structlog. |
| opentelemetry-sdk | Optional OTLP export for SIEM integration (Datadog, Splunk, Elastic). Installed separately as an optional dependency. pip install opentelemetry-sdk opentelemetry-exporter-otlp. |

**2.8 Complete Dependency Summary**

<table style="width:96%;">
<colgroup>
<col style="width: 96%" />
</colgroup>
<tbody>
<tr>
<td><p># pyproject.toml — core dependencies</p>
<p>[tool.poetry.dependencies]</p>
<p>python = '&gt;=3.11,&lt;3.13'</p>
<p># Agent framework adapters</p>
<p>langgraph = '&gt;=0.2'</p>
<p>crewai = '&gt;=0.70'</p>
<p>pyautogen = '&gt;=0.4'</p>
<p># Security &amp; crypto</p>
<p>pynacl = '&gt;=1.5'</p>
<p>pyahocorasick = '&gt;=2.0'</p>
<p>jsonschema = '&gt;=4.0'</p>
<p>PyYAML = '&gt;=6.0'</p>
<p># ML inference (no PyTorch at runtime)</p>
<p>onnxruntime = '&gt;=1.17'</p>
<p>sentence-transformers = '&gt;=2.7'</p>
<p>numpy = '&gt;=1.26'</p>
<p># Logging &amp; observability</p>
<p>structlog = '&gt;=24.0'</p>
<p>[tool.poetry.extras]</p>
<p>otel = ['opentelemetry-sdk', 'opentelemetry-exporter-otlp']</p>
<p>[tool.poetry.dev-dependencies]</p>
<p>pytest = '&gt;=8.0'</p>
<p>pytest-asyncio = '&gt;=0.23'</p>
<p>pytest-cov = '&gt;=5.0'</p>
<p>hypothesis = '&gt;=6.0'</p>
<p>ruff = '&gt;=0.4'</p>
<p>mypy = '&gt;=1.9'</p>
<p>pre-commit = '&gt;=3.7'</p>
<p># Fine-tuning only (not shipped with the package)</p>
<p>transformers = { version='&gt;=4.40', optional=true }</p>
<p>optimum = { version='&gt;=1.19', optional=true,
extras=['onnxruntime'] }</p>
<p>datasets = { version='&gt;=2.19', optional=true }</p></td>
</tr>
</tbody>
</table>

**3. System Architecture**

**3.1 Data Flow**

<table style="width:96%;">
<colgroup>
<col style="width: 96%" />
</colgroup>
<tbody>
<tr>
<td><p>EXTERNAL WORLD (web, docs, APIs, MCP servers)</p>
<p>|</p>
<p>v untrusted input</p>
<p>[ ORCHESTRATOR AGENT ]</p>
<p>|</p>
<p>v signs message with ephemeral Ed25519 key</p>
<p>╔═══════════════════════════════════════════════╗</p>
<p>║ AGENTGUARD FIREWALL LAYER ║</p>
<p>║ ║</p>
<p>║ Stage 1: Rule filter &lt;0.5ms ║</p>
<p>║ Stage 2: ML risk scorer ~12ms ║</p>
<p>║ Stage 3: Consistency check ~4ms ║</p>
<p>║ Stage 4: Trust verify &lt;1ms ║</p>
<p>║ Stage 5: Capability check &lt;1ms ║</p>
<p>║ ║</p>
<p>║ PASS → forward FAIL → quarantine + alert ║</p>
<p>╚═══════════════════════════════════════════════╝</p>
<p>| | |</p>
<p>v v v</p>
<p>Research Code Comms</p>
<p>Agent Agent Agent</p>
<p>(read-only) (code exec) (email/Slack)</p></td>
</tr>
</tbody>
</table>

**3.2 Repository Structure**

<table style="width:96%;">
<colgroup>
<col style="width: 96%" />
</colgroup>
<tbody>
<tr>
<td><p>agentguard/</p>
<p>├── agentguard/</p>
<p>│ ├── __init__.py # Public API: AgentGuard, CapabilityManifest</p>
<p>│ ├── firewall.py # Main class — entry point</p>
<p>│ ├── inspector/</p>
<p>│ │ ├── rule_filter.py # Aho-Corasick rule-based pre-filter</p>
<p>│ │ ├── ml_scorer.py # DeBERTa ONNX inference wrapper</p>
<p>│ │ └── consistency.py # Sentence-transformer consistency check</p>
<p>│ ├── trust/</p>
<p>│ │ ├── authority.py # Ephemeral keypair generation</p>
<p>│ │ └── signing.py # Ed25519 sign &amp; verify (PyNaCl)</p>
<p>│ ├── capability/</p>
<p>│ │ ├── manifest.py # YAML loading + JSON Schema validation</p>
<p>│ │ └── enforcer.py # Runtime capability enforcement</p>
<p>│ ├── adapters/</p>
<p>│ │ ├── langgraph.py # LangGraph StateGraph wrapper</p>
<p>│ │ ├── crewai.py # CrewAI tool + agent hook</p>
<p>│ │ └── autogen.py # AutoGen GroupChat middleware</p>
<p>│ ├── mcp/</p>
<p>│ │ └── output_inspector.py # MCP tool return value inspection</p>
<p>│ └── audit/</p>
<p>│ ├── logger.py # Chained append-only JSONL logger</p>
<p>│ └── otel.py # Optional OpenTelemetry OTLP export</p>
<p>├── schemas/</p>
<p>│ └── capability_manifest.schema.json</p>
<p>├── manifests/ # Example capability manifests</p>
<p>├── examples/</p>
<p>│ ├── vulnerable_pipeline/ # Reference attack demo</p>
<p>│ └── secured_pipeline/ # AgentGuard-protected version</p>
<p>├── benchmarks/ # Attack evaluation harness + datasets</p>
<p>│ ├── dataset/ # 1,200 adversarial + 5,000 benign messages</p>
<p>│ └── evaluate.py # Scoring script</p>
<p>├── tests/</p>
<p>│ ├── test_inspector.py</p>
<p>│ ├── test_trust.py</p>
<p>│ ├── test_capability.py</p>
<p>│ └── test_integration.py</p>
<p>├── .cursorrules # Project-specific Cursor rules</p>
<p>├── .pre-commit-config.yaml</p>
<p>├── pyproject.toml</p>
<p>├── README.md</p>
<p>└── Dockerfile</p></td>
</tr>
</tbody>
</table>

**4. Installation Guide — Zero to Running in 30 Minutes**

Follow these steps exactly in order. Each step has a verification
command so you know it worked before moving on. Estimated total time:
25-35 minutes depending on your internet speed.

<table style="width:96%;">
<colgroup>
<col style="width: 96%" />
</colgroup>
<tbody>
<tr>
<td><p><strong>Before you start — check your operating
system</strong></p>
<p>These instructions cover macOS and Linux (Ubuntu/Debian). Windows
users: install WSL2 first (Windows Subsystem for Linux), then follow the
Linux path inside WSL2. All commands run in your terminal.</p></td>
</tr>
</tbody>
</table>

**Step 1 — Install Cursor (IDE)**

1.  Go to cursor.com and download the installer for your OS.

2.  Run the installer. Cursor opens as a VS Code-compatible application.

3.  Install the Python extension: open Cursor, press Cmd+Shift+X (Mac)
    or Ctrl+Shift+X (Linux), search 'Python', install the Microsoft
    Python extension.

4.  Install the Ruff extension: same extension panel, search 'Ruff',
    install the Astral Software Ruff extension.

<table style="width:96%;">
<colgroup>
<col style="width: 96%" />
</colgroup>
<tbody>
<tr>
<td><p># Verify Cursor installed (run from terminal)</p>
<p>cursor --version</p>
<p># Expected: Cursor 0.x.x or similar</p></td>
</tr>
</tbody>
</table>

**Step 2 — Install pyenv (Python version manager)**

pyenv lets you install exactly Python 3.11 without affecting your system
Python.

**macOS:**

<table style="width:96%;">
<colgroup>
<col style="width: 96%" />
</colgroup>
<tbody>
<tr>
<td><p># Install Homebrew if not already installed</p>
<p>/bin/bash -c "$(curl -fsSL
https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"</p>
<p># Install pyenv</p>
<p>brew install pyenv</p>
<p># Add to your shell profile (~/.zshrc or ~/.bash_profile)</p>
<p>echo 'export PYENV_ROOT="$HOME/.pyenv"' &gt;&gt; ~/.zshrc</p>
<p>echo 'command -v pyenv &gt;/dev/null || export
PATH="$PYENV_ROOT/bin:$PATH"' &gt;&gt; ~/.zshrc</p>
<p>echo 'eval "$(pyenv init -)"' &gt;&gt; ~/.zshrc</p>
<p># Reload your shell</p>
<p>source ~/.zshrc</p></td>
</tr>
</tbody>
</table>

**Linux (Ubuntu/Debian):**

<table style="width:96%;">
<colgroup>
<col style="width: 96%" />
</colgroup>
<tbody>
<tr>
<td><p># Install dependencies</p>
<p>sudo apt-get update</p>
<p>sudo apt-get install -y make build-essential libssl-dev zlib1g-dev
\</p>
<p>libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm \</p>
<p>libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev
libffi-dev liblzma-dev</p>
<p># Install pyenv</p>
<p>curl https://pyenv.run | bash</p>
<p># Add to ~/.bashrc</p>
<p>echo 'export PYENV_ROOT="$HOME/.pyenv"' &gt;&gt; ~/.bashrc</p>
<p>echo 'command -v pyenv &gt;/dev/null || export
PATH="$PYENV_ROOT/bin:$PATH"' &gt;&gt; ~/.bashrc</p>
<p>echo 'eval "$(pyenv init -)"' &gt;&gt; ~/.bashrc</p>
<p>source ~/.bashrc</p></td>
</tr>
</tbody>
</table>

**Verify:**

<table style="width:96%;">
<colgroup>
<col style="width: 96%" />
</colgroup>
<tbody>
<tr>
<td><p>pyenv --version</p>
<p># Expected: pyenv 2.x.x</p></td>
</tr>
</tbody>
</table>

**Step 3 — Install Python 3.11**

<table style="width:96%;">
<colgroup>
<col style="width: 96%" />
</colgroup>
<tbody>
<tr>
<td><p># Install Python 3.11.9 (latest 3.11 patch)</p>
<p>pyenv install 3.11.9</p>
<p># Verify</p>
<p>pyenv versions</p>
<p># You should see 3.11.9 in the list</p></td>
</tr>
</tbody>
</table>

**Step 4 — Install Poetry (package manager)**

<table style="width:96%;">
<colgroup>
<col style="width: 96%" />
</colgroup>
<tbody>
<tr>
<td><p># Install Poetry (official installer — do NOT use pip install
poetry)</p>
<p>curl -sSL https://install.python-poetry.org | python3 -</p>
<p># Add Poetry to your PATH</p>
<p>echo 'export PATH="$HOME/.local/bin:$PATH"' &gt;&gt; ~/.zshrc #
macOS</p>
<p>echo 'export PATH="$HOME/.local/bin:$PATH"' &gt;&gt; ~/.bashrc #
Linux</p>
<p>source ~/.zshrc # or source ~/.bashrc</p>
<p># Verify</p>
<p>poetry --version</p>
<p># Expected: Poetry (version 1.8.x or 2.x.x)</p>
<p># Configure Poetry to create virtualenvs inside the project
folder</p>
<p># (makes it easier to point Cursor at the right Python)</p>
<p>poetry config virtualenvs.in-project true</p></td>
</tr>
</tbody>
</table>

**Step 5 — Install Claude Code (terminal agent)**

Claude Code is Anthropic's terminal coding agent. It requires Claude Pro
or Max. If you have upgraded to Pro, install it now.

<table style="width:96%;">
<colgroup>
<col style="width: 96%" />
</colgroup>
<tbody>
<tr>
<td><p># Claude Code requires Node.js 18+. Check first:</p>
<p>node --version</p>
<p># If Node not installed:</p>
<p># macOS: brew install node</p>
<p># Linux: sudo apt-get install -y nodejs npm</p>
<p># Install Claude Code globally</p>
<p>npm install -g @anthropic-ai/claude-code</p>
<p># Verify</p>
<p>claude --version</p>
<p># Authenticate (opens browser for OAuth)</p>
<p>claude login</p></td>
</tr>
</tbody>
</table>

**Step 6 — Create the AgentGuard project**

This creates the full project scaffold using Poetry with Python 3.11.

<table style="width:96%;">
<colgroup>
<col style="width: 96%" />
</colgroup>
<tbody>
<tr>
<td><p># Create project directory and initialise with Poetry</p>
<p>mkdir agentguard &amp;&amp; cd agentguard</p>
<p># Tell pyenv to use 3.11.9 in this directory</p>
<p>pyenv local 3.11.9</p>
<p># Verify Python version</p>
<p>python --version</p>
<p># Must show: Python 3.11.9</p>
<p># Initialise Poetry project</p>
<p>poetry init \</p>
<p>--name agentguard \</p>
<p>--description 'Inter-agent security firewall for multi-agent AI
systems' \</p>
<p>--author 'Your Name &lt;your@email.com&gt;' \</p>
<p>--python '&gt;=3.11,&lt;3.13' \</p>
<p>--license Apache-2.0 \</p>
<p>--no-interaction</p></td>
</tr>
</tbody>
</table>

**Step 7 — Install all dependencies**

Copy the following commands exactly. They install every dependency the
project needs.

<table style="width:96%;">
<colgroup>
<col style="width: 96%" />
</colgroup>
<tbody>
<tr>
<td><p># Core agent frameworks</p>
<p>poetry add langgraph&gt;=0.2 crewai&gt;=0.70 pyautogen&gt;=0.4</p>
<p># Security &amp; crypto</p>
<p>poetry add pynacl&gt;=1.5 pyahocorasick&gt;=2.0 jsonschema&gt;=4.0
PyYAML&gt;=6.0</p>
<p># ML inference stack (no PyTorch required at runtime)</p>
<p>poetry add onnxruntime&gt;=1.17 sentence-transformers&gt;=2.7
numpy&gt;=1.26</p>
<p># Logging</p>
<p>poetry add structlog&gt;=24.0</p>
<p># Dev dependencies</p>
<p>poetry add --group dev pytest&gt;=8.0 pytest-asyncio&gt;=0.23
pytest-cov&gt;=5.0</p>
<p>poetry add --group dev hypothesis&gt;=6.0 ruff&gt;=0.4 mypy&gt;=1.9
pre-commit&gt;=3.7</p>
<p># Optional: OpenTelemetry SIEM export</p>
<p>poetry add --optional opentelemetry-sdk
opentelemetry-exporter-otlp</p>
<p># Verify the virtual environment was created</p>
<p>poetry env info</p>
<p># Should show Python 3.11.x and a .venv path inside your
project</p></td>
</tr>
</tbody>
</table>

**Step 8 — Create the folder structure**

<table style="width:96%;">
<colgroup>
<col style="width: 96%" />
</colgroup>
<tbody>
<tr>
<td><p># Create all directories</p>
<p>mkdir -p
agentguard/{inspector,trust,capability,adapters,mcp,audit}</p>
<p>mkdir -p schemas manifests
examples/{vulnerable_pipeline,secured_pipeline}</p>
<p>mkdir -p benchmarks/dataset tests</p>
<p># Create __init__.py files</p>
<p>touch agentguard/__init__.py</p>
<p>touch
agentguard/{inspector,trust,capability,adapters,mcp,audit}/__init__.py</p>
<p># Create placeholder source files</p>
<p>touch agentguard/firewall.py</p>
<p>touch agentguard/inspector/{rule_filter,ml_scorer,consistency}.py</p>
<p>touch agentguard/trust/{authority,signing}.py</p>
<p>touch agentguard/capability/{manifest,enforcer}.py</p>
<p>touch agentguard/adapters/{langgraph,crewai,autogen}.py</p>
<p>touch agentguard/mcp/output_inspector.py</p>
<p>touch agentguard/audit/{logger,otel}.py</p>
<p>touch
tests/{test_inspector,test_trust,test_capability,test_integration}.py</p>
<p>touch README.md Dockerfile .gitignore</p>
<p># Verify structure</p>
<p>find . -type f -name '*.py' | head -20</p></td>
</tr>
</tbody>
</table>

**Step 9 — Configure Ruff and pre-commit**

Add the following to your pyproject.toml to configure Ruff:

<table style="width:96%;">
<colgroup>
<col style="width: 96%" />
</colgroup>
<tbody>
<tr>
<td><p># Add to pyproject.toml</p>
<p>[tool.ruff]</p>
<p>line-length = 100</p>
<p>target-version = 'py311'</p>
<p>select = ['E', 'F', 'W', 'I', 'N', 'UP', 'S']</p>
<p>ignore = ['S101'] # Allow assert in tests</p>
<p>[tool.ruff.per-file-ignores]</p>
<p>'tests/*' = ['S', 'E501']</p>
<p>[tool.mypy]</p>
<p>python_version = '3.11'</p>
<p>strict = true</p>
<p>ignore_missing_imports = true</p>
<p>[tool.pytest.ini_options]</p>
<p>asyncio_mode = 'auto'</p>
<p>testpaths = ['tests']</p>
<p>addopts = '--cov=agentguard --cov-report=term-missing
--cov-fail-under=85'</p></td>
</tr>
</tbody>
</table>

Create the pre-commit configuration:

<table style="width:96%;">
<colgroup>
<col style="width: 96%" />
</colgroup>
<tbody>
<tr>
<td><p># .pre-commit-config.yaml</p>
<p>repos:</p>
<p>- repo: https://github.com/astral-sh/ruff-pre-commit</p>
<p>rev: v0.4.0</p>
<p>hooks:</p>
<p>- id: ruff</p>
<p>args: [--fix]</p>
<p>- id: ruff-format</p>
<p>- repo: https://github.com/pre-commit/mirrors-mypy</p>
<p>rev: v1.9.0</p>
<p>hooks:</p>
<p>- id: mypy</p>
<p>additional_dependencies: [types-PyYAML, types-jsonschema]</p></td>
</tr>
</tbody>
</table>

<table style="width:96%;">
<colgroup>
<col style="width: 96%" />
</colgroup>
<tbody>
<tr>
<td><p># Install pre-commit hooks</p>
<p>poetry run pre-commit install</p>
<p># Run once to verify</p>
<p>poetry run pre-commit run --all-files</p>
<p># Expected: all checks pass (or only formatting fixes on empty
files)</p></td>
</tr>
</tbody>
</table>

**Step 10 — Configure Cursor for the project**

Create a .cursorrules file in the project root. This tells Cursor how to
help you correctly throughout the build.

<table style="width:96%;">
<colgroup>
<col style="width: 96%" />
</colgroup>
<tbody>
<tr>
<td><p># .cursorrules</p>
<p># AgentGuard project rules for Cursor AI</p>
<p>## Project context</p>
<p>This is AgentGuard: a Python security middleware library for
multi-agent AI systems.</p>
<p>It intercepts inter-agent messages and enforces inspection, trust,
and capability controls.</p>
<p>## Language and style</p>
<p>- Python 3.11 only. Use modern syntax (match statements, | union
types, etc.)</p>
<p>- All public functions and classes must have type annotations (mypy
strict)</p>
<p>- Docstrings on all public API surfaces (Google style)</p>
<p>- Line length: 100 characters max</p>
<p>## Security rules — NEVER violate these</p>
<p>- ALWAYS use PyNaCl for cryptographic operations. Never use hashlib
for signing.</p>
<p>- NEVER use os.system() or subprocess with shell=True in the library
code</p>
<p>- NEVER log message payloads at DEBUG level — only hashes and
metadata</p>
<p>- ALWAYS validate manifest YAML against the JSON Schema before
use</p>
<p>## Architecture rules</p>
<p>- The firewall.py entry point must remain under 150 lines</p>
<p>- Each security layer (inspector, trust, capability) must be
independently testable</p>
<p>- Adapters (langgraph, crewai, autogen) must import from
agentguard.firewall only</p>
<p>- No circular imports between modules</p>
<p>## Testing rules</p>
<p>- Every new function needs a corresponding test in tests/</p>
<p>- Attack fixture tests live in tests/test_integration.py</p>
<p>- Use pytest.mark.asyncio for all async tests</p></td>
</tr>
</tbody>
</table>

**Step 11 — Initialise Git and GitHub**

<table style="width:96%;">
<colgroup>
<col style="width: 96%" />
</colgroup>
<tbody>
<tr>
<td><p># Initialise git</p>
<p>git init</p>
<p>git branch -M main</p>
<p># Create .gitignore</p>
<p>cat &gt; .gitignore &lt;&lt; 'EOF'</p>
<p>.venv/</p>
<p>__pycache__/</p>
<p>*.pyc</p>
<p>.pytest_cache/</p>
<p>.mypy_cache/</p>
<p>.ruff_cache/</p>
<p>*.egg-info/</p>
<p>dist/</p>
<p>*.onnx # Do NOT commit the model — too large</p>
<p>benchmarks/dataset/*.jsonl # Dataset generated, not committed</p>
<p>audit.jsonl</p>
<p>EOF</p>
<p># Initial commit</p>
<p>git add .</p>
<p>git commit -m 'chore: initialise AgentGuard project scaffold'</p>
<p># Create GitHub repo (install gh CLI first: brew install gh / sudo
apt install gh)</p>
<p>gh repo create agentguard --public --description 'Inter-agent
security firewall for multi-agent AI systems'</p>
<p>git remote add origin
https://github.com/YOUR_USERNAME/agentguard.git</p>
<p>git push -u origin main</p></td>
</tr>
</tbody>
</table>

**Step 12 — Verify the full environment**

Run this complete verification check. Every command should succeed.

<table style="width:96%;">
<colgroup>
<col style="width: 96%" />
</colgroup>
<tbody>
<tr>
<td><p># 1. Python version</p>
<p>poetry run python --version</p>
<p># Must show: Python 3.11.9</p>
<p># 2. All packages importable</p>
<p>poetry run python -c "</p>
<p>import langgraph, crewai, autogen</p>
<p>import nacl.signing</p>
<p>import ahocorasick</p>
<p>import jsonschema</p>
<p>import onnxruntime</p>
<p>import sentence_transformers</p>
<p>import structlog</p>
<p>print('All imports successful')"</p>
<p># 3. Test suite runs (no tests yet, but framework should work)</p>
<p>poetry run pytest --co -q</p>
<p># Expected: 0 tests collected (no errors)</p>
<p># 4. Ruff passes on empty files</p>
<p>poetry run ruff check agentguard/</p>
<p># Expected: All checks passed</p>
<p># 5. Claude Code connected</p>
<p>claude --version</p>
<p># 6. Git status clean</p>
<p>git status</p>
<p># Expected: nothing to commit, working tree clean</p></td>
</tr>
</tbody>
</table>

<table style="width:96%;">
<colgroup>
<col style="width: 96%" />
</colgroup>
<tbody>
<tr>
<td><p><strong>You are ready to build</strong></p>
<p>If all 6 checks above pass, your development environment is fully
configured. The next step is writing the vulnerable reference pipeline —
the 3-agent system that demonstrates the attacks AgentGuard will defend
against.</p></td>
</tr>
</tbody>
</table>

**5. 3-Week Build Schedule**

|  |  |  |
|----|----|----|
| **Week** | **Daily focus** | **Exit criterion** |
| Week 1 Days 1-2 | Dev environment + vulnerable pipeline. 3-agent LangGraph system that demonstrates indirect injection, propagation, and capability escalation. | Attacks reproducible. Baseline attack success rate measured at 100%. |
| Week 1 Days 3-5 | Rule-based pre-filter. Aho-Corasick pattern engine with 50+ injection signatures. LangGraph adapter v1. | Rule filter alone blocks 40%+ of baseline attacks. LangGraph wrap works end-to-end. |
| Week 2 Days 1-3 | DeBERTa fine-tuning on Kaggle GPU. Dataset prep from InjectAgent + MASpi. ONNX export and integration into ml_scorer.py. | ML scorer alone achieves \>80% detection. Inference \<15ms CPU verified. |
| Week 2 Days 4-5 | Trust verifier: Ed25519 keypair generation, Trust Authority sidecar, signing/verification in message envelope. | Impersonation attack: 100% blocked. Per-run key rotation verified. |
| Week 3 Days 1-2 | Capability manifest enforcer. YAML schema, runtime enforcement, monotonic attenuation. CrewAI and AutoGen adapters. | Capability escalation: 100% blocked. All three framework adapters tested. |
| Week 3 Days 3-4 | Benchmark dataset: 1,200 adversarial inter-agent messages generated via Claude API batch. Evaluation harness. Results measured. | Benchmark dataset published on Hugging Face. Full results table generated. |
| Week 3 Day 5 | GitHub v1.0 release: clean README, quick-start guide, demo video script, PyPI publish, blog post first draft. | pip install agentguard works. GitHub repo public. Blog post ready to publish. |

**6. How to Work With Claude Through the Build**

Claude (Sonnet 4.6, Claude Pro) can generate every module in this
project. Here is exactly what to expect and how to work effectively.

**6.1 What Claude generates directly**

- Complete Python modules from a spec — paste the function signature and
  docstring, get the full implementation

- Test files: pytest fixtures, attack scenario tests, integration tests
  for each adapter

- The benchmark dataset: 1,200 adversarial inter-agent messages across 5
  attack classes via Claude API batch

- YAML capability manifests for all example agents

- GitHub Actions workflow files, Dockerfile, pyproject.toml

- README, technical blog post draft, benchmark results writeup

- Debug assistance: paste a stack trace, get the fix and an explanation

**6.2 Daily workflow that works**

5.  Start each session by telling Claude exactly which file you are
    working on and what it needs to do.

6.  Paste errors back exactly as they appear — do not paraphrase. Claude
    needs the full stack trace.

7.  After each module is written, run pytest immediately. Paste failures
    back.

8.  Use Claude Code in the terminal for generating entire new modules.
    Use Cursor chat for editing existing files.

9.  At the end of each day, commit what works. Do not carry uncommitted
    work overnight.

**6.3 Where to use the Claude API separately**

The benchmark dataset generation requires Claude API calls outside of
this chat — you need to generate 1,200 adversarial messages
programmatically. Use the Batch API for this to keep costs under \$10.

<table style="width:96%;">
<colgroup>
<col style="width: 96%" />
</colgroup>
<tbody>
<tr>
<td><p># Install the Anthropic SDK for the benchmark generation
script</p>
<p>poetry add anthropic --group dev</p>
<p># Set your API key (get from console.anthropic.com)</p>
<p>export ANTHROPIC_API_KEY=sk-ant-...</p>
<p># The benchmark generation script
(benchmarks/generate_dataset.py)</p>
<p># will be written in Week 3 Day 3 of the build.</p>
<p># It uses the Batch API at $1.50/MTok (50% off standard Sonnet
rate)</p>
<p># to generate 1,200 adversarial messages for roughly $5-8
total.</p></td>
</tr>
</tbody>
</table>

**7. Total Cost Summary**

|  |  |
|----|----|
| **Item** | **Cost (GBP estimated)** |
| Claude Pro subscription (1 month) | ~£16 |
| Anthropic API — benchmark dataset generation via Batch API | ~£6–12 |
| Kaggle GPU for DeBERTa fine-tuning | £0 (free tier, 30 hrs/week) |
| OR Google Colab Pro (optional, faster GPUs) | ~£10 |
| Cloud spot instance for benchmark evaluation runs (optional) | £3–7 |
| Cursor | £0 (free tier sufficient) |
| Claude Code | £0 (included in Claude Pro) |
| GitHub, PyPI, Docker Hub accounts | £0 |
| Total — minimum | ~£22 |
| Total — comfortable (with Colab Pro + cloud compute) | ~£45 |

<table style="width:96%;">
<colgroup>
<col style="width: 96%" />
</colgroup>
<tbody>
<tr>
<td><p><strong>The most important spend</strong></p>
<p>Claude Pro at £16/month is the single most impactful cost in this
list. Without it, you will hit free tier message limits (15-40 messages
per 5-hour window) within the first hour of a serious coding session.
Upgrade before starting Day 1.</p></td>
</tr>
</tbody>
</table>

**8. Quick Reference**

**8.1 Daily commands**

<table style="width:96%;">
<colgroup>
<col style="width: 96%" />
</colgroup>
<tbody>
<tr>
<td><p># Activate the Poetry environment (run once per terminal
session)</p>
<p>poetry shell</p>
<p># Run all tests</p>
<p>poetry run pytest</p>
<p># Run tests with verbose output</p>
<p>poetry run pytest -v</p>
<p># Run only a specific test file</p>
<p>poetry run pytest tests/test_inspector.py</p>
<p># Check linting</p>
<p>poetry run ruff check agentguard/</p>
<p># Auto-fix linting</p>
<p>poetry run ruff check --fix agentguard/</p>
<p># Type checking</p>
<p>poetry run mypy agentguard/</p>
<p># Add a new dependency</p>
<p>poetry add package-name</p>
<p># Start Claude Code in terminal</p>
<p>claude</p>
<p># Open Cursor in current directory</p>
<p>cursor .</p></td>
</tr>
</tbody>
</table>

**8.2 Troubleshooting common setup issues**

|  |  |
|----|----|
| **Issue** | **Fix** |
| poetry: command not found | Run: export PATH="\$HOME/.local/bin:\$PATH" and reload your shell. Check that the Poetry installer completed without errors. |
| python --version shows 3.9 or 3.10 instead of 3.11 | Run pyenv local 3.11.9 inside the project folder. Check that pyenv init is in your shell profile and the profile was reloaded. |
| import langgraph fails after poetry add | Run poetry shell first to activate the virtual environment, then try the import. The packages are installed in the .venv folder, not your system Python. |
| PyNaCl install fails on Linux | Run: sudo apt-get install -y libsodium-dev then retry poetry add pynacl. |
| pyahocorasick install fails on macOS | Run: brew install automake then retry. The package needs C build tools. |
| sentence-transformers install is slow | It pulls a 80MB model on first use. Normal. Let it complete. |
| Claude Code: authentication error | Run claude login again. The OAuth token expires after 30 days. |
| Cursor can't find Python interpreter | Open Cursor, press Cmd+Shift+P, type 'Python: Select Interpreter', choose the .venv/bin/python inside your project folder. |

**8.3 Key URLs**

|  |  |
|----|----|
| **Resource** | **URL** |
| Cursor download | https://cursor.com |
| Claude Code docs | https://docs.anthropic.com/en/docs/claude-code |
| Anthropic API console (for API key) | https://console.anthropic.com |
| Kaggle (free GPU for fine-tuning) | https://www.kaggle.com/code |
| pyenv installation guide | https://github.com/pyenv/pyenv#installation |
| Poetry documentation | https://python-poetry.org/docs |
| LangGraph documentation | https://langchain-ai.github.io/langgraph |
| DeBERTa-v3-small on Hugging Face | https://huggingface.co/microsoft/deberta-v3-small |
| OWASP Agentic Security Initiative Top 10 | https://owasp.org/www-project-top-10-for-large-language-model-applications |
| InjectAgent benchmark dataset | https://huggingface.co/datasets/sunblaze-edgecloud/InjectAgent |

AgentGuard Design Document & Setup Guide v1.0 — June 2026 — Confidential
