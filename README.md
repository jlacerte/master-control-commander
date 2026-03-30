# Master Control Commander

**A two-system architecture for autonomous AI agent orchestration in vertical businesses.**

Master Control Commander is a production-proven framework for deploying AI agents that run a real business. It combines infrastructure orchestration (**Master Commander**) with an intelligent agent layer (**Master Control**) to create a self-healing, task-driven automation platform.

> Built and battle-tested over 6+ months in a field service business. Handles invoicing, client communications, market intelligence, scheduling, and system operations — autonomously.

---

## The Problem

Most AI agent demos are toy examples. Real business automation requires:

- **Reliability** — Agents that recover from failures without human intervention
- **Domain expertise** — Deep knowledge of your industry's rules, codes, and processes
- **Safety boundaries** — Agents that know what they can and can't do autonomously
- **Coordination** — Multiple specialized agents working together without conflicts
- **Memory** — Persistent context across sessions, conversations, and time

Master Control Commander solves all five.

---

## Architecture Overview

```
                    ┌─────────────────────────────────────────────┐
                    │            MASTER CONTROL                    │
                    │         (AI Agent Layer)                     │
                    │                                              │
                    │  ┌──────────┐ ┌──────────┐ ┌──────────┐    │
                    │  │Concierge │ │ Business │ │  Intel   │    │
                    │  │ Worker   │ │  Worker  │ │  Worker  │    │
                    │  │(Infra)   │ │(Revenue) │ │(Market)  │    │
                    │  └────┬─────┘ └────┬─────┘ └────┬─────┘    │
                    │       │            │            │           │
                    │       └────────────┼────────────┘           │
                    │                    │                         │
                    │              Task Broker                     │
                    │           (Archon/Supabase)                  │
                    └────────────────────┬────────────────────────┘
                                         │
                    ┌────────────────────┼────────────────────────┐
                    │            MASTER COMMANDER                  │
                    │        (Infrastructure Layer)                │
                    │                                              │
                    │  ┌─────────────────────────────────────┐    │
                    │  │         MCP Server Fleet             │    │
                    │  │  ┌─────┐┌─────┐┌─────┐┌─────┐     │    │
                    │  │  │ ERP ││Email││ CRM ││Phone│ ... │    │
                    │  │  └─────┘└─────┘└─────┘└─────┘     │    │
                    │  └─────────────────────────────────────┘    │
                    │                                              │
                    │  ┌──────────┐ ┌──────────┐ ┌──────────┐    │
                    │  │  Health  │ │   Auto   │ │   Port   │    │
                    │  │ Monitor  │ │ Stabilize│ │ Registry │    │
                    │  └──────────┘ └──────────┘ └──────────┘    │
                    │                                              │
                    │  ┌──────────┐ ┌──────────┐ ┌──────────┐    │
                    │  │   RAG    │ │Blueprint │ │ Training │    │
                    │  │  Memory  │ │  Refresh │ │   Data   │    │
                    │  └──────────┘ └──────────┘ └──────────┘    │
                    └─────────────────────────────────────────────┘
```

---

## Two Systems, One Brain

### Master Commander (Infrastructure)

The orchestration layer that keeps everything running. Deployed on a single VPS, it manages:

| Component | Count | Role |
|-----------|-------|------|
| MCP Servers | 11+ | API abstraction (ERP, Email, CRM, Phone, Calendar, Support Desk) |
| Specialized Workers | 3 | Autonomous task execution via AI SDK |
| Cron Jobs | 8+ | Health checks, data sync, email monitoring, auto-stabilize |
| Self-Healing | 1 | Auto-restart with circuit breakers and escalation |
| Port Registry | 1 | Centralized conflict prevention |

### Master Control (Agent Layer)

The intelligence layer. Each worker is a Claude SDK session with:

- **Role-based autonomy** — Financial limits, approval thresholds, forbidden actions
- **Task-driven execution** — Poll a task broker, execute, report results
- **Domain expertise** — Loaded via CLAUDE.md files, skills, and RAG memory
- **Circuit breakers** — Max 3 consecutive failures before escalation

---

## Key Design Patterns

### 1. The Universal Worker Loop

Every worker follows the same core loop:

```python
while True:
    # 1. Check system health (Guardian pattern)
    health = check_health()
    if health.has_red_warnings():
        defer_all_tasks()
        continue

    # 2. Poll for tasks
    task = task_broker.get_next(
        status="todo",
        assigned_to=WORKER_ROLE
    )

    # 3. Execute via AI SDK
    result = sdk_session.send(
        prompt=build_task_prompt(task),
        tools=get_role_tools(WORKER_ROLE)
    )

    # 4. Update task status
    if result.success:
        task_broker.update(task.id, status="review")
    else:
        task.attempts += 1
        if task.attempts >= MAX_ATTEMPTS:
            task_broker.update(task.id, status="review")  # Stop retry loop
            escalate(task)
```

