#!/usr/bin/env python3
"""
Health Monitor — Checks service status and writes health.json.

Run periodically (e.g., every 30 seconds in demo mode) to update
the health file that the worker reads before executing tasks.
"""

import json
import shutil
import time
import os
import httpx
from datetime import datetime, timezone

HEALTH_FILE = os.environ.get("HEALTH_FILE", "health.json")

SERVICES = {
    "task-broker": os.environ.get("BROKER_URL", "http://localhost:8090") + "/health",
    "mock-mcp": os.environ.get("MCP_URL", "http://localhost:8091") + "/health",
}


def check_endpoint(url: str, timeout: float = 3.0) -> str:
    try:
        r = httpx.get(url, timeout=timeout)
        if r.status_code == 200:
            return "green"
        return "yellow"
    except Exception:
        return "red"


def check_system():
    disk = shutil.disk_usage("/")
    disk_pct = round(disk.used / disk.total * 100, 1)

    try:
        with open("/proc/meminfo") as f:
            lines = f.readlines()
        mem = {}
        for line in lines:
            parts = line.split()
            if parts[0] in ("MemTotal:", "MemAvailable:"):
                mem[parts[0].rstrip(":")] = int(parts[1])
        mem_pct = round((1 - mem.get("MemAvailable", 0) / mem.get("MemTotal", 1)) * 100, 1)
    except Exception:
        mem_pct = 0.0

    return {"disk_usage_percent": disk_pct, "memory_usage_percent": mem_pct}


def run_health_check():
    services = {}
    for name, url in SERVICES.items():
        services[name] = check_endpoint(url)

    system = check_system()

    # Determine overall status
    statuses = list(services.values())
    if "red" in statuses or system["disk_usage_percent"] > 95:
        overall = "red"
    elif "yellow" in statuses or system["disk_usage_percent"] > 80:
        overall = "yellow"
    else:
        overall = "green"

    health = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "overall": overall,
        "services": services,
        "system": system,
    }

    with open(HEALTH_FILE, "w") as f:
        json.dump(health, f, indent=2)

    return health


def main():
    print("Health Monitor started. Checking every 30 seconds.")
    while True:
        health = run_health_check()
        status_str = " | ".join(f"{k}={v}" for k, v in health["services"].items())
        print(f"[{health['timestamp']}] {health['overall'].upper()} — {status_str} — disk={health['system']['disk_usage_percent']}%")
        time.sleep(30)


if __name__ == "__main__":
    main()
