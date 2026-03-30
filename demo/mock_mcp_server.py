#!/usr/bin/env python3
"""
Mock MCP Server — Simulates domain-specific API tools.

In production, each MCP server wraps a real API (ERP, CRM, Email, etc.).
This mock returns plausible data so the demo worker can complete tasks
without external service credentials.
"""

import random
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI

app = FastAPI(title="Mock MCP Server (Demo)")

# --- Simulated data ---

BUILDINGS = [
    {"id": "B-001", "name": "Warehouse District A", "address": "120 Industrial Blvd", "last_inspection": "2025-11-15", "system_type": "wet", "heads": 84},
    {"id": "B-002", "name": "Office Tower Centre", "address": "500 Main St", "last_inspection": "2026-01-22", "system_type": "dry", "heads": 210},
    {"id": "B-003", "name": "School Complex North", "address": "45 Education Rd", "last_inspection": "2025-09-03", "system_type": "wet", "heads": 156},
    {"id": "B-004", "name": "Hospital Wing B", "address": "1 Health Ave", "last_inspection": "2026-02-10", "system_type": "pre-action", "heads": 320},
    {"id": "B-005", "name": "Retail Centre South", "address": "800 Commerce Dr", "last_inspection": "2025-07-20", "system_type": "wet", "heads": 62},
]

CLIENTS = [
    {"id": "C-001", "name": "Regional Health Authority", "contact": "procurement@health.example.com", "balance": 12500.00},
    {"id": "C-002", "name": "Municipal School Board", "contact": "facilities@schools.example.com", "balance": 0.00},
    {"id": "C-003", "name": "Industrial Properties Inc.", "contact": "ops@indprop.example.com", "balance": 3200.00},
]


@app.get("/health")
def health():
    return {"status": "ok", "service": "mock-mcp"}


@app.get("/tools/list_buildings")
def list_buildings():
    return {"buildings": BUILDINGS}


@app.get("/tools/get_building/{building_id}")
def get_building(building_id: str):
    for b in BUILDINGS:
        if b["id"] == building_id:
            return b
    return {"error": "Building not found"}


@app.get("/tools/list_clients")
def list_clients():
    return {"clients": CLIENTS}


@app.get("/tools/inspections_this_month")
def inspections_this_month():
    """Simulate inspection data for the current month."""
    now = datetime.now(timezone.utc)
    inspections = []
    for b in random.sample(BUILDINGS, min(3, len(BUILDINGS))):
        day = random.randint(1, min(now.day, 28))
        inspections.append({
            "building_id": b["id"],
            "building_name": b["name"],
            "date": f"{now.year}-{now.month:02d}-{day:02d}",
            "result": random.choice(["pass", "pass", "pass", "minor_deficiency"]),
            "inspector": "Field Tech",
            "system_type": b["system_type"],
            "heads_tested": b["heads"],
        })
    return {"month": now.strftime("%Y-%m"), "inspections": inspections}


@app.get("/tools/overdue_followups")
def overdue_followups():
    """Return simulated overdue follow-up items."""
    now = datetime.now(timezone.utc)
    return {
        "overdue": [
            {
                "client": CLIENTS[0]["name"],
                "action": "Send inspection certificate",
                "due_date": (now - timedelta(days=5)).strftime("%Y-%m-%d"),
                "priority": "high",
            },
            {
                "client": CLIENTS[2]["name"],
                "action": "Follow up on estimate #E-2026-042",
                "due_date": (now - timedelta(days=12)).strftime("%Y-%m-%d"),
                "priority": "medium",
            },
        ]
    }


@app.get("/tools/estimate_retrofit/{building_id}")
def estimate_retrofit(building_id: str):
    """Generate a simulated cost estimate for a building retrofit."""
    building = None
    for b in BUILDINGS:
        if b["id"] == building_id:
            building = b
            break
    if not building:
        return {"error": "Building not found"}

    cost_per_head = random.uniform(85, 150)
    labour_hours = building["heads"] * 0.5
    labour_rate = 95.0
    materials = round(building["heads"] * cost_per_head, 2)
    labour = round(labour_hours * labour_rate, 2)

    return {
        "building": building["name"],
        "building_id": building_id,
        "system_type": building["system_type"],
        "heads": building["heads"],
        "materials_cost": materials,
        "labour_cost": labour,
        "subtotal": round(materials + labour, 2),
        "tax_rate": 0.14975,
        "total": round((materials + labour) * 1.14975, 2),
        "validity_days": 30,
    }
