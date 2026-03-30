#!/usr/bin/env python3
"""
Demo Worker — A minimal but functional autonomous agent.

Demonstrates the core patterns:
  - Guardian (health-gated execution)
  - Circuit breaker (max 3 attempts)
  - Task polling loop
  - Claude SDK session per task
  - Autonomy matrix

Run this after starting the task broker and mock MCP server.
"""

import json
import os
import sys
import time
import httpx
from datetime import datetime, timezone
from anthropic import Anthropic

# --- Configuration ---

WORKER_ID = "demo-worker"
BROKER_URL = os.environ.get("BROKER_URL", "http://localhost:8090")
MCP_URL = os.environ.get("MCP_URL", "http://localhost:8091")
HEALTH_FILE = os.environ.get("HEALTH_FILE", "health.json")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "10"))
MAX_ATTEMPTS = 3
MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-20250514")

# --- Autonomy matrix ---

AUTONOMY = {
    "read_data": {"autonomous": True},
    "generate_report": {"autonomous": True},
    "send_email": {"autonomous": False, "reason": "Requires approval in demo mode"},
    "create_invoice": {"autonomous": False, "reason": "Financial action"},
}

# --- Tool definitions for Claude ---

TOOLS = [
    {
        "name": "query_buildings",
        "description": "List all buildings in the asset database with their inspection history and system details.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "query_inspections",
        "description": "Get inspections completed this month with results and details.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "query_overdue_followups",
        "description": "Get overdue follow-up actions that need attention.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "estimate_retrofit",
        "description": "Generate a cost estimate for retrofitting a building's fire protection system.",
        "input_schema": {
            "type": "object",
            "properties": {
                "building_id": {"type": "string", "description": "Building ID (e.g. B-003)"}
            },
            "required": ["building_id"],
        },
    },
    {
        "name": "query_clients",
        "description": "List all clients with contact info and account balances.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


def log(msg: str):
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


# --- Guardian: health gate ---

def check_health() -> str:
    try:
        with open(HEALTH_FILE) as f:
            health = json.load(f)
        return health.get("overall", "red")
    except FileNotFoundError:
        return "unknown"


# --- Task broker interface ---

def fetch_tasks() -> list:
    try:
        r = httpx.get(f"{BROKER_URL}/tasks", params={"status": "todo", "assigned_to": WORKER_ID}, timeout=5)
        return r.json()
    except Exception as e:
        log(f"Broker unreachable: {e}")
        return []


def update_task(task_id: str, status: str, notes: str = ""):
    try:
        httpx.patch(f"{BROKER_URL}/tasks/{task_id}", json={"status": status, "notes": notes}, timeout=5)
    except Exception as e:
        log(f"Failed to update task {task_id}: {e}")


def increment_attempts(task_id: str, current: int):
    try:
        httpx.patch(f"{BROKER_URL}/tasks/{task_id}", json={"attempts": current + 1}, timeout=5)
    except Exception:
        pass


# --- MCP tool execution ---

def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Call the mock MCP server to execute a tool."""
    endpoint_map = {
        "query_buildings": "/tools/list_buildings",
        "query_inspections": "/tools/inspections_this_month",
        "query_overdue_followups": "/tools/overdue_followups",
        "query_clients": "/tools/list_clients",
        "estimate_retrofit": "/tools/estimate_retrofit/{building_id}",
    }

    path = endpoint_map.get(tool_name)
    if not path:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})

    try:
        if "{building_id}" in path:
            path = path.format(building_id=tool_input.get("building_id", "B-001"))

        r = httpx.get(f"{MCP_URL}{path}", timeout=10)
        return r.text
    except Exception as e:
        return json.dumps({"error": str(e)})


# --- Claude SDK session ---

SYSTEM_PROMPT = """You are a field service business worker agent. You help manage inspections,
client follow-ups, and cost estimates for fire protection systems.

Your capabilities:
- Query building and inspection databases
- Identify overdue follow-ups
- Generate cost estimates for retrofits
- Produce summary reports

Rules:
- Be concise and factual
- Use the tools available to gather data before answering
- Format reports clearly with sections and numbers
- All currency is in CAD
"""


def execute_task_with_claude(task: dict) -> str:
    """Run a Claude SDK session to execute the task."""
    client = Anthropic()

    messages = [
        {"role": "user", "content": f"Please execute this task:\n\nTitle: {task['title']}\nDescription: {task['description']}\n\nUse the available tools to gather data, then provide a complete result."}
    ]

    # Agentic loop: keep going until Claude stops using tools
    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=messages,
            tools=TOOLS,
        )

        # Check if Claude wants to use tools
        tool_uses = [b for b in response.content if b.type == "tool_use"]

        if not tool_uses:
            # No more tool calls — extract final text
            text_blocks = [b.text for b in response.content if b.type == "text"]
            return "\n".join(text_blocks) if text_blocks else "(no output)"

        # Process tool calls
        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for tool_use in tool_uses:
            log(f"  Tool: {tool_use.name}({json.dumps(tool_use.input)})")
            result = execute_tool(tool_use.name, tool_use.input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": result,
            })

        messages.append({"role": "user", "content": tool_results})


# --- Main worker loop ---

def main():
    log(f"Worker '{WORKER_ID}' starting. Model: {MODEL}")
    log(f"Broker: {BROKER_URL} | MCP: {MCP_URL}")
    log(f"Polling every {POLL_INTERVAL}s. Ctrl+C to stop.\n")

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: Set ANTHROPIC_API_KEY in your environment or .env file.")
        sys.exit(1)

    while True:
        # Step 1: Guardian — check health
        health = check_health()
        if health == "red":
            log("HEALTH RED — deferring tasks, waiting for recovery.")
            time.sleep(30)
            continue
        elif health == "yellow":
            log("HEALTH YELLOW — operating with caution.")
        elif health == "unknown":
            log("No health file found. Running without health gate.")

        # Step 2: Poll for tasks
        tasks = fetch_tasks()
        if not tasks:
            time.sleep(POLL_INTERVAL)
            continue

        # Step 3: Process each task
        for task in tasks:
            task_id = task["id"]
            attempts = task.get("attempts", 0)

            # Circuit breaker
            if attempts >= MAX_ATTEMPTS:
                log(f"CIRCUIT BREAKER: Task '{task['title']}' hit {MAX_ATTEMPTS} attempts. Moving to review.")
                update_task(task_id, "review", f"Circuit breaker after {MAX_ATTEMPTS} attempts.")
                continue

            log(f"Executing: {task['title']} (attempt {attempts + 1}/{MAX_ATTEMPTS})")
            update_task(task_id, "doing")

            try:
                result = execute_task_with_claude(task)
                log(f"Completed: {task['title']}")
                log(f"--- Result preview ---\n{result[:500]}\n--- End preview ---\n")
                update_task(task_id, "done", result[:2000])
            except Exception as e:
                log(f"FAILED: {task['title']} — {e}")
                increment_attempts(task_id, attempts)
                if attempts + 1 >= MAX_ATTEMPTS:
                    update_task(task_id, "review", f"Failed after {attempts + 1} attempts: {e}")
                else:
                    update_task(task_id, "todo")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
