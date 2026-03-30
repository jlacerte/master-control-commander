[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.2.0--alpha-blue.svg)](CHANGELOG.md)
[![Status](https://img.shields.io/badge/status-production-brightgreen.svg)]()
[![Built with Claude Code](https://img.shields.io/badge/Built%20with-Claude%20Code-blueviolet.svg)](https://claude.ai/code)
[![Anthropic SDK](https://img.shields.io/badge/Anthropic-SDK-orange.svg)](https://github.com/anthropics/anthropic-sdk-python)
[![MCP Servers](https://img.shields.io/badge/MCP%20Servers-15-informational.svg)]()
[![Autonomous Workers](https://img.shields.io/badge/Workers-5%20autonomous-success.svg)]()
[![Distributed](https://img.shields.io/badge/architecture-distributed-purple.svg)]()
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS-lightgrey.svg)]()

# Master Control Commander

🇫🇷 [Version française](README.fr.md) · 📋 [Changelog / Version Tracking](CHANGELOG.md)

**v0.2.0-alpha — Active Development**

> Status: Production system running 24/7 across multiple nodes. Architecture documented from real infrastructure. Demo available for local testing on any platform.

A distributed, two-layer architecture for running autonomous AI agents in a real business. Separates infrastructure orchestration (**Commander**) from intelligent agent logic (**Control**). Components communicate over HTTP, making the system natively distributable across nodes and platforms.

Developed and tested over 6+ months in a field service operation handling invoicing, client communications, market intelligence, and system maintenance. Currently running on 3 VPS nodes with 15 MCP servers, 5 autonomous workers, and 30+ scheduled automations.

---

## Architecture

### Distributed Network Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     DISTRIBUTED NODE MAP                             │
│                                                                      │
│  ┌──────────────────────┐   ┌──────────────────────┐                │
│  │  NODE 1: Primary VPS  │   │  NODE 2: Dedicated    │               │
│  │  Linux x86_64         │   │  Linux x86_64         │               │
│  │  AMD EPYC · 8GB · SSD │   │  Project workloads    │               │
│  │                        │   │                        │               │
│  │  15 MCP Servers        │   └──────────┬─────────────┘              │
│  │  5 Workers             │              │                            │
│  │  30+ Cron jobs         │              │ HTTP/MCP                   │
│  │  Health monitoring     │              │                            │
│  └──────────┬─────────────┘   ┌──────────┴─────────────┐            │
│             │                 │  NODE 3: Archon Cloud    │            │
│             │ HTTP/MCP        │  Task Broker (Supabase)  │            │
│             │                 │  RAG Knowledge Base      │            │
│             │                 │  Project Management      │            │
│  ┌──────────┴─────────────┐   └──────────┬─────────────┘            │
│  │  NODE 4: Workstation    │              │                           │
│  │  macOS / Linux / Win    │              │                           │
│  │  Claude Code CLI        │──────────────┘                          │
│  │  Direct MCP access      │                                         │
│  │  Dev + operator console │                                         │
│  └─────────────────────────┘                                         │
│                                                                      │
│  All nodes connect to the same MCP servers and Task Broker           │
│  via HTTP. No shared filesystem or VPN required.                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Two-Layer Design

```
┌──────────────────────────────────────────────────────────────────┐
│                      MASTER CONTROL (Agent Layer)                 │
│                                                                   │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐        │
│  │ Concierge │ │ Business  │ │   Intel   │ │   Slack   │  ...   │
│  │  Worker   │ │  Worker   │ │  Worker   │ │  Socket   │        │
│  │  (Infra)  │ │ (Revenue) │ │ (Market)  │ │  (Chat)   │        │
│  └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └─────┬─────┘        │
│        └──────────────┼─────────────┼─────────────┘              │
│                       │             │                             │
│              ┌────────┴─────────────┴────────┐                   │
│              │       Task Broker              │                   │
│              │    (Supabase — external)       │                   │
│              └───────────────────────────────┘                   │
└──────────────────────────┬───────────────────────────────────────┘
                           │ HTTP
┌──────────────────────────┼───────────────────────────────────────┐
│                   MASTER COMMANDER (Infrastructure Layer)         │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                   MCP Server Fleet (15)                     │  │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐  │  │
│  │  │ ERP  │ │Email │ │ CRM  │ │Phone │ │ Desk │ │Calendar│ │  │
│  │  │Zoho  │ │Zoho  │ │Zoho  │ │Twilio│ │Zoho  │ │Nextcl. │ │  │
│  │  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘  │  │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐  │  │
│  │  │ File │ │Intel │ │Brief.│ │Slack │ │Email │ │Servi-│  │  │
│  │  │Maker │ │igence│ │  ing │ │      │ │IMAP  │ │cNtre │  │  │
│  │  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘  │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐    │
│  │  Health  │ │   Auto   │ │   Port   │ │  RAG Memory +    │    │
│  │ Monitor  │ │ Stabilize│ │ Registry │ │  Blueprint Sync  │    │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
```

### Commander (Infrastructure)

| Component | Count | Role |
|-----------|-------|------|
| MCP Servers | 15 | API abstraction — ERP, Email, CRM, Phone, Calendar, Help Desk, Database, Intelligence |
| Workers | 5 | Autonomous task execution via Claude SDK (infra, business, intel, orchestration, chat) |
| Cron Jobs | 30+ | Health checks, data sync, auto-stabilize, email commands, blueprint refresh |
| Port Registry | 1 | Centralized port conflict prevention with validation script |

### Control (Agent Layer)

Each worker is a Claude SDK session with:
- Role-based autonomy (financial limits, approval gates, forbidden actions)
- Task-driven execution (poll → execute → report)
- Domain expertise loaded via CLAUDE.md files and RAG
- Circuit breakers (max 3 failures before escalation)

---

## Distributed by Design

The architecture is natively distributable. Components communicate exclusively over HTTP — no shared filesystem, no VPN, no tight coupling.

### Why it distributes

| Component | Protocol | Location constraint |
|-----------|----------|-------------------|
| MCP Servers | HTTP endpoints | Any machine with network access |
| Task Broker | Supabase REST API | Cloud-hosted (external) |
| Workers | HTTP client → MCP + Broker | Any machine with Python + API key |
| Claude Code | CLI / Desktop / Web | macOS, Linux |
| Health Monitor | Reads local + remote endpoints | Any node |

### Current production topology

| Node | Hardware | Role | OS |
|------|----------|------|-----|
| Primary VPS | AMD EPYC 7713 · 8 GB RAM · 160 GB SSD | 15 MCP servers, 5 workers, cron, monitoring | Ubuntu 22.04 (x86_64) |
| Dedicated VPS | Dedicated workloads | Project-specific processing | Linux (x86_64) |
| Archon Cloud | Supabase-backed | Task broker, RAG knowledge base, project management | Docker |
| Workstation | Apple M-series · 16+ GB RAM | Claude Code operator console, development, direct MCP access | macOS (ARM64) |

### Adding a new node

A new node (VPS, laptop, container) needs only:
1. Network access to the MCP server endpoints (HTTP)
2. Network access to the Task Broker (Supabase URL + key)
3. An Anthropic API key for Claude SDK sessions
4. A CLAUDE.md file defining the worker's role and autonomy rules

No code changes. No deployment pipeline. No shared state beyond the broker.

### Tested platforms

The system has been tested and runs in production on:
- **Linux x86_64** — Ubuntu 22.04 VPS (production, all 3 nodes)
- **macOS Apple Silicon** — development workstation, Claude Code operator console

---

## Design Patterns

### 1. Universal Worker Loop

```python
while True:
    health = check_health()          # Guardian: health gates execution
    if health == "red":
        defer_all_tasks()
        continue

    task = broker.get_next(status="todo", assigned_to=ROLE)
    result = sdk_session.send(prompt=task, tools=ROLE_TOOLS)

    if result.success:
        broker.update(task.id, status="review")
    elif task.attempts >= MAX:
        broker.update(task.id, status="review")  # Circuit breaker
        escalate(task)
```

### 2. Guardian Pattern

Health status gates all operations. No worker attempts business tasks when infrastructure is degraded.

```
GREEN  → Normal execution
YELLOW → Reduced capabilities
RED    → Defer everything, focus on recovery
```

### 3. Circuit Breaker

Prevents infinite retry loops — the most common failure mode in autonomous agents.

```
Attempt 1 fails → retry
Attempt 2 fails → retry
Attempt 3 fails → stop, mark "review", escalate
```

### 4. MCP Abstraction

Agents see clean tool calls. MCP servers handle OAuth, rate limiting, retries, and error normalization. The agent never touches raw APIs.

### 5. Autonomy Matrix

Explicit boundaries per worker, defined in CLAUDE.md:

| Action | Autonomous | Needs Approval |
|--------|-----------|----------------|
| Read / Search | Always | — |
| Routine emails | Below threshold | Above threshold |
| Create invoices | < $5,000 | > $5,000 |
| Delete anything | Never | Always |

### 6. Dry-Run

All write operations: prepare → validate → execute. No fire-and-forget.

---

## Self-Healing

```
Auto-Stabilize (every 10 min)
    ├── Read health.json
    ├── Service down? → Restart (max 3/hour)
    ├── Multiple down? → Check root cause first, then escalate
    └── Forbidden: never restart SSH/systemd/Docker, never delete data
```

Rules that exist because of real incidents:

| Rule | Incident |
|------|----------|
| Max 3 restarts/hour per service | A crash loop caused 2,083 restarts |
| Validate ports before assigning | Port conflict took down multiple services |
| Include self-IP in nginx whitelist | Missing entry caused 17h downtime |
| Check deps after container rebuild | Missing library broke search for 6 days |

---

## Data Strategy

Two layers, each serving a different purpose:

| Layer | Purpose | Update Frequency |
|-------|---------|-----------------|
| RAG Memory | Conversation history, decisions, context | Hourly |
| Blueprint | ERP snapshot (clients, finances, projects) | Weekly |

```
RAG Memory     → "What happened yesterday?"
Blueprint      → "What's the current state of Client A?"
```

---

## Core Concept: Adversarial Validation

The central idea behind this architecture: **two agents in a pit**. Every meaningful action passes through a challenge-response loop where one agent proposes and another validates.

This is borrowed from adversarial networks (GANs) — but applied to business operations instead of image generation. The "generator" proposes actions. The "discriminator" checks them.

### How it works

```
┌─────────────────────────────────────────────────────────────┐
│                   ADVERSARIAL LOOP                           │
│                                                              │
│   ┌────────────┐         ┌────────────┐                     │
│   │  PROPOSER   │ ──────→ │  VALIDATOR  │                    │
│   │  (Worker)   │ ←────── │  (Reviewer) │                    │
│   │             │  accept  │             │                    │
│   │  Generates  │  reject  │  Challenges │                    │
│   │  action     │  revise  │  checks     │                    │
│   └────────────┘         └────────────┘                     │
│         │                       │                            │
│         ▼                       ▼                            │
│   "Create invoice           "Amount matches work             │
│    for $4,200"               order? Client active?           │
│                               Terms correct?"                │
│                                                              │
│   Only executes if BOTH agents agree.                        │
└─────────────────────────────────────────────────────────────┘
```

### The two systems as adversaries

**Master Control** (agent layer) proposes actions based on tasks, domain knowledge, and business rules. **Master Commander** (infrastructure layer) validates feasibility, checks system health, and enforces constraints.

Neither system trusts the other blindly:

| Proposer says | Validator checks |
|---------------|-----------------|
| "Send invoice to client" | Client exists? Amount matches? Not already sent? |
| "Restart service X" | Max restarts reached? Other services affected? |
| "Schedule inspection" | Calendar conflict? Travel time realistic? |
| "Email client about overdue payment" | Correct contact? Escalation level appropriate? |

### Why this matters

Single-agent systems fail silently. The agent makes a confident mistake and nobody catches it. With adversarial validation:

- **Errors get caught before execution** — the validator asks the questions the proposer forgot
- **Confidence is earned, not assumed** — both agents must agree
- **Escalation is natural** — disagreement between agents = ask a human
- **Domain rules are enforced structurally** — not just "hoped for" via prompting

### Levels of adversarial validation

```
Level 0: No validation      → Agent acts alone (dangerous)
Level 1: Self-check         → Agent reviews its own output (weak)
Level 2: Peer validation    → Second agent validates (this architecture)
Level 3: Human-in-the-loop  → Disagreements escalate to operator
```

This architecture operates at Level 2 by default, with automatic escalation to Level 3 when the two agents disagree.

---

## Demo

A self-contained demo is included in the `demo/` directory. It runs a minimal Master Control Commander on your local machine — no external services needed (except a Claude API key).

### What the demo includes

| Component | File | Role |
|-----------|------|------|
| Task Broker | `task_broker.py` | SQLite-based task queue with REST API |
| Mock MCP Server | `mock_mcp_server.py` | Simulated domain tools (buildings, inspections, clients) |
| Health Monitor | `health_monitor.py` | Checks services, writes health.json |
| Worker | `demo_worker.py` | Autonomous agent: polls tasks, calls Claude, uses tools |
| Launcher | `start_demo.sh` | Starts everything in the right order |

### Quick start

```bash
git clone https://github.com/jlacerte/master-control-commander.git
cd master-control-commander/demo

# Set your API key
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# Install and run
pip install -r requirements.txt
./start_demo.sh
```

The demo seeds 3 sample tasks (inspection summary, overdue follow-ups, retrofit estimate). The worker picks them up, calls Claude with the mock tools, and produces results.

### Hardware requirements

| Platform | Example Hardware | RAM | Tested? |
|----------|-----------------|-----|---------|
| Linux (x86_64) | VPS, dedicated server | 4+ GB | Production |
| macOS (Apple Silicon) | MacBook Pro M-series | 8+ GB | Development |

The demo uses the Claude API — all computation happens server-side. No GPU required. Requirements: Python 3.11+ and an Anthropic API key.

### What to observe

1. **Guardian pattern** — Worker checks health.json before each polling cycle
2. **Task lifecycle** — Tasks move: `todo → doing → done` (or `→ review` on failure)
3. **Tool use loop** — Claude calls mock MCP tools, processes results, produces output
4. **Circuit breaker** — If a task fails 3 times, it moves to `review` instead of retrying

### Adding your own tasks

While the demo is running:

```bash
curl -X POST http://localhost:8090/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "List all buildings with dry systems", "description": "Query the database and list buildings that use dry pipe systems."}'
```

---

## Production Setup

For a real deployment (not the demo):

1. **Deploy one MCP server** for your most-used API
2. **Create one worker** using the universal worker loop
3. **Set up health monitoring** (cron + JSON)
4. **Add the task broker** (Supabase free tier or SQLite)
5. **Connect a chat interface** (Slack Socket Mode or equivalent)

### Scale path

```
Week 1:  1 MCP server + 1 worker + health check
Week 2:  Add 2-3 more MCP servers
Week 3:  Second worker (adversarial validator role)
Week 4:  Auto-stabilize + RAG memory
Month 2: Blueprint automation + adversarial loops on critical paths
```

The primary node runs on a single VPS (AMD EPYC, 8 GB RAM, $20-50/month). Additional nodes can be added by pointing workers at the same MCP endpoints and Task Broker. Systemd manages services. Cron handles scheduling. No Kubernetes needed.

---

## Applicable Verticals

Works for businesses with repetitive operational workflows, external system integrations, and domain-specific knowledge:

HVAC, plumbing, electrical, fire protection, property management, insurance inspections, equipment maintenance, construction management.

---

## Lessons from Production

1. **Two agents are smarter than one.** Adversarial validation catches errors that self-review misses.
2. **CLAUDE.md is the product.** Domain instructions and autonomy rules matter more than architecture.
3. **Self-healing saves you at 3 AM.** Circuit breakers + auto-restart means sleeping through issues.
4. **MCP abstraction is necessary.** Agents on raw APIs leads to retry loops and OAuth problems.
5. **Explicit autonomy beats model judgment.** Define what agents can and can't do.
6. **One VPS is enough to start.** The architecture distributes across nodes when needed, but a single VPS handles production workloads at this scale.
7. **Health before features.** Never deploy when existing services are degraded.
8. **Disagreement = escalation.** When agents don't agree, a human decides. This is a feature.

---

## License

MIT. See [LICENSE](LICENSE).

---

*Built with [Claude Code](https://claude.ai/code) + [Anthropic SDK](https://github.com/anthropics/anthropic-sdk-python)*
