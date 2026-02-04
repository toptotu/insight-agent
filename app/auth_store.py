import hashlib
import hmac
import os
import secrets
import sqlite3
import threading
import time
from typing import Any, Dict, Optional


class AuthStore:
    def __init__(self, base_dir: str) -> None:
        self.base_dir = base_dir
        self.db_path = os.path.join(base_dir, "data", "store.db")
        self._lock = threading.Lock()
        self._ensure_db()
        self._ensure_default_user()

    def _ensure_db(self) -> None:
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    must_change_password INTEGER NOT NULL,
                    created_at INTEGER NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL
                )
                """
            )
            conn.commit()

    def _ensure_default_user(self) -> None:
        username = os.getenv("AUTH_USERNAME", "admin").strip()
        password = os.getenv("AUTH_PASSWORD", "admin123").strip()
        if not username or not password:
            return
        with self._lock, sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT username FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            if row:
                return
            password_hash = self._hash_password(password)
            conn.execute(
                """
                INSERT INTO users (username, password_hash, must_change_password, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (username, password_hash, 1, int(time.time())),
            )
            conn.commit()

    def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        user = self.get_user(username)
        if not user:
            return None
        if not self._verify_password(password, user["password_hash"]):
            return None
        return user

    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT username, password_hash, must_change_password FROM users WHERE username = ?",
                (username,),
            ).fetchone()
        if not row:
            return None
        return {
            "username": row[0],
            "password_hash": row[1],
            "must_change_password": bool(row[2]),
        }

    def update_password(self, username: str, new_password: str) -> bool:
        password_hash = self._hash_password(new_password)
        with self._lock, sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT username FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            if not row:
                return False
            conn.execute(
                """
                UPDATE users
                SET password_hash = ?, must_change_password = 0
                WHERE username = ?
                """,
                (password_hash, username),
            )
            conn.commit()
        return True

    def create_session(self, username: str) -> Dict[str, Any]:
        session_id = secrets.token_urlsafe(32)
        now = int(time.time())
        ttl = int(os.getenv("AUTH_SESSION_TTL", "28800"))
        expires_at = now + ttl
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO sessions (session_id, username, created_at, expires_at)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, username, now, expires_at),
            )
            conn.commit()
        return {"session_id": session_id, "username": username, "expires_at": expires_at}

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        if not session_id:
            return None
        with self._lock, sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT session_id, username, expires_at
                FROM sessions
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
        if not row:
            return None
        if int(time.time()) > row[2]:
            self.delete_session(session_id)
            return None
        return {"session_id": row[0], "username": row[1], "expires_at": row[2]}

    def delete_session(self, session_id: str) -> None:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            conn.commit()

    def _hash_password(self, password: str) -> str:
        iterations = 120000
        salt = secrets.token_bytes(16)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return f"pbkdf2${iterations}${salt.hex()}${dk.hex()}"

    def _verify_password(self, password: str, hashed: str) -> bool:
        try:
            algo, iterations_str, salt_hex, hash_hex = hashed.split("$")
            if algo != "pbkdf2":
                return False
            iterations = int(iterations_str)
            salt = bytes.fromhex(salt_hex)
            expected = bytes.fromhex(hash_hex)
            dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
            return hmac.compare_digest(dk, expected)
        except Exception:
            return False
