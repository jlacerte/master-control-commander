#!/usr/bin/env python3
"""
Task Broker — SQLite-based task queue (zero external dependencies).

Exposes a simple REST API for workers to poll, claim, and update tasks.
In production, this role is filled by Supabase/Archon.
"""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from contextlib import contextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Task Broker (Demo)")

DB_PATH = "tasks.db"


def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                status TEXT DEFAULT 'todo',
                assigned_to TEXT DEFAULT NULL,
                attempts INTEGER DEFAULT 0,
                created_at TEXT,
                updated_at TEXT,
                notes TEXT DEFAULT ''
            )
        """)


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


class TaskCreate(BaseModel):
    title: str
    description: str = ""
    assigned_to: str = "demo-worker"


class TaskUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    attempts: Optional[int] = None


@app.on_event("startup")
def startup():
    init_db()
    seed_demo_tasks()


def seed_demo_tasks():
    """Pre-load demo tasks if the database is empty."""
    with get_db() as db:
        count = db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        if count > 0:
            return

    demo_tasks = [
        {
            "title": "Generate monthly inspection summary",
            "description": "Query the database for all inspections completed this month and produce a summary report.",
        },
        {
            "title": "Check overdue follow-ups",
            "description": "Review the client database for any follow-up actions that are past their due date.",
        },
        {
            "title": "Draft estimate for building retrofit",
            "description": "Based on the asset database, prepare a cost estimate for retrofitting Building C with updated equipment.",
        },
    ]
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as db:
        for t in demo_tasks:
            db.execute(
                "INSERT INTO tasks (id, title, description, status, assigned_to, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), t["title"], t["description"], "todo", "demo-worker", now, now),
            )
    print(f"Seeded {len(demo_tasks)} demo tasks.")


@app.get("/health")
def health():
    return {"status": "ok", "service": "task-broker"}


@app.get("/tasks")
def list_tasks(status: str = None, assigned_to: str = None):
    query = "SELECT * FROM tasks WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if assigned_to:
        query += " AND assigned_to = ?"
        params.append(assigned_to)
    query += " ORDER BY created_at ASC"

    with get_db() as db:
        rows = db.execute(query, params).fetchall()
    return [dict(r) for r in rows]


@app.get("/tasks/{task_id}")
def get_task(task_id: str):
    with get_db() as db:
        row = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Task not found")
    return dict(row)


@app.post("/tasks")
def create_task(task: TaskCreate):
    now = datetime.now(timezone.utc).isoformat()
    task_id = str(uuid.uuid4())
    with get_db() as db:
        db.execute(
            "INSERT INTO tasks (id, title, description, assigned_to, status, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
            (task_id, task.title, task.description, task.assigned_to, "todo", now, now),
        )
    return {"id": task_id, "status": "created"}


@app.patch("/tasks/{task_id}")
def update_task(task_id: str, update: TaskUpdate):
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as db:
        row = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Task not found")

        fields = []
        params = []
        if update.status is not None:
            fields.append("status = ?")
            params.append(update.status)
        if update.notes is not None:
            fields.append("notes = ?")
            params.append(update.notes)
        if update.attempts is not None:
            fields.append("attempts = ?")
            params.append(update.attempts)

        if fields:
            fields.append("updated_at = ?")
            params.append(now)
            params.append(task_id)
            db.execute(f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?", params)

    return {"id": task_id, "status": "updated"}
