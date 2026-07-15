import sqlite3

CREATE_SESSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    project_path TEXT NOT NULL,
    task_prompt TEXT NOT NULL,
    final_summary TEXT,
    handover_report TEXT
)
"""

CREATE_EPISODES_TABLE = """
CREATE TABLE IF NOT EXISTS episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    step_number INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT,
    tool_calls TEXT,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions (session_id) ON DELETE CASCADE
)
"""

CREATE_FILE_OUTLINES_TABLE = """
CREATE TABLE IF NOT EXISTS file_outlines (
    filename TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    outline TEXT NOT NULL
)
"""

CREATE_FTS5_TABLE = """
CREATE VIRTUAL TABLE IF NOT EXISTS fts_memory USING fts5(
    session_id UNINDEXED,
    episode_id UNINDEXED,
    category,
    content,
    tokenize='porter'
)
"""

CREATE_FTS4_TABLE = """
CREATE VIRTUAL TABLE IF NOT EXISTS fts_memory USING fts4(
    session_id,
    episode_id,
    category,
    content,
    tokenize=porter
)
"""

def initialize_schema(conn: sqlite3.Connection):
    """Sets up the SQLite database schema and foreign keys."""
    cursor = conn.cursor()
    
    # Enable Foreign Keys support and WAL mode
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA synchronous = NORMAL;")
    
    # Create main tables
    cursor.execute(CREATE_SESSIONS_TABLE)
    cursor.execute(CREATE_EPISODES_TABLE)
    cursor.execute(CREATE_FILE_OUTLINES_TABLE)
    
    # Create full-text virtual search table
    try:
        cursor.execute(CREATE_FTS5_TABLE)
    except sqlite3.OperationalError:
        # Fallback to FTS4 if FTS5 is not available
        cursor.execute(CREATE_FTS4_TABLE)
        
    conn.commit()
