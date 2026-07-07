# simple sqlite storage - right now just tracks whether Slack notifications went through
import sqlite3
from datetime import datetime, timezone

DB_PATH = "smart_group_project_manager.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notification_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel TEXT NOT NULL,
            message TEXT NOT NULL,
            success INTEGER NOT NULL,
            error TEXT,
            sent_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def log_notification(channel, message, success, error=None):
    conn = get_connection()
    conn.execute(
        "INSERT INTO notification_log (channel, message, success, error, sent_at) VALUES (?, ?, ?, ?, ?)",
        (channel, message, int(success), error, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()


def get_notification_logs(limit=20):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM notification_log ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]
