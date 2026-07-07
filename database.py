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
    conn.execute("""
        CREATE TABLE IF NOT EXISTS meeting_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_title TEXT NOT NULL,
            meeting_time TEXT NOT NULL,
            notes TEXT NOT NULL,
            created_at TEXT NOT NULL
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


def save_meeting_notes(meeting_title, meeting_time, notes):
    """Save meeting notes to the database."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO meeting_notes (meeting_title, meeting_time, notes, created_at) VALUES (?, ?, ?, ?)",
        (meeting_title, meeting_time, notes, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()


def get_meeting_notes(limit=50):
    """Retrieve all meeting notes from the database."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM meeting_notes ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_meeting_note_by_id(note_id):
    """Retrieve a specific meeting note by ID."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM meeting_notes WHERE id = ?", (note_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None
