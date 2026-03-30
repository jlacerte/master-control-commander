# Master Control — The Local AI Validation Layer

> This document describes the **Master Control** side of the architecture — the local AI agent framework that validates business communications before they are sent.

## Overview

Master Control runs on a local Mac (Apple Silicon, 24GB+ RAM) and provides:

1. **QA Auditor** — Validates AI-generated emails against business rules using a local LLM
2. **MCP Servers** — Exposes tools to Claude Code (QA + Gmail)
3. **Agent Framework** — Perceive→Think→Act→Observe loop with modular skills
4. **Web Dashboard** — Real-time monitoring: traces, memory, Ollama GPU tracking
5. **WireGuard VPN** — Encrypted tunnel to Master Commander (VPS)

```
Master Commander (VPS)                Master Control (Local Mac)
┌─────────────────────┐              ┌──────────────────────────┐
│ Workers generate     │   WireGuard  │ QA Auditor validates     │
│ emails, reports,     │─────────────▶│ against business rules   │
│ invoices             │   ~15ms      │ via local LLM (Ollama)   │
│                      │◀─────────────│                          │
│ 11+ MCP servers      │  PASS/FAIL   │ Returns corrected_text   │
│ Cron automation      │  + fixes     │ if violations found      │
└─────────────────────┘              └──────────────────────────┘
```

## Why Local?

Business content (invoices, client names, license numbers, financial data) never touches cloud LLMs. The QA validation runs entirely on local hardware via Ollama. Master Commander only sees the PASS/FAIL result through the encrypted VPN tunnel.

## The QA Auditor

### How It Works

```
Email content arrives via POST /qa/check
  → Load rulebook.yaml (business rules, 3 severity levels)
  → Build prompt for local LLM
  → LLM semantically evaluates content against each rule
  → Return JSON: {status, violations[], corrected_text}
```

### Rulebook (YAML)

Business rules are defined in YAML — not code. The LLM interprets them semantically:

```yaml
rules:
  # === CRITICAL (blockers) ===
  - id: COMPANY_NAME
    severity: critical
    description: "The official company name must be exact"
    patterns:
      - "Acme Sprinkler Systems"    # wrong variant
      - "Acme Sprinklers Inc."      # wrong variant
    expected: "Acme Sprinklers"

  - id: LICENSE_NUMBER
    severity: critical
    description: "Trade license number must be correct"
    expected: "1234-5678-90"
    context: "Never invent a license number"

  - id: PO_REQUIRED_CLIENT_X
    severity: critical
    description: "Invoices to Client X must include a PO number"
    trigger: "recipient is Client X accounts payable"

  # === WARNING ===
  - id: CONFIDENTIAL_PARTNER
    severity: warning
    description: "No internal pricing or margins in partner reports"
    trigger: "report destined to partner or client"
```

### Example: FAIL Response

```json
{
  "status": "FAIL",
  "violations": [
    {
      "rule": "COMPANY_NAME",
      "severity": "critical",
      "found": "Acme Sprinkler Systems Inc.",
      "expected": "Acme Sprinklers",
      "detail": "Company name must be 'Acme Sprinklers'."
    },
    {
      "rule": "LICENSE_NUMBER",
      "severity": "critical",
      "found": "1234-5679-90",
      "expected": "1234-5678-90",
      "detail": "License number is incorrect."
    }
  ],
  "corrected_text": "Hello, here is the report for Acme Sprinklers. License: 1234-5678-90",
  "model": "gemma3:12b",
  "latency_ms": 17674
}
```

### Why LLM-as-Judge (Not Regex)?

Traditional guardrails use programmatic validators (regex, schemas, OPA policies). We use an LLM because:

- **Semantic understanding** — Catches "Acme Sprinkler Systems Inc." as wrong even though it contains the right words
- **Context awareness** — Knows that mentioning margins (42%) in a partner report is a confidentiality violation
- **Corrected text** — Generates a fixed version, not just a pass/fail flag
- **Natural language rules** — Business owners write rules in plain language, not regex

Trade-off: ~10-20s latency per check vs. <1ms for regex. Acceptable for pre-send email validation.

