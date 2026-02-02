import html
import os
import re
import threading
import time
from typing import Dict, Optional

import requests

from app.config_store import ConfigStore
from app.rag import RAGStore


def extract_text(content: str) -> str:
    if "<" in content and ">" in content:
        content = re.sub(r"(?is)<(script|style).*?>.*?(</\\1>)", " ", content)
        content = re.sub(r"(?s)<[^>]+>", " ", content)
    content = html.unescape(content)
    content = re.sub(r"\\s+", " ", content).strip()
    return content


class CrawlerService:
    def __init__(self, config_store: ConfigStore, rag_store: RAGStore) -> None:
        self.config_store = config_store
        self.rag_store = rag_store
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._interval = int(os.getenv("CRAWLER_CHECK_INTERVAL", "60"))
        self._max_chars = int(os.getenv("CRAWLER_MAX_CHARS", "5000"))

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.run_due_sources()
            except Exception:
                pass
            self._stop_event.wait(self._interval)

    def run_due_sources(self) -> None:
        now = int(time.time())
        for source in self.config_store.list_crawlers():
            if not source.get("enabled", True):
                continue
            next_run_at = source.get("next_run_at")
            if next_run_at and now < next_run_at:
                continue
            self.run_source(source)

    def run_source(self, source: Dict[str, object]) -> Dict[str, object]:
        now = int(time.time())
        interval = int(source.get("interval_minutes") or 1440)
        next_run_at = now + max(1, interval) * 60
        source_id = str(source.get("source_id"))
        try:
            response = requests.get(str(source.get("url")), timeout=20)
            response.raise_for_status()
            text = extract_text(response.text)
            text = text[: self._max_chars]
            if not text:
                raise ValueError("Empty content")
            title = f"{source.get('name')} - {time.strftime('%Y-%m-%d')}"
            doc = self.config_store.create_document(
                domain_id=str(source.get("domain_id")),
                title=title,
                source=str(source.get("url")),
                source_type=str(source.get("source_type") or "crawler"),
                content=text,
            )
            self.rag_store.invalidate(str(source.get("domain_id")))
            self.config_store.update_crawler_status(
                source_id=source_id,
                status="success",
                last_run_at=now,
                next_run_at=next_run_at,
            )
            return {"status": "success", "document": doc}
        except Exception as exc:
            self.config_store.update_crawler_status(
                source_id=source_id,
                status=f"error: {exc}",
                last_run_at=now,
                next_run_at=next_run_at,
            )
            return {"status": "error", "message": str(exc)}
