"""
Universal Worker Template — Master Control Commander

This is the core pattern that all specialized workers follow.
Customize the WORKER_CONFIG and task execution logic for your domain.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

# --- Configuration ---

WORKER_CONFIG = {
    "name": "business-worker",
    "role": "business",
    "poll_interval": 30,           # seconds between task checks
    "max_attempts": 3,             # circuit breaker threshold
    "health_check_path": "/path/to/health.json",
    "task_broker_project_id": "your-project-id",
}

# Autonomy matrix — what this worker can do without approval
AUTONOMY_MATRIX = {
    "read_data":        {"autonomous": True,  "limit": None},
    "send_email":       {"autonomous": True,  "limit": "routine_only"},
    "create_invoice":   {"autonomous": True,  "limit": 5000},  # dollars
    "delete_anything":  {"autonomous": False, "limit": None},
    "restart_service":  {"autonomous": False, "limit": None},
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(WORKER_CONFIG["name"])


# --- Guardian Pattern ---

def check_system_health() -> dict:
    """
    Read the health.json file produced by the health monitor cron.
    Returns health status with any red/yellow warnings.
    """
    health_path = Path(WORKER_CONFIG["health_check_path"])
    if not health_path.exists():
        return {"status": "unknown", "warnings": ["Health file not found"]}

    health = json.loads(health_path.read_text())
    red_warnings = [
        s for s in health.get("services", {}).values()
        if s.get("status") == "red"
    ]
    return {
        "status": "red" if red_warnings else "green",
        "warnings": red_warnings,
        "timestamp": health.get("timestamp"),
    }


def should_defer_tasks(health: dict) -> bool:
    """Guardian gate: defer all tasks if system health is red."""
    if health["status"] == "red":
        logger.warning(f"RED health status — deferring tasks: {health['warnings']}")
        return True
    return False


# --- Task Broker Integration ---

async def poll_next_task(broker_client) -> dict | None:
    """
    Poll the task broker for the next available task.
    Replace with your actual broker (Supabase, Linear, custom API).
    """
    tasks = await broker_client.list_tasks(
        filter_by="status",
        filter_value="todo",
        per_page=1,
    )
    return tasks[0] if tasks else None


async def update_task_status(broker_client, task_id: str, status: str, note: str = ""):
    """Update task status in the broker."""
    await broker_client.manage_task(
        action="update",
        task_id=task_id,
        status=status,
        description_append=f"\n[{datetime.now().isoformat()}] {note}" if note else None,
    )


# --- Circuit Breaker ---

class CircuitBreaker:
    """
    Tracks consecutive failures per task.
    After MAX_ATTEMPTS, marks task for human review instead of retrying.
    """

    def __init__(self, max_attempts: int = 3):
        self.max_attempts = max_attempts
        self.failure_counts: dict[str, int] = {}

    def record_failure(self, task_id: str) -> bool:
        """Returns True if circuit is now open (should stop retrying)."""
        self.failure_counts[task_id] = self.failure_counts.get(task_id, 0) + 1
        return self.failure_counts[task_id] >= self.max_attempts

    def record_success(self, task_id: str):
        """Reset failure count on success."""
        self.failure_counts.pop(task_id, None)

    def is_open(self, task_id: str) -> bool:
        return self.failure_counts.get(task_id, 0) >= self.max_attempts


# --- SDK Session Execution ---

async def execute_task_with_sdk(task: dict, tools: list) -> dict:
    """
    Execute a task using an AI SDK session.

    In production, this creates a Claude SDK session with:
    - The task description as the prompt
    - Domain-specific tools (MCP servers)
    - Worker's CLAUDE.md for context
    - Autonomy boundaries

    Replace with your actual SDK integration.
    """
    # Build the prompt with task context
    prompt = f"""
    Task: {task['title']}
    Description: {task.get('description', 'No description')}
    Priority: {task.get('priority', 'normal')}

    Execute this task following your role guidelines and autonomy matrix.
    Report what you did and any issues encountered.
    """

    # --- Replace this with actual SDK call ---
    # from anthropic import Anthropic
    # client = Anthropic()
    # result = client.messages.create(
    #     model="claude-sonnet-4-20250514",
    #     messages=[{"role": "user", "content": prompt}],
    #     tools=tools,
    # )
    # return {"success": True, "output": result.content}

    return {"success": True, "output": "Task executed (template)"}


# --- Main Worker Loop ---

async def worker_loop(broker_client):
    """
    The universal worker loop.

    1. Check health (Guardian)
    2. Poll for tasks
    3. Execute via SDK
    4. Update status (with circuit breaker)
    5. Sleep and repeat
    """
    circuit_breaker = CircuitBreaker(max_attempts=WORKER_CONFIG["max_attempts"])

    logger.info(f"Starting {WORKER_CONFIG['name']} worker loop")

    while True:
        try:
            # --- Step 1: Guardian Check ---
            health = check_system_health()
            if should_defer_tasks(health):
                await asyncio.sleep(60)  # Check again in 1 min
                continue

            # --- Step 2: Poll for task ---
            task = await poll_next_task(broker_client)
            if not task:
                await asyncio.sleep(WORKER_CONFIG["poll_interval"])
                continue

            task_id = task["id"]
            logger.info(f"Processing task: {task['title']} ({task_id})")

            # Check circuit breaker
            if circuit_breaker.is_open(task_id):
                logger.warning(f"Circuit open for {task_id} — skipping")
                continue

            # Mark as doing
            await update_task_status(broker_client, task_id, "doing")

            # --- Step 3: Execute ---
            tools = get_tools_for_role(WORKER_CONFIG["role"])
            result = await execute_task_with_sdk(task, tools)

            # --- Step 4: Update status ---
            if result["success"]:
                circuit_breaker.record_success(task_id)
                await update_task_status(
                    broker_client, task_id, "review",
                    note=f"Completed: {result['output'][:200]}"
                )
                logger.info(f"Task {task_id} completed → review")
            else:
                should_stop = circuit_breaker.record_failure(task_id)
                if should_stop:
                    await update_task_status(
                        broker_client, task_id, "review",
                        note=f"CIRCUIT OPEN after {WORKER_CONFIG['max_attempts']} failures"
                    )
                    logger.error(f"Task {task_id} — circuit breaker opened")
                else:
                    await update_task_status(
                        broker_client, task_id, "todo",
                        note=f"Attempt failed, will retry"
                    )

        except Exception as e:
            logger.exception(f"Worker loop error: {e}")
            await asyncio.sleep(10)

        # --- Step 5: Sleep ---
        await asyncio.sleep(WORKER_CONFIG["poll_interval"])


def get_tools_for_role(role: str) -> list:
    """
    Return the MCP tools available for this worker role.
    Each role has a different set of capabilities.
    """
    tool_sets = {
        "infrastructure": [
            "health_check", "restart_service", "check_logs",
            "port_registry", "system_status",
        ],
        "business": [
            "erp_invoices", "erp_estimates", "email_send",
            "crm_contacts", "workdrive_files", "support_tickets",
        ],
        "intelligence": [
            "regulatory_search", "competitor_monitor",
            "contract_opportunities", "market_analysis",
        ],
    }
    return tool_sets.get(role, [])


# --- Entry Point ---

if __name__ == "__main__":
    # Replace with your actual broker client initialization
    broker_client = None  # YourBrokerClient(project_id=WORKER_CONFIG["task_broker_project_id"])
    asyncio.run(worker_loop(broker_client))