## WireGuard Integration

Always-on encrypted tunnel between Mac and VPS:

```
Mac (10.0.0.2) ←→ VPS (10.0.0.1)
Protocol: WireGuard (UDP 51820)
Latency: ~15ms
Packet loss: 0%
```

Master Commander calls `POST http://10.0.0.2:8070/qa/check` through the tunnel. The QA server binds on `0.0.0.0:8070`.

### Setup (macOS)

```bash
brew install wireguard-tools
# Generate keys, write config, activate:
sudo bash infra/wireguard/start.sh
```

## Agent Framework

### Loop: Perceive → Think → Act → Observe

```python
# Simplified — actual code in agent/base.py
for turn in range(max_turns):
    # Perceive: inject relevant memories
    augmented_input = memory.search(user_input, top_k=5) + user_input

    # Think: call LLM
    response = llm.chat(messages + [augmented_input])

    # Parse: extract structured response
    thought, skill_name, params = parse(response)  # regex, not function-calling

    # Act: execute skill
    result = executor.execute(skill_name, params)

    # Observe: add result to conversation
    messages.append(f"OBSERVATION: {result}")

    # Or if FINAL_ANSWER: return to user
```

### Skills

Each skill implements `BaseSkill` with a JSON Schema spec:

```python
@SkillRegistry.register("qa_check")
class QACheckSkill(BaseSkill):
    @property
    def spec(self) -> SkillSpec:
        return SkillSpec(
            name="qa_check",
            description="Verify email against business rulebook",
            parameters={...},
            timeout_seconds=120.0,
        )

    def execute(self, **params) -> ToolResult:
        result = run_qa_check(email_html=params["email_text"])
        return ToolResult(tool_name="qa_check", content=json.dumps(result))
```

Available skills: `qa_check`, `gmail`, `think`, `memory_store`, `memory_search`.

## Web Dashboard

Five pages at `http://localhost:8090`:

### Ollama Monitor
Real-time view of local LLM activity:
- Which models are loaded in VRAM (GPU badge, size in GB)
- Which apps are connected (auto-identifies apps by PID/process name)
- Activity log with timestamps (model load/unload, client connect/disconnect)
- System RAM usage bar

### Traces
OpenTelemetry spans for every LLM call:
- Full datetime with relative time
- Model badge, token counts (in/out), tok/s speed
- Waterfall view per trace with color-coded durations (green < 1s, yellow < 5s, red > 5s)

### Memory Browser
SQLite + FTS5 full-text search over long-term agent memory with BM25 ranking.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.12+ |
| LLM | Ollama (gemma3:12b primary, 10+ models) |
| Memory | SQLite + FTS5 (BM25 ranking) |
| Tracing | OpenTelemetry → SQLite |
| Web | FastAPI + Jinja2 + Tailwind CSS |
| MCP | FastMCP (stdio transport) |
| VPN | WireGuard |
| Gmail | OAuth2 + Google API |

## Test Results

30/30 tests pass:
- 20 unit tests (rulebook loading, prompt building, response parsing)
- 10 integration tests against local LLM with real email fixtures
- 5 PASS emails (health checks, reports, invoices with correct data)
- 5 FAIL emails (wrong company name, missing PO#, wrong license, confidential data leaked)

E2E validated through WireGuard tunnel: Master Commander sent test emails, all returned correct PASS/FAIL results with ~15ms network + ~10-20s LLM latency.

## What Makes This Approach Unique

Based on competitive research across the AI agent ecosystem (March 2026):

1. **Cross-machine agent-to-agent QA via VPN** — No existing system validates one agent's output with another agent on a separate machine over VPN
2. **LLM-as-judge with domain business rules** — Guardrails AI uses schemas; this uses an LLM that semantically understands business context
3. **Privacy-first distributed architecture** — Sensitive content never leaves the local machine
4. **MCP as inter-agent protocol** — Ahead of the MCP 2026 roadmap for agent-to-agent communication

---

*Part of the [Master Control Commander](https://github.com/jlacerte/master-control-commander) architecture.*
