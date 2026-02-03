import json
import os
import re
import sqlite3
import threading
import time
import uuid
from typing import Any, Dict, List, Optional


class QuickReportStore:
    def __init__(self, base_dir: str) -> None:
        self.base_dir = base_dir
        self.db_path = os.path.join(base_dir, "data", "store.db")
        self.reports_dir = os.path.join(base_dir, "data", "quick_reports")
        self._lock = threading.Lock()
        self._ensure_db()
        os.makedirs(self.reports_dir, exist_ok=True)

    def _ensure_db(self) -> None:
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS quick_reports (
                    report_id TEXT PRIMARY KEY,
                    created_at INTEGER NOT NULL,
                    title TEXT,
                    payload TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def create_report(self, payload: Dict[str, Any], title: str = "") -> str:
        report_id = uuid.uuid4().hex
        now = int(time.time())
        data = json.dumps(payload, ensure_ascii=False)
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO quick_reports (report_id, created_at, title, payload) VALUES (?, ?, ?, ?)",
                (report_id, now, title, data),
            )
            conn.commit()
        return report_id

    def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT report_id, created_at, title, payload FROM quick_reports WHERE report_id = ?",
                (report_id,),
            ).fetchone()
        if not row:
            return None
        payload = json.loads(row[3])
        report_id = row[0]
        html_content = payload.get("html_content", "") or ""
        file_path = payload.get("file_path") or os.path.join(self.reports_dir, f"{report_id}.html")
        file_url = payload.get("file_url") or f"/quick-reports-files/{report_id}.html"
        if html_content:
            self._ensure_report_file(file_path, html_content)
        elif os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as handle:
                    html_content = handle.read()
                payload["html_content"] = html_content
            except OSError:
                pass
        payload.update(
            {
                "report_id": report_id,
                "created_at": row[1],
                "title": row[2] or payload.get("title", ""),
                "file_path": file_path,
                "file_url": file_url,
            }
        )
        return payload

    def list_reports(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT report_id, created_at, title, payload
                FROM quick_reports
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        items: List[Dict[str, Any]] = []
        for row in rows:
            payload = json.loads(row[3])
            report_id = row[0]
            summary = payload.get("summary", "") or ""
            if not summary:
                html_content = payload.get("html_content", "") or ""
                summary = _strip_html(html_content)[:120]
            if not summary:
                summary = payload.get("prompt", "")[:120]
            summary_line = summary.splitlines()[0] if summary else ""
            html_content = payload.get("html_content", "") or ""
            file_path = payload.get("file_path") or os.path.join(self.reports_dir, f"{report_id}.html")
            file_url = payload.get("file_url") or f"/quick-reports-files/{report_id}.html"
            if html_content:
                self._ensure_report_file(file_path, html_content)
            prompt = payload.get("prompt", "") or ""
            prompt_preview = prompt[:200]
            title = row[2] or ""
            if not title:
                title = prompt_preview
            items.append(
                {
                    "report_id": report_id,
                    "created_at": row[1],
                    "title": title,
                    "summary_line": summary_line,
                    "file_url": file_url,
                    "prompt_preview": prompt_preview,
                }
            )
        return items

    def delete_report(self, report_id: str) -> bool:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT 1 FROM quick_reports WHERE report_id = ?",
                (report_id,),
            ).fetchone()
            if not row:
                return False
            conn.execute("DELETE FROM quick_reports WHERE report_id = ?", (report_id,))
            conn.commit()
        return True

    def _ensure_report_file(self, file_path: str, html_content: str) -> None:
        if not file_path:
            return
        if os.path.exists(file_path):
            return
        try:
            with open(file_path, "w", encoding="utf-8") as handle:
                handle.write(html_content)
        except OSError:
            return

    def update_report(self, report_id: str, payload: Dict[str, Any], title: str = "") -> bool:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT 1 FROM quick_reports WHERE report_id = ?",
                (report_id,),
            ).fetchone()
            if not row:
                return False
            conn.execute(
                "UPDATE quick_reports SET title = ?, payload = ? WHERE report_id = ?",
                (title, json.dumps(payload, ensure_ascii=False), report_id),
            )
            conn.commit()
        return True


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)
