import os
import json
import sqlite3
import threading
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from memory.schema import initialize_schema


class AgentMemory:
    """
    Local SQLite and FTS5 memory database for storing, indexing,
    and searching past agent sessions, episodic steps, and outlines.
    """
    _global_lock = threading.RLock()

    def __init__(self, db_path: str = None):
        self.lock = self._global_lock
        if db_path is None:
            # Default to local .agents/memory.db in CWD
            os.makedirs(".agents", exist_ok=True)
            db_path = os.path.join(".agents", "memory.db")
        
        self.db_path = db_path
        with self.lock:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30.0)
            self.conn.row_factory = sqlite3.Row
            try:
                initialize_schema(self.conn)
            except Exception:
                self.conn.rollback()
                raise

    def create_session(self, session_id: str, task_prompt: str):
        """Creates a new session record and indexes the objective."""
        with self.lock:
            try:
                cursor = self.conn.cursor()
                timestamp = datetime.now(timezone.utc).isoformat()
                project_path = os.path.abspath(".")
                
                cursor.execute("""
                    INSERT OR REPLACE INTO sessions (session_id, timestamp, project_path, task_prompt)
                    VALUES (?, ?, ?, ?)
                """, (session_id, timestamp, project_path, task_prompt))
                
                # Index session objective in FTS
                cursor.execute("""
                    INSERT INTO fts_memory (session_id, episode_id, category, content)
                    VALUES (?, NULL, 'task', ?)
                """, (session_id, task_prompt))
                
                self.conn.commit()
            except Exception:
                self.conn.rollback()
                raise

    def add_episode(self, session_id: str, step_number: int, role: str, content: str, tool_calls: List[Dict[str, Any]] = None):
        """Saves a step/interaction and indexes its textual content in FTS."""
        with self.lock:
            try:
                cursor = self.conn.cursor()
                timestamp = datetime.now(timezone.utc).isoformat()
                tool_calls_json = json.dumps(tool_calls) if tool_calls else None
                
                cursor.execute("""
                    INSERT INTO episodes (session_id, step_number, role, content, tool_calls, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (session_id, step_number, role, content, tool_calls_json, timestamp))
                
                episode_id = cursor.lastrowid
                
                # Categorize the entry for filtering
                category = "thought"
                if role == "user":
                    category = "user_input"
                elif role == "tool":
                    category = "tool_output"
                    
                if content:
                    # Index in FTS
                    cursor.execute("""
                        INSERT INTO fts_memory (session_id, episode_id, category, content)
                        VALUES (?, ?, ?, ?)
                    """, (session_id, episode_id, category, content))
                    
                self.conn.commit()
                return episode_id
            except Exception:
                self.conn.rollback()
                raise

    def update_session_results(self, session_id: str, final_summary: str = None, handover_report: str = None):
        """Updates the session with final execution outcomes."""
        with self.lock:
            try:
                cursor = self.conn.cursor()
                if final_summary:
                    cursor.execute("UPDATE sessions SET final_summary = ? WHERE session_id = ?", (final_summary, session_id))
                    cursor.execute("""
                        INSERT INTO fts_memory (session_id, episode_id, category, content)
                        VALUES (?, NULL, 'summary', ?)
                    """, (session_id, final_summary))
                    
                if handover_report:
                    cursor.execute("UPDATE sessions SET handover_report = ? WHERE session_id = ?", (handover_report, session_id))
                    cursor.execute("""
                        INSERT INTO fts_memory (session_id, episode_id, category, content)
                        VALUES (?, NULL, 'handover', ?)
                    """, (session_id, handover_report))
                    
                self.conn.commit()
            except Exception:
                self.conn.rollback()
                raise

    def save_file_outline(self, filename: str, outline: str):
        """Caches a file's structure outline and indexes it."""
        with self.lock:
            try:
                cursor = self.conn.cursor()
                timestamp = datetime.now(timezone.utc).isoformat()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO file_outlines (filename, timestamp, outline)
                    VALUES (?, ?, ?)
                """, (filename, timestamp, outline))
                
                # Index in FTS
                cursor.execute("""
                    INSERT INTO fts_memory (session_id, episode_id, category, content)
                    VALUES ('system', NULL, 'file_outline', ?)
                """, (f"Outline of {filename}:\n{outline}",))
                
                self.conn.commit()
            except Exception:
                self.conn.rollback()
                raise

    def search(
        self, 
        query: str, 
        category: str = None, 
        limit: int = 5, 
        allowed_categories: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Searches the FTS virtual index matching query terms,
        ordered by rank (relevance BM25) and session recency.
        """
        with self.lock:
            cursor = self.conn.cursor()
            
            sql = """
                SELECT 
                    f.category,
                    f.content,
                    s.timestamp as session_timestamp,
                    s.task_prompt,
                    e.step_number,
                    f.session_id,
                    f.episode_id
                FROM fts_memory f
                LEFT JOIN sessions s ON f.session_id = s.session_id
                LEFT JOIN episodes e ON f.episode_id = e.id
                WHERE fts_memory MATCH ?
            """
            params = [query]
            
            if category:
                if allowed_categories is not None and category not in allowed_categories:
                    return []
                sql += " AND f.category = ?"
                params.append(category)
            elif allowed_categories is not None:
                if not allowed_categories:
                    return []
                placeholders = ",".join(["?"] * len(allowed_categories))
                sql += f" AND f.category IN ({placeholders})"
                params.extend(allowed_categories)
                
            # Order by BM25 relevance score and break ties using timestamp DESC
            sql += " ORDER BY rank ASC, s.timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                results.append({
                    "category": row["category"],
                    "content": row["content"],
                    "session_timestamp": row["session_timestamp"],
                    "task_prompt": row["task_prompt"],
                    "step_number": row["step_number"],
                    "session_id": row["session_id"]
                })
            return results

    def close(self):
        """Closes the sqlite database connection safely."""
        with self.lock:
            try:
                self.conn.close()
            except Exception:
                pass
