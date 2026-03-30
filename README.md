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
                    │  │   RAG    │ │Blueprint │ │ Training │    │
                    │  │  Memory  │ │  Refresh │ │   Data   │    │
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

Three layers, each serving a different purpose:

| Layer | Purpose | Update Frequency |
|-------|---------|-----------------|
| RAG Memory | Conversation history, decisions, context | Hourly |
| Blueprint | ERP snapshot (clients, finances, projects) | Weekly |
| Training Data | Domain expertise for fine-tuning | As needed |

```
RAG Memory     → "What happened yesterday?"
Blueprint      → "What's the current state of Client A?"
Training Data  → "How should a domain expert respond?"
```

---

## Local Model Strategy

Beyond cloud agents, the architecture includes local model deployment for field use — offline-capable domain expertise on commodity hardware.

### Open-Weight vs Proprietary

| Factor | Proprietary (API) | Open-Weight (Local) |
|--------|-------------------|---------------------|
| Privacy | Data leaves your network | Stays on your hardware |
| Ownership | You rent access | You own the model |
| Cost (long-term) | Per-token ongoing | One-time training |
| Offline | No | Yes |
| Vendor lock-in | High | None |

### Training Pipeline

```
Extract data (work orders, inspections, SOPs)
    → Structure as JSONL (instruction/input/output)
    → Augment via API distillation (~$20-50)
    → Fine-tune QLoRA 4-bit
    → Export GGUF
    → Deploy via Ollama
```

### Training Environments

| Environment | GPU | Cost | Notes |
|-------------|-----|------|-------|
| MacBook Pro (MLX) | Apple Silicon | $0 | Native QLoRA, ~45-60 min for 1K examples |
| Gaming PC (CUDA) | NVIDIA RTX 4060+ | $0 | Unsloth + PyTorch, 8GB VRAM handles 7B 4-bit |
| Kaggle | T4/P100 16GB | Free (30h/week) | Good for larger runs |
| Google Colab Pro | A100 40GB | $12/month | Production training |

#### MacBook Pro (MLX)

```bash
pip install mlx-lm
mlx_lm.lora \
  --model mlx-community/Qwen2.5-7B-Instruct-4bit \
  --train --data ./training-data \
  --batch-size 4 --lora-layers 16 --iters 1000
```

#### Gaming PC — NVIDIA GPU (CUDA + Unsloth)

An NVIDIA GPU with 8+ GB VRAM (RTX 3060, 4060, etc.) can fine-tune 7B models using Unsloth:

```bash
# Setup (one-time)
pip install unsloth torch

# Fine-tune
python -c "
from unsloth import FastLanguageModel
model, tokenizer = FastLanguageModel.from_pretrained(
    'unsloth/Qwen2.5-7B-Instruct-bnb-4bit',
    max_seq_length=2048, load_in_4bit=True
)
model = FastLanguageModel.get_peft_model(model, r=16, lora_alpha=16,
    target_modules=['q_proj','k_proj','v_proj','o_proj',
                    'gate_proj','up_proj','down_proj'])

# Load your JSONL training data and train
from unsloth import UnslothTrainer, UnslothTrainingArguments
# ... see Unsloth docs for full example
"

# Export to GGUF for Ollama
model.save_pretrained_gguf("./output", tokenizer, quantization_method="q4_k_m")

# Deploy
ollama create my-expert -f Modelfile
```

Hardware notes:
- **RTX 4060 (8GB):** Handles Qwen 7B in 4-bit comfortably. ~30-45 min for 1K examples.
- **RTX 3060 (12GB):** More VRAM headroom, similar speed.
- **RTX 4090 (24GB):** Can handle 14B models, 3-4x faster.

### Recommended Models

| Model | Size (4-bit) | License | Notes |
|-------|-------------|---------|-------|
| Qwen 2.5 7B | ~4.5 GB | Apache 2.0 | Best multilingual, strong reasoning |
| Llama 4 Scout 8B | ~5 GB | Llama license | Large community |
| Gemma 3 4B | ~2.5 GB | Apache 2.0 | Smallest viable, runs on phones |
| Phi-4 Mini 3.8B | ~2.3 GB | MIT | Good at structured tasks |

### Deployment

```
┌──────────────┐     ┌──────────────┐
│  MacBook /   │     │    VPS       │
│  Gaming PC   │     │  (Cloud)     │
│  ┌─────────┐ │     │  ┌────────┐  │
│  │ Ollama  │ │     │  │ Claude │  │
│  │ Local   │ │     │  │  API   │  │
│  │ Model   │ │     │  │Workers │  │
│  └────┬────┘ │     │  └────────┘  │
└───────┼──────┘     └──────────────┘
        │
  Local Network / Tailscale
        │
┌───────┼──────┐
│  Mobile      │  → Queries local model over LAN
│  (Field)     │    or runs Gemma 4B on-device
└──────────────┘
```

**Hybrid approach:** Local model for field work (offline, private), cloud agents for back-office (invoicing, CRM, email).

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

| Setup | RAM | GPU | Works? |
|-------|-----|-----|--------|
| Any modern laptop | 4+ GB | None needed | Yes — demo uses API only |
| Gaming PC (RTX 4060) | 8+ GB | 8 GB VRAM | Yes — also suitable for local fine-tuning |
| MacBook Pro M-series | 16+ GB | Integrated | Yes — demo + MLX fine-tuning |

The demo itself only needs Python 3.11+ and a Claude API key. GPU is only needed if you want to fine-tune a local model afterward.

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
Week 3:  Second worker (different role)
Week 4:  Auto-stabilize + RAG memory
Month 2: Blueprint automation + training data extraction
Month 3: Fine-tune local model
```

Everything runs on a single VPS (4 CPU, 8GB RAM, $20-50/month). Systemd manages services. Cron handles scheduling. No Kubernetes needed.

---

## Applicable Verticals

Works for businesses with repetitive operational workflows, external system integrations, and domain-specific knowledge:

HVAC, plumbing, electrical, fire protection, property management, insurance inspections, equipment maintenance, construction management.

---

## Lessons from Production

1. **CLAUDE.md is the product.** Domain instructions and autonomy rules matter more than architecture.
2. **Self-healing saves you at 3 AM.** Circuit breakers + auto-restart means sleeping through issues.
3. **MCP abstraction is necessary.** Agents on raw APIs leads to retry loops and OAuth problems.
4. **Explicit autonomy beats model judgment.** Define what agents can and can't do.
5. **One VPS is enough.** Resist over-engineering at this scale.
6. **Voice input needs STT correction.** Domain terms get mangled by speech-to-text.
7. **Health before features.** Never deploy when existing services are degraded.

---

## License

MIT. See [LICENSE](LICENSE).

---

*Built with [Claude Code](https://claude.ai/code) + [Anthropic SDK](https://github.com/anthropics/anthropic-sdk-python)*
