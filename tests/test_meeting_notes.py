"""
Tests for meeting notes functionality.
"""
import pytest
import os
import sqlite3
from datetime import datetime, timezone

# Import the functions we want to test
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import database


@pytest.fixture
def test_db():
    """Create a test database for each test."""
    # Use a temporary test database
    test_db_path = "test_smart_group_project_manager.db"
    database.DB_PATH = test_db_path
    
    # Initialize the database
    database.init_db()
    
    yield
    
    # Clean up after test
    if os.path.exists(test_db_path):
        os.remove(test_db_path)


class TestMeetingNotes:
    """Test suite for meeting notes functionality."""

    def test_save_meeting_notes(self, test_db):
        """Test saving meeting notes to the database."""
        meeting_title = "Q3 Planning Meeting"
        meeting_time = "2026-07-15T10:00:00"
        notes = "Discussed roadmap for next quarter. Agreed on priorities."
        
        # Save the notes
        database.save_meeting_notes(meeting_title, meeting_time, notes)
        
        # Verify the notes were saved
        saved_notes = database.get_meeting_notes()
        assert len(saved_notes) == 1
        assert saved_notes[0]["meeting_title"] == meeting_title
        assert saved_notes[0]["meeting_time"] == meeting_time
        assert saved_notes[0]["notes"] == notes

    def test_save_multiple_meeting_notes(self, test_db):
        """Test saving multiple meeting notes."""
        notes_data = [
            ("Meeting 1", "2026-07-15T10:00:00", "First meeting notes"),
            ("Meeting 2", "2026-07-16T14:00:00", "Second meeting notes"),
            ("Meeting 3", "2026-07-17T09:30:00", "Third meeting notes"),
        ]
        
        # Save multiple notes
        for title, time, notes in notes_data:
            database.save_meeting_notes(title, time, notes)
        
        # Verify all notes were saved
        saved_notes = database.get_meeting_notes()
        assert len(saved_notes) == 3

    def test_get_meeting_notes_ordered_by_date(self, test_db):
        """Test that meeting notes are retrieved in reverse chronological order."""
        database.save_meeting_notes("Old Meeting", "2026-07-10T10:00:00", "Old notes")
        database.save_meeting_notes("New Meeting", "2026-07-20T10:00:00", "New notes")
        
        notes = database.get_meeting_notes()
        assert len(notes) == 2
        # Most recent should be first
        assert notes[0]["meeting_title"] == "New Meeting"
        assert notes[1]["meeting_title"] == "Old Meeting"

    def test_get_meeting_note_by_id(self, test_db):
        """Test retrieving a specific meeting note by ID."""
        database.save_meeting_notes("Test Meeting", "2026-07-15T10:00:00", "Test notes")
        
        # Get all notes to find the ID
        all_notes = database.get_meeting_notes()
        note_id = all_notes[0]["id"]
        
        # Retrieve by ID
        note = database.get_meeting_note_by_id(note_id)
        assert note is not None
        assert note["meeting_title"] == "Test Meeting"
        assert note["notes"] == "Test notes"

    def test_get_meeting_note_by_id_not_found(self, test_db):
        """Test retrieving a non-existent note returns None."""
        note = database.get_meeting_note_by_id(999)
        assert note is None

    def test_meeting_notes_have_timestamp(self, test_db):
        """Test that saved meeting notes have a created_at timestamp."""
        database.save_meeting_notes("Timestamped Meeting", "2026-07-15T10:00:00", "With timestamp")
        
        notes = database.get_meeting_notes()
        assert len(notes) == 1
        assert notes[0]["created_at"] is not None
        # Verify timestamp is in ISO format
        assert "T" in notes[0]["created_at"]

    def test_get_meeting_notes_limit(self, test_db):
        """Test that get_meeting_notes respects the limit parameter."""
        # Save 5 notes
        for i in range(5):
            database.save_meeting_notes(f"Meeting {i}", f"2026-07-{15+i}T10:00:00", f"Notes {i}")
        
        # Get with limit of 2
        notes = database.get_meeting_notes(limit=2)
        assert len(notes) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