### 2. Guardian Pattern

System health gates all task execution:

```
Health Check (every 5 min)
    │
    ├── GREEN: All systems operational → Execute tasks normally
    ├── YELLOW: Non-critical service down → Execute with reduced capabilities
    └── RED: Critical service down → Defer ALL tasks, focus on recovery
```

No worker will attempt business operations when infrastructure is degraded. Health always comes first.

### 3. Circuit Breaker

Prevents the most common failure mode in autonomous systems — infinite retry loops:

```
Task fails → attempts++ → retry
Task fails → attempts++ → retry
Task fails → attempts++ → MAX_ATTEMPTS reached
    → Mark "review" (human attention needed)
    → Escalate (notification)
    → Move to next task
```

**Critical lesson:** Without this, a single bad task can consume 100% of agent compute indefinitely.

### 4. MCP Abstraction Layer

API complexity is hidden behind Model Context Protocol servers:

```
Agent: "Create an invoice for Client A, $2,500"
    │
    ├── MCP Server handles:
    │   ├── OAuth token refresh
    │   ├── Rate limiting
    │   ├── Retry with backoff
    │   ├── Data validation
    │   └── Error normalization
    │
    └── Agent sees: clean tool call → clean result
```

Each MCP server is a standalone HTTP service with its own systemd unit, health endpoint, and restart policy. The agent never touches raw APIs.

### 5. Autonomy Matrix

Each worker has explicit boundaries:

| Action | Autonomous | Needs Approval |
|--------|-----------|----------------|
| Read data / Search | Always | — |
| Send routine emails | < threshold | > threshold |
| Create invoices | < $5,000 | > $5,000 |
| System restarts | Non-critical services | Critical services |
| Delete / Destructive | Never | Always |

The matrix is defined in each worker's CLAUDE.md and enforced by the AI model itself — no code-level guardrails needed.

### 6. Dry-Run Pattern

All destructive operations follow: prepare → validate → execute.

```python
# Phase 1: Prepare
invoice_data = build_invoice(work_order)

# Phase 2: Validate (always)
validation = validate_invoice(invoice_data)
if not validation.ok:
    report_error(validation.issues)
    return

# Phase 3: Execute (only after validation passes)
result = create_invoice(invoice_data)
```

No "fire and forget." Every action that affects external systems goes through validation first.

---

## Worker Specialization

### Concierge Worker (Infrastructure)

- Monitors system health
- Restarts failed services
- Runs deep health checks
- Manages port conflicts
- Escalates issues it can't resolve

### Business Worker (Revenue)

- Processes invoices and estimates
- Manages client communications
- Handles collections and follow-ups
- Syncs data between ERP systems
- Enforces business rules and SOPs

### Intelligence Worker (Market)

- Monitors regulatory changes
- Tracks competitor activity
- Analyzes public contract opportunities
- Generates market intelligence reports
- Alerts on relevant license changes

---

## Self-Healing Architecture

```
┌──────────────────────────────────────────────┐
│              AUTO-STABILIZE                    │
│                                                │
│  Cron (every 10 min)                          │
│      │                                         │
│      ├── Read health.json                      │
│      ├── Service down?                         │
│      │   ├── Restart (max 3/hour per service)  │
│      │   └── Verify recovery                   │
│      ├── Multiple services down?               │
│      │   ├── Check systemic cause first        │
│      │   └── Escalate to task broker           │
│      └── Forbidden actions:                    │
│          ├── Never restart SSH/systemd/Docker   │
│          ├── Never delete data                  │
│          ├── Never modify credentials           │
│          └── Never exceed restart budget        │
│                                                │
│  Escalation chain:                             │
│  Auto-fix → Task creation → Email alert        │
└──────────────────────────────────────────────┘
```

### Hard-Won Rules

These rules exist because of real production incidents:

| Rule | Why |
|------|-----|
| Max 3 restarts/hour per service | Prevented a crash loop that caused 2,083 restarts |
| Always validate port before assigning | A port conflict took down multiple services simultaneously |
| Nginx whitelist must include self-IP | Missing self-IP caused 17 hours of downtime |
| Check binary dependencies after container rebuild | A missing library broke RAG search for 6 days undetected |
| Never modify production during high-stakes events | Learned during a critical demo |

---

## Data Strategy

Three layers of knowledge, each serving a different purpose:

### Layer 1: RAG Memory (Operational)

- Conversation history, decisions, context
- Auto-synced hourly from a structured journal
- Indexed via vector search (pgvector)
- Powers cross-session continuity

### Layer 2: Blueprint (Business Truth)

