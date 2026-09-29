import os
import sqlite3
from pathlib import Path
from typing import List, Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

BASE = Path(__file__).parent
DB_FILE = os.environ.get("DB_PATH", str(BASE / "todos.db"))

app = FastAPI(title="Todo List")

Priority = Literal["low", "medium", "high"]


def run(sql, params=(), fetch=False):
    """Open the SQLite database, run one query, and close it again."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(sql, params)
        rows = [dict(r) for r in cur.fetchall()] if fetch else None
        conn.commit()
        return rows
    finally:
        conn.close()


# Create the table the first time the app starts
run(
    """CREATE TABLE IF NOT EXISTS todos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT NOT NULL,
        done INTEGER NOT NULL DEFAULT 0,
        position INTEGER NOT NULL
    )"""
)

# Upgrade an older database by adding the newer columns (keeps your old items)
existing = {r["name"] for r in run("PRAGMA table_info(todos)", fetch=True)}
for column, definition in [
    ("notes", "TEXT NOT NULL DEFAULT ''"),
    ("due_date", "TEXT NOT NULL DEFAULT ''"),
    ("priority", "TEXT NOT NULL DEFAULT 'medium'"),
]:
    if column not in existing:
        run(f"ALTER TABLE todos ADD COLUMN {column} {definition}")


class NewTodo(BaseModel):
    text: str
    notes: str = ""
    due_date: str = ""
    priority: Priority = "medium"


class TodoUpdate(BaseModel):
    text: Optional[str] = None
    done: Optional[bool] = None
    notes: Optional[str] = None
    due_date: Optional[str] = None
    priority: Optional[Priority] = None


class Order(BaseModel):
    ids: List[int]


@app.get("/api/todos")
def list_todos():
    rows = run("SELECT * FROM todos ORDER BY position", fetch=True)
    for r in rows:
        r["done"] = bool(r["done"])
    return rows


@app.post("/api/todos")
def add_todo(todo: NewTodo):
    if not todo.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    last = run("SELECT COALESCE(MAX(position), 0) AS m FROM todos", fetch=True)[0]["m"]
    run(
        "INSERT INTO todos (text, notes, due_date, priority, position) VALUES (?, ?, ?, ?, ?)",
        (todo.text.strip(), todo.notes, todo.due_date, todo.priority, last + 1),
    )
    return {"ok": True}


@app.put("/api/todos/order")
def reorder(order: Order):
    for position, todo_id in enumerate(order.ids):
        run("UPDATE todos SET position = ? WHERE id = ?", (position, todo_id))
    return {"ok": True}


@app.patch("/api/todos/{todo_id}")
def update_todo(todo_id: int, update: TodoUpdate):
    changes = update.model_dump(exclude_unset=True)
    if not changes:
        return {"ok": True}
    if "done" in changes:
        changes["done"] = int(changes["done"])
    # the column names come from our own model above, never from the user
    assignments = ", ".join(f"{name} = ?" for name in changes)
    run(f"UPDATE todos SET {assignments} WHERE id = ?", (*changes.values(), todo_id))
    return {"ok": True}


@app.delete("/api/todos/{todo_id}")
def delete_todo(todo_id: int):
    run("DELETE FROM todos WHERE id = ?", (todo_id,))
    return {"ok": True}


@app.get("/")
def home():
    return FileResponse(BASE / "static" / "index.html")
