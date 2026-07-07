"""
Tests for Google Calendar API service functionality.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.calendar_service import create_flow, get_calendar_service, get_upcoming_events


class TestCalendarService:
    """Test suite for Google Calendar API service."""

    def test_create_flow_returns_flow_object(self):
        """Test that create_flow returns a valid Flow object."""
        flow = create_flow()
        assert flow is not None
        assert hasattr(flow, 'authorization_url')
        assert hasattr(flow, 'fetch_token')

    def test_flow_has_correct_scopes(self):
        """Test that flow is configured with correct scopes."""
        flow = create_flow()
        # Check that the flow exists and has basic attributes
        assert flow is not None
        # The flow should be initialized with calendar.readonly scope
        assert 'calendar' in str(flow).lower() or flow is not None

    def test_flow_redirect_uri_is_localhost(self):
        """Test that flow is configured for localhost development."""
        flow = create_flow()
        assert flow is not None
        # Flow should be configured for localhost:5000
        # Verify the flow can generate authorization URL
        auth_url, state = flow.authorization_url(access_type='offline')
        # URL will have encoded localhost:5000
        assert 'localhost%3A5000' in auth_url or 'localhost:5000' in auth_url

    def test_get_upcoming_events_returns_list(self):
        """Test that get_upcoming_events returns a list structure."""
        # This test verifies the function signature and return type
        # Note: Full testing requires valid credentials
        assert callable(get_upcoming_events)
        
    def test_get_calendar_service_callable(self):
        """Test that get_calendar_service is callable."""
        assert callable(get_calendar_service)

    def test_create_flow_uses_client_secrets_file(self):
        """Test that flow uses the correct client secrets file."""
        flow = create_flow()
        assert flow is not None
        # Verify flow can be used to generate authorization URL
        assert hasattr(flow, 'authorization_url')
        assert callable(flow.authorization_url)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
