# AgentGuard runtime image — core firewall + OTEL (no LangGraph/CrewAI/AutoGen stack).
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=300 \
    PIP_RETRIES=10

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc g++ \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE ./
COPY agentguard/ agentguard/

# Install CPU PyTorch first (sentence-transformers dependency) from the stable CPU index.
RUN pip install --upgrade pip \
    && pip install --retries 10 --timeout 300 \
        torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --retries 10 --timeout 300 ".[otel]"

RUN useradd --create-home --shell /bin/bash agentguard
USER agentguard

VOLUME ["/data"]
ENV AGENTGUARD_AUDIT_LOG=/data/audit.jsonl

# Default: print version (override with `agentguard verify /data/audit.jsonl`)
CMD ["agentguard", "version"]
