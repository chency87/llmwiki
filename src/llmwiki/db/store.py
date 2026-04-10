import sqlite3
import os
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional

class Store:
    _thread_local = threading.local()

    def __init__(self, vault_path: str = "vault"):
        self.vault_path = os.path.abspath(vault_path)
        self.db_path = os.path.join(self.vault_path, ".llmwiki", "llmwiki.db")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Returns a thread-local SQLite connection."""
        if not hasattr(self._thread_local, "connections"):
            self._thread_local.connections = {}
        
        if self.db_path not in self._thread_local.connections:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=-2000")
            self._thread_local.connections[self.db_path] = conn
            
        return self._thread_local.connections[self.db_path]

    def _init_db(self):
        conn = self._get_conn()
        with conn:
            # Manifest table
            conn.execute("CREATE TABLE IF NOT EXISTS manifest (filename TEXT PRIMARY KEY, hash TEXT NOT NULL, status TEXT NOT NULL, processed_at TEXT)")
            
            # Entities table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS entities (
                    name TEXT PRIMARY KEY, 
                    path TEXT NOT NULL, 
                    summary TEXT NOT NULL, 
                    categories TEXT,
                    tags TEXT,
                    updated_at TEXT
                )
            """)
            
            # Links table with weights
            conn.execute("""
                CREATE TABLE IF NOT EXISTS links (
                    source TEXT, 
                    target TEXT, 
                    weight REAL DEFAULT 1.0,
                    type TEXT DEFAULT 'related',
                    PRIMARY KEY (source, target)
                )
            """)
            
            # Migration for existing links table
            try:
                conn.execute("ALTER TABLE links ADD COLUMN weight REAL DEFAULT 1.0")
                conn.execute("ALTER TABLE links ADD COLUMN type TEXT DEFAULT 'related'")
            except sqlite3.OperationalError:
                pass

            try:
                conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS entities_fts USING fts5(name, summary, categories, tags, content='entities', content_rowid='rowid')")
            except: pass
            
            conn.execute("CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL, trace_id TEXT, task_type TEXT NOT NULL, category TEXT NOT NULL, level TEXT NOT NULL, message TEXT NOT NULL)")
            conn.execute("CREATE TABLE IF NOT EXISTS sessions (agent_id TEXT PRIMARY KEY, session_key TEXT NOT NULL, last_updated TEXT NOT NULL)")
            conn.execute("CREATE TABLE IF NOT EXISTS heartbeat (service_name TEXT PRIMARY KEY, last_seen TEXT NOT NULL, status TEXT NOT NULL)")

    def set_heartbeat(self, service_name: str, status: str = "running"):
        now = datetime.now().isoformat()
        conn = self._get_conn()
        with conn:
            conn.execute("INSERT OR REPLACE INTO heartbeat (service_name, last_seen, status) VALUES (?, ?, ?)", (service_name, now, status))

    def mark_status(self, filename: str, file_hash: str, status: str):
        now = datetime.now().isoformat()
        conn = self._get_conn()
        with conn:
            conn.execute("INSERT OR REPLACE INTO manifest (filename, hash, status, processed_at) VALUES (?, ?, ?, ?)", (filename, file_hash, status, now))

    def try_acquire_lock(self, filename: str, file_hash: str) -> bool:
        now = datetime.now().isoformat()
        conn = self._get_conn()
        with conn:
            cur = conn.execute("SELECT status FROM manifest WHERE filename = ? AND hash = ?", (filename, file_hash))
            row = cur.fetchone()
            if row:
                if row[0] == "PROCESSED" or row[0] == "PROCESSING":
                    return False
            
            res = conn.execute("""
                INSERT INTO manifest (filename, hash, status, processed_at) 
                VALUES (?, ?, 'PROCESSING', ?)
                ON CONFLICT(filename) DO UPDATE SET 
                    status = 'PROCESSING', 
                    hash = excluded.hash,
                    processed_at = excluded.processed_at
                WHERE status IN ('PENDING', 'ERROR') OR hash != excluded.hash
            """, (filename, file_hash, now))
            
            return res.rowcount > 0

    def mark_processed(self, filename: str, file_hash: str):
        self.mark_status(filename, file_hash, "PROCESSED")

    def mark_error(self, filename: str, file_hash: str):
        self.mark_status(filename, file_hash, "ERROR")

    def is_processed(self, filename: str, file_hash: str) -> bool:
        conn = self._get_conn()
        cur = conn.execute("SELECT hash, status FROM manifest WHERE filename = ?", (filename,))
        row = cur.fetchone()
        return row and row[0] == file_hash and row[1] == "PROCESSED"

    def get_manifest_stats(self) -> Dict[str, int]:
        conn = self._get_conn()
        cur = conn.execute("SELECT status, COUNT(*) FROM manifest GROUP BY status")
        return {row[0]: row[1] for row in cur.fetchall()}

    def update_entity(self, name: str, path: str, summary: str, categories: str = "", tags: str = ""):
        now = datetime.now().isoformat()
        conn = self._get_conn()
        with conn:
            conn.execute("""
                INSERT OR REPLACE INTO entities (name, path, summary, categories, tags, updated_at) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, path, summary, categories, tags, now))

    def get_entity_count(self) -> int:
        conn = self._get_conn()
        cur = conn.execute("SELECT COUNT(*) FROM entities")
        return cur.fetchone()[0]

    def get_knowledge_map(self) -> Dict[str, Any]:
        conn = self._get_conn()
        cur = conn.execute("SELECT name, path, summary, categories, tags FROM entities")
        return {row[0]: {"path": row[1], "summary": row[2], "categories": row[3], "tags": row[4]} for row in cur.fetchall()}

    def search_entities_keyword(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        results = []
        try:
            cur = conn.execute("SELECT name, path, summary FROM entities_fts WHERE entities_fts MATCH ? ORDER BY rank LIMIT ?", (query, limit))
            results = [{"name": r[0], "path": r[1], "summary": r[2]} for r in cur.fetchall()]
        except: pass
        if not results:
            words = query.split()
            for word in words:
                if len(word) < 3: continue
                cur = conn.execute("SELECT name, path, summary FROM entities WHERE name LIKE ? OR summary LIKE ? OR categories LIKE ? OR tags LIKE ? LIMIT ?", (f"%{word}%", f"%{word}%", f"%{word}%", f"%{word}%", limit))
                for r in cur.fetchall():
                    if r[0] not in [res["name"] for res in results]:
                        results.append({"name": r[0], "path": r[1], "summary": r[2]})
        return results[:limit]

    def add_link(self, source: str, target: str, weight: float = 1.0, link_type: str = "related"):
        conn = self._get_conn()
        with conn:
            conn.execute("""
                INSERT INTO links (source, target, weight, type) 
                VALUES (?, ?, ?, ?)
                ON CONFLICT(source, target) DO UPDATE SET 
                    weight = excluded.weight,
                    type = excluded.type
            """, (source, target, weight, link_type))

    def get_backlinks(self, target: str) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        cur = conn.execute("SELECT source, weight, type FROM links WHERE target = ?", (target,))
        return [{"source": row[0], "weight": row[1], "type": row[2]} for row in cur.fetchall()]

    def add_log(self, category: str, level: str, message: str, trace_id: str = None, task_type: str = "UNKNOWN"):
        now = datetime.now().isoformat()
        conn = self._get_conn()
        with conn:
            conn.execute("INSERT INTO logs (timestamp, category, level, message, trace_id, task_type) VALUES (?, ?, ?, ?, ?, ?)", (now, category, level, message, trace_id, task_type))

    def get_paginated_traces(self, page: int = 1, limit: int = 10) -> List[Dict[str, Any]]:
        offset = (page - 1) * limit
        conn = self._get_conn()
        cur = conn.execute("SELECT trace_id, task_type, MIN(timestamp), MAX(timestamp) FROM logs GROUP BY trace_id ORDER BY MAX(id) DESC LIMIT ? OFFSET ?", (limit, offset))
        traces = []
        for row in cur.fetchall():
            tid = row[0] or "no-trace"
            trace_info = {"trace_id": tid, "task_type": row[1], "start_time": row[2], "end_time": row[3], "logs": []}
            log_cur = conn.execute("SELECT timestamp, category, level, message FROM logs WHERE (trace_id = ? OR (? = 'no-trace' AND trace_id IS NULL)) ORDER BY id ASC", (row[0], tid))
            trace_info["logs"] = [{"timestamp": lr[0], "category": lr[1], "level": lr[2], "message": lr[3]} for lr in log_cur.fetchall()]
            traces.append(trace_info)
        return traces

    def get_trace_count(self) -> int:
        conn = self._get_conn()
        cur = conn.execute("SELECT COUNT(DISTINCT trace_id) FROM logs")
        return cur.fetchone()[0]

    def get_session(self, agent_id: str) -> Optional[str]:
        conn = self._get_conn()
        cur = conn.execute("SELECT session_key FROM sessions WHERE agent_id = ?", (agent_id,))
        row = cur.fetchone()
        return row[0] if row else None

    def save_session(self, agent_id: str, session_key: str):
        now = datetime.now().isoformat()
        conn = self._get_conn()
        with conn:
            conn.execute("INSERT OR REPLACE INTO sessions (agent_id, session_key, last_updated) VALUES (?, ?, ?)", (agent_id, session_key, now))
