import json
import os
import re
import sqlite3
import threading
import time
import uuid
from typing import Any, Dict, List, Optional


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9\\-\\s]", "", value)
    value = re.sub(r"\\s+", "-", value)
    return value.strip("-")


def _generate_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


class ConfigStore:
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
                CREATE TABLE IF NOT EXISTS custom_domains (
                    domain_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    default_agents TEXT,
                    default_skills TEXT,
                    created_at INTEGER NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS custom_agents (
                    agent_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    focus TEXT,
                    description TEXT,
                    default_query TEXT,
                    skill_ids TEXT,
                    category TEXT,
                    domain_id TEXT,
                    created_at INTEGER NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS custom_skills (
                    skill_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    category TEXT,
                    mode TEXT,
                    input_fields TEXT,
                    output_fields TEXT,
                    prompt_template TEXT,
                    tags TEXT,
                    example_output TEXT,
                    created_at INTEGER NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS custom_documents (
                    doc_id TEXT PRIMARY KEY,
                    domain_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    source TEXT,
                    source_type TEXT,
                    content TEXT,
                    created_at INTEGER NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS disabled_items (
                    item_type TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    updated_at INTEGER NOT NULL,
                    PRIMARY KEY (item_type, item_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS crawler_sources (
                    source_id TEXT PRIMARY KEY,
                    domain_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    source_type TEXT,
                    description TEXT,
                    interval_minutes INTEGER,
                    enabled INTEGER,
                    last_run_at INTEGER,
                    next_run_at INTEGER,
                    status TEXT,
                    created_at INTEGER NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS report_templates (
                    template_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    sections TEXT,
                    created_at INTEGER NOT NULL
                )
                """
            )
            conn.commit()
        self._ensure_agent_category_column()
        self._ensure_skill_columns()
        self._ensure_domain_columns()
        self._ensure_crawler_columns()
        self._ensure_report_template_columns()

    def _ensure_agent_category_column(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            columns = [row[1] for row in conn.execute("PRAGMA table_info(custom_agents)").fetchall()]
            if "category" not in columns:
                conn.execute("ALTER TABLE custom_agents ADD COLUMN category TEXT")
                conn.commit()

    def _ensure_skill_columns(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            columns = [row[1] for row in conn.execute("PRAGMA table_info(custom_skills)").fetchall()]
            column_defs = {
                "category": "TEXT",
                "mode": "TEXT",
                "input_fields": "TEXT",
                "output_fields": "TEXT",
                "prompt_template": "TEXT",
                "tags": "TEXT",
                "example_output": "TEXT",
            }
            for column, data_type in column_defs.items():
                if column not in columns:
                    conn.execute(f"ALTER TABLE custom_skills ADD COLUMN {column} {data_type}")
            conn.commit()

    def _ensure_domain_columns(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            columns = [row[1] for row in conn.execute("PRAGMA table_info(custom_domains)").fetchall()]
            if "default_agents" not in columns:
                conn.execute("ALTER TABLE custom_domains ADD COLUMN default_agents TEXT")
            if "default_skills" not in columns:
                conn.execute("ALTER TABLE custom_domains ADD COLUMN default_skills TEXT")
            conn.commit()

    def _ensure_crawler_columns(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            columns = [row[1] for row in conn.execute("PRAGMA table_info(crawler_sources)").fetchall()]
            column_defs = {
                "source_type": "TEXT",
                "description": "TEXT",
                "interval_minutes": "INTEGER",
                "enabled": "INTEGER",
                "last_run_at": "INTEGER",
                "next_run_at": "INTEGER",
                "status": "TEXT",
            }
            for column, data_type in column_defs.items():
                if column not in columns:
                    conn.execute(f"ALTER TABLE crawler_sources ADD COLUMN {column} {data_type}")
            conn.commit()

    def _ensure_report_template_columns(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            columns = [row[1] for row in conn.execute("PRAGMA table_info(report_templates)").fetchall()]
            column_defs = {
                "description": "TEXT",
                "sections": "TEXT",
            }
            for column, data_type in column_defs.items():
                if column not in columns:
                    conn.execute(f"ALTER TABLE report_templates ADD COLUMN {column} {data_type}")
            conn.commit()

    def disable_item(self, item_type: str, item_id: str) -> None:
        now = int(time.time())
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO disabled_items (item_type, item_id, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(item_type, item_id) DO UPDATE SET updated_at = excluded.updated_at
                """,
                (item_type, item_id, now),
            )
            conn.commit()

    def enable_item(self, item_type: str, item_id: str) -> None:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM disabled_items WHERE item_type = ? AND item_id = ?",
                (item_type, item_id),
            )
            conn.commit()

    def get_disabled_ids(self, item_type: str) -> List[str]:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT item_id FROM disabled_items WHERE item_type = ?",
                (item_type,),
            ).fetchall()
        return [row[0] for row in rows]

    def list_domains(self) -> List[Dict[str, Any]]:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT domain_id, name, description, default_agents, default_skills, created_at
                FROM custom_domains
                ORDER BY created_at DESC
                """
            ).fetchall()
        return [
            {
                "domain_id": row[0],
                "name": row[1],
                "description": row[2] or "",
                "default_agents": json.loads(row[3]) if row[3] else [],
                "default_skills": json.loads(row[4]) if row[4] else [],
                "created_at": row[5],
            }
            for row in rows
        ]

    def create_domain(
        self,
        name: str,
        description: str = "",
        domain_id: Optional[str] = None,
        default_agents: Optional[List[str]] = None,
        default_skills: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        now = int(time.time())
        if not domain_id:
            slug = _slugify(name)
            domain_id = _generate_id(slug or "custom-domain")
        default_agents_payload = json.dumps(default_agents or [], ensure_ascii=False)
        default_skills_payload = json.dumps(default_skills or [], ensure_ascii=False)
        with self._lock, sqlite3.connect(self.db_path) as conn:
            exists = conn.execute(
                "SELECT 1 FROM custom_domains WHERE domain_id = ?",
                (domain_id,),
            ).fetchone()
            if exists:
                raise ValueError("domain_id already exists")
            conn.execute(
                """
                INSERT INTO custom_domains (domain_id, name, description, default_agents, default_skills, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (domain_id, name, description, default_agents_payload, default_skills_payload, now),
            )
            conn.commit()
        return {
            "domain_id": domain_id,
            "name": name,
            "description": description,
            "default_agents": default_agents or [],
            "default_skills": default_skills or [],
            "created_at": now,
        }

    def update_domain(self, domain_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT domain_id, name, description, default_agents, default_skills, created_at
                FROM custom_domains WHERE domain_id = ?
                """,
                (domain_id,),
            ).fetchone()
            if not row:
                return None
            name = updates.get("name", row[1])
            description = updates.get("description", row[2])
            default_agents = updates.get(
                "default_agents", json.loads(row[3]) if row[3] else []
            )
            default_skills = updates.get(
                "default_skills", json.loads(row[4]) if row[4] else []
            )
            conn.execute(
                """
                UPDATE custom_domains
                SET name = ?, description = ?, default_agents = ?, default_skills = ?
                WHERE domain_id = ?
                """,
                (
                    name,
                    description,
                    json.dumps(default_agents, ensure_ascii=False),
                    json.dumps(default_skills, ensure_ascii=False),
                    domain_id,
                ),
            )
            conn.commit()
        return {
            "domain_id": domain_id,
            "name": name,
            "description": description,
            "default_agents": default_agents,
            "default_skills": default_skills,
        }

    def delete_domain(self, domain_id: str) -> None:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM custom_domains WHERE domain_id = ?", (domain_id,))
            conn.commit()

    def list_agents(self) -> List[Dict[str, Any]]:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT agent_id, name, focus, description, default_query, skill_ids, category, domain_id, created_at
                FROM custom_agents
                ORDER BY created_at DESC
                """
            ).fetchall()
        agents = []
        for row in rows:
            skill_ids = json.loads(row[5]) if row[5] else []
            agents.append(
                {
                    "agent_id": row[0],
                    "name": row[1],
                    "focus": row[2] or "",
                    "description": row[3] or "",
                    "default_query": row[4] or "",
                    "skill_ids": skill_ids,
                    "category": row[6] or "",
                    "domain_id": row[7] or "",
                    "created_at": row[8],
                }
            )
        return agents

    def create_agent(
        self,
        name: str,
        focus: str,
        description: str,
        default_query: str,
        skill_ids: List[str],
        domain_id: str = "",
        agent_id: Optional[str] = None,
        category: str = "",
    ) -> Dict[str, Any]:
        now = int(time.time())
        if not agent_id:
            agent_id = _generate_id("custom-agent")
        payload = json.dumps(skill_ids, ensure_ascii=False)
        with self._lock, sqlite3.connect(self.db_path) as conn:
            exists = conn.execute(
                "SELECT 1 FROM custom_agents WHERE agent_id = ?",
                (agent_id,),
            ).fetchone()
            if exists:
                raise ValueError("agent_id already exists")
            conn.execute(
                """
                INSERT INTO custom_agents
                (agent_id, name, focus, description, default_query, skill_ids, category, domain_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (agent_id, name, focus, description, default_query, payload, category, domain_id, now),
            )
            conn.commit()
        return {
            "agent_id": agent_id,
            "name": name,
            "focus": focus,
            "description": description,
            "default_query": default_query,
            "skill_ids": skill_ids,
            "category": category,
            "domain_id": domain_id,
            "created_at": now,
        }

    def update_agent(self, agent_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT agent_id, name, focus, description, default_query, skill_ids, category, domain_id
                FROM custom_agents WHERE agent_id = ?
                """,
                (agent_id,),
            ).fetchone()
            if not row:
                return None
            name = updates.get("name", row[1])
            focus = updates.get("focus", row[2])
            description = updates.get("description", row[3])
            default_query = updates.get("default_query", row[4])
            skill_ids = updates.get("skill_ids", json.loads(row[5]) if row[5] else [])
            category = updates.get("category", row[6])
            domain_id = updates.get("domain_id", row[7])
            conn.execute(
                """
                UPDATE custom_agents
                SET name = ?, focus = ?, description = ?, default_query = ?, skill_ids = ?, category = ?, domain_id = ?
                WHERE agent_id = ?
                """,
                (
                    name,
                    focus,
                    description,
                    default_query,
                    json.dumps(skill_ids, ensure_ascii=False),
                    category,
                    domain_id,
                    agent_id,
                ),
            )
            conn.commit()
        return {
            "agent_id": agent_id,
            "name": name,
            "focus": focus,
            "description": description,
            "default_query": default_query,
            "skill_ids": skill_ids,
            "category": category,
            "domain_id": domain_id,
        }

    def delete_agent(self, agent_id: str) -> None:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM custom_agents WHERE agent_id = ?", (agent_id,))
            conn.commit()

    def list_skills(self) -> List[Dict[str, Any]]:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT skill_id, name, description, category, mode, input_fields, output_fields, prompt_template,
                       tags, example_output, created_at
                FROM custom_skills
                ORDER BY created_at DESC
                """
            ).fetchall()
        return [
            {
                "skill_id": row[0],
                "name": row[1],
                "description": row[2] or "",
                "category": row[3] or "",
                "mode": row[4] or "",
                "input_fields": json.loads(row[5]) if row[5] else [],
                "output_fields": json.loads(row[6]) if row[6] else [],
                "prompt_template": row[7] or "",
                "tags": json.loads(row[8]) if row[8] else [],
                "example_output": row[9] or "",
                "created_at": row[10],
            }
            for row in rows
        ]

    def create_skill(
        self,
        name: str,
        description: str = "",
        skill_id: Optional[str] = None,
        category: str = "",
        mode: str = "",
        input_fields: Optional[List[str]] = None,
        output_fields: Optional[List[str]] = None,
        prompt_template: str = "",
        tags: Optional[List[str]] = None,
        example_output: str = "",
    ) -> Dict[str, Any]:
        now = int(time.time())
        if not skill_id:
            skill_id = _generate_id("custom-skill")
        input_fields_payload = json.dumps(input_fields or [], ensure_ascii=False)
        output_fields_payload = json.dumps(output_fields or [], ensure_ascii=False)
        tags_payload = json.dumps(tags or [], ensure_ascii=False)
        with self._lock, sqlite3.connect(self.db_path) as conn:
            exists = conn.execute(
                "SELECT 1 FROM custom_skills WHERE skill_id = ?",
                (skill_id,),
            ).fetchone()
            if exists:
                raise ValueError("skill_id already exists")
            conn.execute(
                """
                INSERT INTO custom_skills
                (skill_id, name, description, category, mode, input_fields, output_fields, prompt_template, tags,
                 example_output, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    skill_id,
                    name,
                    description,
                    category,
                    mode,
                    input_fields_payload,
                    output_fields_payload,
                    prompt_template,
                    tags_payload,
                    example_output,
                    now,
                ),
            )
            conn.commit()
        return {
            "skill_id": skill_id,
            "name": name,
            "description": description,
            "category": category,
            "mode": mode,
            "input_fields": input_fields or [],
            "output_fields": output_fields or [],
            "prompt_template": prompt_template,
            "tags": tags or [],
            "example_output": example_output,
            "created_at": now,
        }

    def update_skill(self, skill_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT skill_id, name, description, category, mode, input_fields, output_fields, prompt_template,
                       tags, example_output
                FROM custom_skills WHERE skill_id = ?
                """,
                (skill_id,),
            ).fetchone()
            if not row:
                return None
            name = updates.get("name", row[1])
            description = updates.get("description", row[2])
            category = updates.get("category", row[3])
            mode = updates.get("mode", row[4])
            input_fields = updates.get("input_fields", json.loads(row[5]) if row[5] else [])
            output_fields = updates.get("output_fields", json.loads(row[6]) if row[6] else [])
            prompt_template = updates.get("prompt_template", row[7])
            tags = updates.get("tags", json.loads(row[8]) if row[8] else [])
            example_output = updates.get("example_output", row[9])
            conn.execute(
                """
                UPDATE custom_skills
                SET name = ?, description = ?, category = ?, mode = ?, input_fields = ?, output_fields = ?,
                    prompt_template = ?, tags = ?, example_output = ?
                WHERE skill_id = ?
                """,
                (
                    name,
                    description,
                    category,
                    mode,
                    json.dumps(input_fields, ensure_ascii=False),
                    json.dumps(output_fields, ensure_ascii=False),
                    prompt_template,
                    json.dumps(tags, ensure_ascii=False),
                    example_output,
                    skill_id,
                ),
            )
            conn.commit()
        return {
            "skill_id": skill_id,
            "name": name,
            "description": description,
            "category": category,
            "mode": mode,
            "input_fields": input_fields,
            "output_fields": output_fields,
            "prompt_template": prompt_template,
            "tags": tags,
            "example_output": example_output,
        }

    def delete_skill(self, skill_id: str) -> None:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM custom_skills WHERE skill_id = ?", (skill_id,))
            conn.commit()

    def list_documents(self, domain_id: Optional[str] = None) -> List[Dict[str, Any]]:
        query = """
            SELECT doc_id, domain_id, title, source, source_type, content, created_at
            FROM custom_documents
        """
        params: List[Any] = []
        if domain_id:
            query += " WHERE domain_id = ?"
            params.append(domain_id)
        query += " ORDER BY created_at DESC"
        with self._lock, sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            {
                "doc_id": row[0],
                "domain_id": row[1],
                "title": row[2],
                "source": row[3] or "",
                "source_type": row[4] or "custom",
                "content": row[5] or "",
                "created_at": row[6],
            }
            for row in rows
        ]

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT doc_id, domain_id, title, source, source_type, content, created_at
                FROM custom_documents WHERE doc_id = ?
                """,
                (doc_id,),
            ).fetchone()
        if not row:
            return None
        return {
            "doc_id": row[0],
            "domain_id": row[1],
            "title": row[2],
            "source": row[3] or "",
            "source_type": row[4] or "custom",
            "content": row[5] or "",
            "created_at": row[6],
        }

    def create_document(
        self,
        domain_id: str,
        title: str,
        source: str,
        source_type: str,
        content: str,
        doc_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        now = int(time.time())
        if not doc_id:
            doc_id = _generate_id("custom-doc")
        with self._lock, sqlite3.connect(self.db_path) as conn:
            exists = conn.execute(
                "SELECT 1 FROM custom_documents WHERE doc_id = ?",
                (doc_id,),
            ).fetchone()
            if exists:
                raise ValueError("doc_id already exists")
            conn.execute(
                """
                INSERT INTO custom_documents
                (doc_id, domain_id, title, source, source_type, content, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (doc_id, domain_id, title, source, source_type, content, now),
            )
            conn.commit()
        return {
            "doc_id": doc_id,
            "domain_id": domain_id,
            "title": title,
            "source": source,
            "source_type": source_type,
            "content": content,
            "created_at": now,
        }

    def update_document(self, doc_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT doc_id, domain_id, title, source, source_type, content
                FROM custom_documents WHERE doc_id = ?
                """,
                (doc_id,),
            ).fetchone()
            if not row:
                return None
            domain_id = updates.get("domain_id", row[1])
            title = updates.get("title", row[2])
            source = updates.get("source", row[3])
            source_type = updates.get("source_type", row[4])
            content = updates.get("content", row[5])
            conn.execute(
                """
                UPDATE custom_documents
                SET domain_id = ?, title = ?, source = ?, source_type = ?, content = ?
                WHERE doc_id = ?
                """,
                (domain_id, title, source, source_type, content, doc_id),
            )
            conn.commit()
        return {
            "doc_id": doc_id,
            "domain_id": domain_id,
            "title": title,
            "source": source,
            "source_type": source_type,
            "content": content,
        }

    def delete_document(self, doc_id: str) -> None:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM custom_documents WHERE doc_id = ?", (doc_id,))
            conn.commit()

    def list_crawlers(self) -> List[Dict[str, Any]]:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT source_id, domain_id, name, url, source_type, description, interval_minutes, enabled,
                       last_run_at, next_run_at, status, created_at
                FROM crawler_sources
                ORDER BY created_at DESC
                """
            ).fetchall()
        return [
            {
                "source_id": row[0],
                "domain_id": row[1],
                "name": row[2],
                "url": row[3],
                "source_type": row[4] or "crawler",
                "description": row[5] or "",
                "interval_minutes": row[6] if row[6] is not None else 1440,
                "enabled": bool(row[7]) if row[7] is not None else True,
                "last_run_at": row[8],
                "next_run_at": row[9],
                "status": row[10] or "",
                "created_at": row[11],
            }
            for row in rows
        ]

    def create_crawler(
        self,
        domain_id: str,
        name: str,
        url: str,
        source_type: str = "crawler",
        description: str = "",
        interval_minutes: int = 1440,
        enabled: bool = True,
        source_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        now = int(time.time())
        if not source_id:
            source_id = _generate_id("crawler")
        next_run_at = now + max(1, interval_minutes) * 60 if enabled else None
        with self._lock, sqlite3.connect(self.db_path) as conn:
            exists = conn.execute(
                "SELECT 1 FROM crawler_sources WHERE source_id = ?",
                (source_id,),
            ).fetchone()
            if exists:
                raise ValueError("source_id already exists")
            conn.execute(
                """
                INSERT INTO crawler_sources
                (source_id, domain_id, name, url, source_type, description, interval_minutes, enabled, last_run_at,
                 next_run_at, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source_id,
                    domain_id,
                    name,
                    url,
                    source_type,
                    description,
                    interval_minutes,
                    1 if enabled else 0,
                    None,
                    next_run_at,
                    "",
                    now,
                ),
            )
            conn.commit()
        return {
            "source_id": source_id,
            "domain_id": domain_id,
            "name": name,
            "url": url,
            "source_type": source_type,
            "description": description,
            "interval_minutes": interval_minutes,
            "enabled": enabled,
            "last_run_at": None,
            "next_run_at": next_run_at,
            "status": "",
            "created_at": now,
        }

    def update_crawler(self, source_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT source_id, domain_id, name, url, source_type, description, interval_minutes, enabled,
                       last_run_at, next_run_at, status
                FROM crawler_sources WHERE source_id = ?
                """,
                (source_id,),
            ).fetchone()
            if not row:
                return None
            domain_id = updates.get("domain_id", row[1])
            name = updates.get("name", row[2])
            url = updates.get("url", row[3])
            source_type = updates.get("source_type", row[4])
            description = updates.get("description", row[5])
            interval_minutes = updates.get("interval_minutes", row[6])
            enabled = updates.get("enabled", bool(row[7]))
            last_run_at = row[8]
            next_run_at = row[9]
            status = row[10]
            if "enabled" in updates or "interval_minutes" in updates:
                next_run_at = (
                    int(time.time()) + max(1, interval_minutes) * 60 if enabled else None
                )
            conn.execute(
                """
                UPDATE crawler_sources
                SET domain_id = ?, name = ?, url = ?, source_type = ?, description = ?, interval_minutes = ?,
                    enabled = ?, next_run_at = ?
                WHERE source_id = ?
                """,
                (
                    domain_id,
                    name,
                    url,
                    source_type,
                    description,
                    interval_minutes,
                    1 if enabled else 0,
                    next_run_at,
                    source_id,
                ),
            )
            conn.commit()
        return {
            "source_id": source_id,
            "domain_id": domain_id,
            "name": name,
            "url": url,
            "source_type": source_type,
            "description": description,
            "interval_minutes": interval_minutes,
            "enabled": enabled,
            "last_run_at": last_run_at,
            "next_run_at": next_run_at,
            "status": status,
        }

    def update_crawler_status(
        self,
        source_id: str,
        status: str,
        last_run_at: Optional[int],
        next_run_at: Optional[int],
    ) -> None:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE crawler_sources
                SET status = ?, last_run_at = ?, next_run_at = ?
                WHERE source_id = ?
                """,
                (status, last_run_at, next_run_at, source_id),
            )
            conn.commit()

    def delete_crawler(self, source_id: str) -> None:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM crawler_sources WHERE source_id = ?", (source_id,))
            conn.commit()

    def list_report_templates(self) -> List[Dict[str, Any]]:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT template_id, name, description, sections, created_at
                FROM report_templates
                ORDER BY created_at DESC
                """
            ).fetchall()
        return [
            {
                "template_id": row[0],
                "name": row[1],
                "description": row[2] or "",
                "sections": json.loads(row[3]) if row[3] else [],
                "created_at": row[4],
            }
            for row in rows
        ]

    def create_report_template(
        self,
        name: str,
        description: str = "",
        sections: Optional[List[Dict[str, Any]]] = None,
        template_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        now = int(time.time())
        if not template_id:
            template_id = _generate_id("report")
        with self._lock, sqlite3.connect(self.db_path) as conn:
            exists = conn.execute(
                "SELECT 1 FROM report_templates WHERE template_id = ?",
                (template_id,),
            ).fetchone()
            if exists:
                raise ValueError("template_id already exists")
            conn.execute(
                """
                INSERT INTO report_templates (template_id, name, description, sections, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    template_id,
                    name,
                    description,
                    json.dumps(sections or [], ensure_ascii=False),
                    now,
                ),
            )
            conn.commit()
        return {
            "template_id": template_id,
            "name": name,
            "description": description,
            "sections": sections or [],
            "created_at": now,
        }

    def update_report_template(
        self, template_id: str, updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT template_id, name, description, sections
                FROM report_templates WHERE template_id = ?
                """,
                (template_id,),
            ).fetchone()
            if not row:
                return None
            name = updates.get("name", row[1])
            description = updates.get("description", row[2])
            sections = updates.get("sections", json.loads(row[3]) if row[3] else [])
            conn.execute(
                """
                UPDATE report_templates
                SET name = ?, description = ?, sections = ?
                WHERE template_id = ?
                """,
                (name, description, json.dumps(sections, ensure_ascii=False), template_id),
            )
            conn.commit()
        return {
            "template_id": template_id,
            "name": name,
            "description": description,
            "sections": sections,
        }

    def delete_report_template(self, template_id: str) -> None:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM report_templates WHERE template_id = ?", (template_id,))
            conn.commit()
