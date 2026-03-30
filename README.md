# Master Control Commander

**v0.1.0-alpha — Active Development**

> Status: Early development and consolidation. Architecture documented from a working production system. Demo available for local testing.

A two-system architecture for running autonomous AI agents in a real business. Separates infrastructure orchestration (**Commander**) from intelligent agent logic (**Control**).

Developed and tested over 6+ months in a field service operation handling invoicing, client communications, market intelligence, and system maintenance.

---

## Architecture

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
                    │       └────────────┼────────────┘           │
                    │                    │                         │
                    │              Task Broker                     │
                    │           (Supabase/SQLite)                  │
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
                    │  │   RAG    │ │Blueprint │ │Adversarial│   │
                    │  │  Memory  │ │  Refresh │ │ Validator │   │
                    │  └──────────┘ └──────────┘ └──────────┘    │
                    └─────────────────────────────────────────────┘
```

### Commander (Infrastructure)

Keeps everything running on a single VPS with systemd and cron:

| Component | Role |
|-----------|------|
| MCP Servers (11+) | API abstraction — ERP, Email, CRM, Phone, Calendar |
| Workers (3) | Autonomous task execution via Claude SDK |
| Cron Jobs (8+) | Health checks, data sync, auto-stabilize |
| Port Registry | Centralized port conflict prevention |

### Control (Agent Layer)

Each worker is a Claude SDK session with:
- Role-based autonomy (financial limits, approval gates, forbidden actions)
- Task-driven execution (poll → execute → report)
- Domain expertise loaded via CLAUDE.md files and RAG
- Circuit breakers (max 3 failures before escalation)

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

| Setup | RAM | Works? |
|-------|-----|--------|
| Any modern laptop | 4+ GB | Yes — demo uses API only |
| VPS (4 CPU, 8 GB) | 8 GB | Yes — production target |

The demo needs Python 3.11+ and a Claude API key. No GPU required.

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

Everything runs on a single VPS (4 CPU, 8GB RAM, $20-50/month). Systemd manages services. Cron handles scheduling. No Kubernetes needed.

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
6. **One VPS is enough.** Resist over-engineering at this scale.
7. **Health before features.** Never deploy when existing services are degraded.
8. **Disagreement = escalation.** When agents don't agree, a human decides. This is a feature.

---

## License

MIT. See [LICENSE](LICENSE).

---

*Built with [Claude Code](https://claude.ai/code) + [Anthropic SDK](https://github.com/anthropics/anthropic-sdk-python)*
