import json
import os
import sqlite3
import threading
import time
import uuid
from typing import Any, Dict, Optional


class TaskStore:
    def __init__(self, base_dir: str) -> None:
        self.base_dir = base_dir
        self.db_path = os.path.join(base_dir, "data", "store.db")
        self._lock = threading.Lock()
        self._ensure_db()

    def _ensure_db(self) -> None:
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    created_at INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def create_task(self, payload: Dict[str, Any], status: str = "completed") -> str:
        task_id = uuid.uuid4().hex
        now = int(time.time())
        data = json.dumps(payload, ensure_ascii=False)
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO tasks (task_id, created_at, status, payload) VALUES (?, ?, ?, ?)",
                (task_id, now, status, data),
            )
            conn.commit()
        return task_id

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT task_id, created_at, status, payload FROM tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        if not row:
            return None
        payload = json.loads(row[3])
        payload.update({"task_id": row[0], "created_at": row[1], "status": row[2]})
        return payload
