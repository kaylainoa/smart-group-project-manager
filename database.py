# # simple sqlite storage - right now just tracks whether Slack notifications went through
# import sqlite3
# from datetime import datetime, timezone

# DB_PATH = "smart_group_project_manager.db"


# def get_connection():
#     conn = sqlite3.connect(DB_PATH)
#     conn.row_factory = sqlite3.Row
#     return conn


# def init_db():
#     conn = get_connection()
#     conn.execute("""
#         CREATE TABLE IF NOT EXISTS notification_log (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             channel TEXT NOT NULL,
#             message TEXT NOT NULL,
#             success INTEGER NOT NULL,
#             error TEXT,
#             sent_at TEXT NOT NULL
#         )
#     """)
#     conn.execute("""
#         CREATE TABLE IF NOT EXISTS meeting_notes (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             meeting_title TEXT NOT NULL,
#             meeting_time TEXT NOT NULL,
#             notes TEXT NOT NULL,
#             created_at TEXT NOT NULL
#         )
#     """)
#     conn.commit()
#     conn.close()


# def log_notification(channel, message, success, error=None):
#     conn = get_connection()
#     conn.execute(
#         "INSERT INTO notification_log (channel, message, success, error, sent_at) VALUES (?, ?, ?, ?, ?)",
#         (channel, message, int(success), error, datetime.now(timezone.utc).isoformat()),
#     )
#     conn.commit()
#     conn.close()


# def get_notification_logs(limit=20):
#     conn = get_connection()
#     rows = conn.execute(
#         "SELECT * FROM notification_log ORDER BY id DESC LIMIT ?", (limit,)
#     ).fetchall()
#     conn.close()
#     return [dict(row) for row in rows]


# def save_meeting_notes(meeting_title, meeting_time, notes):
#     """Save meeting notes to the database."""
#     conn = get_connection()
#     conn.execute(
#         "INSERT INTO meeting_notes (meeting_title, meeting_time, notes, created_at) VALUES (?, ?, ?, ?)",
#         (meeting_title, meeting_time, notes, datetime.now(timezone.utc).isoformat()),
#     )
#     conn.commit()
#     conn.close()


# def get_meeting_notes(limit=50):
#     """Retrieve all meeting notes from the database."""
#     conn = get_connection()
#     rows = conn.execute(
#         "SELECT * FROM meeting_notes ORDER BY created_at DESC LIMIT ?", (limit,)
#     ).fetchall()
#     conn.close()
#     return [dict(row) for row in rows]


# def get_meeting_note_by_id(note_id):
#     """Retrieve a specific meeting note by ID."""
#     conn = get_connection()
#     row = conn.execute(
#         "SELECT * FROM meeting_notes WHERE id = ?", (note_id,)
#     ).fetchone()
#     conn.close()
#     return dict(row) if row else None
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
        CREATE TABLE IF NOT EXISTS meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            google_event_id TEXT UNIQUE,
            title TEXT NOT NULL,
            start_time TEXT NOT NULL,
            location TEXT,
            description TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS meeting_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_id INTEGER,
            meeting_title TEXT NOT NULL,
            meeting_time TEXT NOT NULL,
            notes TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (meeting_id) REFERENCES meetings(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS deadlines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            google_event_id TEXT UNIQUE,
            title TEXT NOT NULL,
            due_time TEXT NOT NULL,
            description TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            note_id INTEGER,
            task_text TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Not Started',
            created_at TEXT NOT NULL,
            FOREIGN KEY (note_id) REFERENCES meeting_notes(id)
        )
    """)

    conn.commit()
    conn.close()

def generate_tasks_from_notes(notes):
    tasks = []

    sentences = notes.split(".")

    for sentence in sentences:
        sentence = sentence.strip()

        if not sentence:
            continue

        lower = sentence.lower()

        if "need to" in lower or "must" in lower or "fix" in lower or "finish" in lower or "complete" in lower:
            tasks.append(sentence)

    if not tasks:
        tasks.append("Review meeting notes and assign next steps.")

    return tasks

def save_meeting(event):
    conn = get_connection()
    conn.execute("""
        INSERT OR IGNORE INTO meetings
        (google_event_id, title, start_time, location, description)
        VALUES (?, ?, ?, ?, ?)
    """, (
        event["id"],
        event["title"],
        event["start"],
        event.get("location", ""),
        event.get("description", "")
    ))
    conn.commit()
    conn.close()


def get_meetings():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM meetings ORDER BY start_time ASC"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def save_deadline(event):
    conn = get_connection()
    conn.execute("""
        INSERT OR IGNORE INTO deadlines
        (google_event_id, title, due_time, description)
        VALUES (?, ?, ?, ?)
    """, (
        event["id"],
        event["title"],
        event["start"],
        event.get("description", "")
    ))
    conn.commit()
    conn.close()


def get_deadlines():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM deadlines ORDER BY due_time ASC"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def save_meeting_notes(meeting_id, meeting_title, meeting_time, notes):
    conn = get_connection()
    cursor = conn.execute("""
        INSERT INTO meeting_notes
        (meeting_id, meeting_title, meeting_time, notes, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        meeting_id,
        meeting_title,
        meeting_time,
        notes,
        datetime.now(timezone.utc).isoformat()
    ))
    note_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return note_id


def get_meeting_notes():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM meeting_notes ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def save_task(note_id, task_text, status="Not Started"):
    conn = get_connection()
    conn.execute("""
        INSERT INTO tasks (note_id, task_text, status, created_at)
        VALUES (?, ?, ?, ?)
    """, (
        note_id,
        task_text,
        status,
        datetime.now(timezone.utc).isoformat()
    ))
    conn.commit()
    conn.close()


def get_tasks():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM tasks ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


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