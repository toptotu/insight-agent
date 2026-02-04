import json
import os
import re
import threading
import time
import uuid
from typing import Any, Dict, List, Optional


class QuickReportManager:
    def __init__(self, base_dir: str) -> None:
        self.base_dir = base_dir
        self.reports_dir = os.path.join(base_dir, "data", "quick_reports")
        self._lock = threading.Lock()
        os.makedirs(self.reports_dir, exist_ok=True)

    def list_reports(self, limit: int = 200) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        report_ids = set()
        for filename in os.listdir(self.reports_dir):
            if filename.endswith(".json"):
                report_id = filename.replace(".json", "")
                report_ids.add(report_id)
                meta = self._read_meta(report_id)
                if meta:
                    items.append(meta)
        for filename in os.listdir(self.reports_dir):
            if not filename.endswith(".html"):
                continue
            report_id = filename.replace(".html", "")
            if report_id in report_ids:
                continue
            meta = self.get_report(report_id)
            if meta:
                items.append(meta)
        items.sort(key=lambda item: item.get("created_at", 0), reverse=True)
        return items[:limit]

    def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        meta = self._read_meta(report_id)
        if meta:
            return meta
        html_path = self._html_path(report_id)
        if not os.path.exists(html_path):
            return None
        try:
            with open(html_path, "r", encoding="utf-8") as handle:
                html_content = handle.read()
        except OSError:
            return None
        created_at = int(os.path.getmtime(html_path))
        meta = self._build_meta(
            report_id=report_id,
            prompt="",
            html_content=html_content,
            created_at=created_at,
        )
        self._write_meta(report_id, meta)
        return meta

    def create_report(self, prompt: str, html_content: str) -> Dict[str, Any]:
        report_id = uuid.uuid4().hex
        created_at = int(time.time())
        meta = self._build_meta(report_id=report_id, prompt=prompt, html_content=html_content, created_at=created_at)
        self._write_html(report_id, html_content)
        self._write_meta(report_id, meta)
        return meta

    def update_report(self, report_id: str, html_content: str) -> Optional[Dict[str, Any]]:
        meta = self._read_meta(report_id)
        if not meta:
            return None
        meta["html_content"] = html_content
        meta["summary"] = _strip_html(html_content)[:200]
        meta["summary_line"] = meta["summary"].splitlines()[0] if meta["summary"] else ""
        self._write_html(report_id, html_content)
        self._write_meta(report_id, meta)
        return meta

    def delete_report(self, report_id: str) -> bool:
        meta_path = self._meta_path(report_id)
        html_path = self._html_path(report_id)
        deleted = False
        for path in (meta_path, html_path):
            if os.path.exists(path):
                try:
                    os.remove(path)
                    deleted = True
                except OSError:
                    continue
        return deleted

    def _build_meta(
        self, report_id: str, prompt: str, html_content: str, created_at: int
    ) -> Dict[str, Any]:
        summary = _strip_html(html_content)[:200]
        title = (prompt or report_id)[:80]
        return {
            "report_id": report_id,
            "created_at": created_at,
            "title": title,
            "prompt": prompt,
            "prompt_preview": prompt[:200],
            "summary": summary,
            "summary_line": summary.splitlines()[0] if summary else "",
            "file_path": self._html_path(report_id),
            "file_url": f"/quick-reports-files/{report_id}.html",
            "html_content": html_content,
        }

    def _read_meta(self, report_id: str) -> Optional[Dict[str, Any]]:
        path = self._meta_path(report_id)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except (OSError, json.JSONDecodeError):
            return None

    def _write_meta(self, report_id: str, meta: Dict[str, Any]) -> None:
        path = self._meta_path(report_id)
        with self._lock:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(meta, handle, ensure_ascii=False, indent=2)

    def _write_html(self, report_id: str, html_content: str) -> None:
        path = self._html_path(report_id)
        with self._lock:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(html_content)

    def _meta_path(self, report_id: str) -> str:
        return os.path.join(self.reports_dir, f"{report_id}.json")

    def _html_path(self, report_id: str) -> str:
        return os.path.join(self.reports_dir, f"{report_id}.html")


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)
