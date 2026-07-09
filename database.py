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


# small helper so we can safely add a new column to a table that already exists
# and already has data in it, without wiping anything out
def _add_column_if_missing(conn, table, column, coltype):
    existing = [row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")


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

    # a prior version of this table allowed multiple calendars per user (composite
    # primary key); drop and recreate to enforce exactly one, permanent, per user
    pk_columns = [
        row[1] for row in conn.execute("PRAGMA table_info(user_calendar_selection)").fetchall()
        if row[5] > 0
    ]
    if pk_columns and pk_columns != ["user_email"]:
        conn.execute("DROP TABLE user_calendar_selection")

    # remembers which Google Calendar each teammate picked on their first login,
    # so we know where to pull their events from every time after that
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_calendar_selection (
            user_email TEXT PRIMARY KEY,
            calendar_id TEXT NOT NULL,
            calendar_name TEXT
        )
    """)

    # replaced by per-note sending (each note now gets its own Send button
    # instead of one shared pending summary) - drop the old singleton table
    conn.execute("DROP TABLE IF EXISTS pending_slack_summary")

    # project-wide settings (not per-user, unlike calendar selection) - right
    # now just holds which GitHub repo the dashboard/Slack reports pull from
    conn.execute("""
        CREATE TABLE IF NOT EXISTS project_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            github_repo_url TEXT
        )
    """)

    # these two columns got added after meetings/deadlines already existed, so we
    # tack them on with ALTER TABLE instead of recreating (keeps existing rows around)
    # - user_email: whose meeting/deadline this is, so people don't see each other's
    # - calendar_id: which of that user's calendars it came from
    _add_column_if_missing(conn, "meetings", "user_email", "TEXT")
    _add_column_if_missing(conn, "meetings", "calendar_id", "TEXT")
    _add_column_if_missing(conn, "deadlines", "user_email", "TEXT")
    _add_column_if_missing(conn, "deadlines", "calendar_id", "TEXT")
    # this db file predates meeting_id being added to meeting_notes
    _add_column_if_missing(conn, "meeting_notes", "meeting_id", "INTEGER")
    # tracks when a note's update was posted to Slack, so its card can show
    # "Sent" instead of the button once that's happened
    _add_column_if_missing(conn, "meeting_notes", "sent_at", "TEXT")
    # so the dashboard can show a time range ("11am-2pm") instead of just a start time
    _add_column_if_missing(conn, "meetings", "end_time", "TEXT")

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

# saves one calendar event as a meeting. "OR IGNORE" means if we've already saved
# this exact event before (same google_event_id), it just skips it instead of erroring
def save_meeting(event, user_email, calendar_id):
    conn = get_connection()
    conn.execute("""
        INSERT OR IGNORE INTO meetings
        (google_event_id, title, start_time, end_time, location, description, user_email, calendar_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        event["id"],
        event["title"],
        event["start"],
        event.get("end"),
        event.get("location", ""),
        event.get("description", ""),
        user_email,
        calendar_id
    ))
    conn.commit()
    conn.close()


# only pulls back meetings that belong to this specific user + calendar, so
# teammates never see each other's stuff on the dashboard
def get_meetings(user_email, calendar_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM meetings WHERE user_email = ? AND calendar_id = ? ORDER BY start_time ASC",
        (user_email, calendar_id)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


# same idea as save_meeting, just for the deadline-flagged events
def save_deadline(event, user_email, calendar_id):
    conn = get_connection()
    conn.execute("""
        INSERT OR IGNORE INTO deadlines
        (google_event_id, title, due_time, description, user_email, calendar_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        event["id"],
        event["title"],
        event["start"],
        event.get("description", ""),
        user_email,
        calendar_id
    ))
    conn.commit()
    conn.close()


def get_deadlines(user_email, calendar_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM deadlines WHERE user_email = ? AND calendar_id = ? ORDER BY due_time ASC",
        (user_email, calendar_id)
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


# just the notes from the dashboard's "Enter Notes" box (meeting_id is NULL),
# not the ones tied to a specific meeting on /meetings - shown as cards on
# the dashboard's "Saved Notes" column
def get_general_notes():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM meeting_notes WHERE meeting_id IS NULL ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_note_by_id(note_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM meeting_notes WHERE id = ?", (note_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def mark_note_sent(note_id):
    conn = get_connection()
    conn.execute(
        "UPDATE meeting_notes SET sent_at = ? WHERE id = ?",
        (datetime.now(timezone.utc).isoformat(), note_id)
    )
    conn.commit()
    conn.close()


# wipes every card in the dashboard's "Saved Notes" column (general notes only,
# not meeting-specific ones) along with any tasks generated from them
def clear_general_notes():
    conn = get_connection()
    note_ids = [
        row["id"] for row in
        conn.execute("SELECT id FROM meeting_notes WHERE meeting_id IS NULL").fetchall()
    ]
    if note_ids:
        placeholders = ",".join("?" for _ in note_ids)
        conn.execute(f"DELETE FROM tasks WHERE note_id IN ({placeholders})", note_ids)
        conn.execute(f"DELETE FROM meeting_notes WHERE id IN ({placeholders})", note_ids)
    conn.commit()
    conn.close()


# unlike calendar selection, this can be changed anytime - it's a project-wide
# setting, not tied to any one person's identity/permissions
def save_github_repo_url(repo_url):
    conn = get_connection()
    conn.execute("""
        INSERT INTO project_settings (id, github_repo_url) VALUES (1, ?)
        ON CONFLICT(id) DO UPDATE SET github_repo_url = excluded.github_repo_url
    """, (repo_url,))
    conn.commit()
    conn.close()


def get_github_repo_url():
    conn = get_connection()
    row = conn.execute("SELECT github_repo_url FROM project_settings WHERE id = 1").fetchone()
    conn.close()
    return row["github_repo_url"] if row else None


# locks in which calendar this user wants to use. "DO NOTHING" on conflict means
# if they somehow submit the picker form twice, the second one is just ignored -
# once you've picked a calendar it's permanent
def save_calendar_selection(user_email, calendar_id, calendar_name):
    conn = get_connection()
    conn.execute("""
        INSERT INTO user_calendar_selection (user_email, calendar_id, calendar_name)
        VALUES (?, ?, ?)
        ON CONFLICT(user_email) DO NOTHING
    """, (user_email, calendar_id, calendar_name))
    conn.commit()
    conn.close()


# returns None if this user hasn't picked a calendar yet - that's how app.py
# knows whether to show them the picker or the actual dashboard
def get_calendar_selection(user_email):
    conn = get_connection()
    row = conn.execute(
        "SELECT calendar_id, calendar_name FROM user_calendar_selection WHERE user_email = ?",
        (user_email,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None



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