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
            conn.commit()
        self._ensure_agent_category_column()
        self._ensure_skill_columns()

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

    def list_domains(self) -> List[Dict[str, Any]]:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT domain_id, name, description, created_at FROM custom_domains ORDER BY created_at DESC"
            ).fetchall()
        return [
            {
                "domain_id": row[0],
                "name": row[1],
                "description": row[2] or "",
                "created_at": row[3],
            }
            for row in rows
        ]

    def create_domain(self, name: str, description: str = "", domain_id: Optional[str] = None) -> Dict[str, Any]:
        now = int(time.time())
        if not domain_id:
            slug = _slugify(name)
            domain_id = _generate_id(slug or "custom-domain")
        with self._lock, sqlite3.connect(self.db_path) as conn:
            exists = conn.execute(
                "SELECT 1 FROM custom_domains WHERE domain_id = ?",
                (domain_id,),
            ).fetchone()
            if exists:
                raise ValueError("domain_id already exists")
            conn.execute(
                "INSERT INTO custom_domains (domain_id, name, description, created_at) VALUES (?, ?, ?, ?)",
                (domain_id, name, description, now),
            )
            conn.commit()
        return {"domain_id": domain_id, "name": name, "description": description, "created_at": now}

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