- Weekly automated snapshot of ERP data
- Client profiles, financial status, project state
- Version-controlled in Git
- Single source of truth for business operations

### Layer 3: Training Data (Domain Expertise)

- Extracted from real operational data
- STT corrections, domain Q&A, agent behaviors
- JSONL format for fine-tuning
- Enables local model deployment (MLX + QLoRA)

```
RAG Memory     → "What happened yesterday?"
Blueprint      → "What's the current state of Client A's account?"
Training Data  → "How should an expert in this domain respond?"
```

---

## Interactive Layer: Chat Integration

A real-time interface (Slack/Teams) enables:

- **Voice-to-agent** — Speech-to-text → intent parsing → SDK session
- **Multi-session management** — Concurrent conversations with context isolation
- **Natural language commands** — "Send the invoice for Project X" triggers the full pipeline
- **Streaming responses** — Real-time progress updates during long operations

```
User (voice/text)
    │
    ├── Intent classification
    │   ├── Business action → Business Worker
    │   ├── System query → Concierge Worker
    │   └── General → Direct SDK session
    │
    ├── Session management
    │   ├── Create/resume SDK session
    │   ├── Inject domain context (CLAUDE.md + tools)
    │   └── Stream responses back to chat
    │
    └── Post-processing
        ├── Cost tracking per session
        ├── Transcript logging
        └── Error recovery with user notification
```

---

## Deployment Model

Everything runs on a single VPS (4 CPU, 8GB RAM):

```
VPS ($20-50/month)
├── 11 MCP servers (FastAPI/HTTP, ~50MB each)
├── 3 workers (Python, SDK sessions on-demand)
├── 1 task broker (Supabase/Postgres)
├── 1 health monitor (cron + JSON)
├── 1 auto-stabilize daemon
├── 1 chat integration (WebSocket)
└── 1 RAG index (pgvector in Postgres)
```

No Kubernetes. No microservice mesh. No cloud functions. A single Linux box with systemd, cron, and good architecture.

---

## Getting Started

### Prerequisites

- Linux VPS (Ubuntu 22.04+, 4+ CPU, 8GB+ RAM)
- Python 3.11+
- Claude API access (or compatible LLM API)
- At least one external system to integrate (ERP, CRM, Email)

### Minimal Setup

1. **Deploy one MCP server** — Start with your most-used API
2. **Create one worker** — Use the universal worker loop pattern
3. **Set up health monitoring** — Cron + JSON status file
4. **Add the task broker** — Supabase free tier works
5. **Connect chat interface** — Slack Socket Mode or equivalent

### Scale Path

```
Week 1:  1 MCP server + 1 worker + health check
Week 2:  Add 2-3 more MCP servers for core APIs
Week 3:  Add second worker (different specialization)
Week 4:  Enable auto-stabilize + RAG memory
Month 2: Blueprint automation + training data extraction
Month 3: Fine-tune local model for domain expertise
```

---

## Lessons Learned

After 6+ months of production operation:

1. **The CLAUDE.md is the product.** Your prompts, skills, and domain instructions are your real competitive advantage — not the model.

2. **Self-healing saves you at 3 AM.** Auto-stabilize with proper circuit breakers means you sleep through issues that would page an on-call engineer.

3. **MCP abstraction is non-negotiable.** Agents touching raw APIs directly is a recipe for token-burning retry loops and OAuth nightmares.

4. **Autonomy matrices prevent disasters.** Explicit boundaries > hoping the model "knows" what's appropriate.

5. **One VPS is enough.** Resist the urge to over-engineer. systemd + cron + good architecture beats Kubernetes for this scale.

6. **Voice input needs STT correction.** Domain-specific terms get mangled. Budget for a correction layer.

7. **Health > Features.** Never deploy new features when existing services are degraded.

8. **The blueprint pattern is underrated.** Weekly ERP snapshots in Git give you version-controlled business truth that agents can read without API calls.

---

## Applicable Verticals

This architecture works for any business with:

- Repetitive operational workflows
- External system integrations (ERP, CRM, Email)
- Domain-specific knowledge requirements
- Need for both autonomous and supervised actions
- Field service, inspections, or compliance tracking

**Examples:** HVAC, plumbing, electrical, property management, insurance inspections, equipment maintenance, construction management.

---

## Philosophy

> "The intelligence is in Claude, not in the tools. Keep the tools simple."

> "The tunnel will still be there tomorrow. Come back to the fire."

> "Breathe. The fire is still burning. Let's pick up from where we left off."

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

## Status

**Production** — This architecture has been running a real business since late 2025. The patterns described here are extracted from that production system, anonymized for public sharing.

Built with [Claude Code](https://claude.ai/code) + [Anthropic Agent SDK](https://github.com/anthropics/anthropic-sdk-python)
