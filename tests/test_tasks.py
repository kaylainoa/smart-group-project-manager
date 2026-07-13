# this is the test case for the gemini API
import unittest
from unittest.mock import patch, MagicMock
# Swap 'gemini_service' if your file uses a different name
from gemini_service import project_summary, categorize_update, _parse_categorized_response

class GeminiServiceTestCase(unittest.TestCase):

    @patch('google.genai.Client')
    def test_project_summary_success(self, mock_client_class):
        # Fake out the Gemini API response structure
        mock_client_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "*Focus Areas*\n- **Task 1** completed successfully."
        
        mock_client_instance.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client_instance

        # Run the summarizer with dummy data
        result = project_summary("Notes here", ["commit 1"], ["Deadline Friday"])

        # Make sure the clean summary structure is intact
        self.assertIn("*Focus Areas*", result)
        self.assertIn("Task 1", result)
        mock_client_instance.models.generate_content.assert_called_once()

    @patch('google.genai.Client')
    def test_project_summary_fallback_on_exception(self, mock_client_class):
        # Force the Gemini API to drop connection or throw a quota error
        mock_client_instance = MagicMock()
        mock_client_instance.models.generate_content.side_effect = Exception("Quota Exceeded")
        mock_client_class.return_value = mock_client_instance

        result = project_summary("Fix bug", ["commit A"], ["Due tonight"])

        # Verify our backup safety net takes over instead of breaking the app
        self.assertIn("Gemini was temporarily unavailable", result)
        self.assertIn("Fix bug", result)

    @patch('google.genai.Client')
    def test_categorize_update_success(self, mock_client_class):
        mock_client_instance = MagicMock()
        mock_response = MagicMock()
        
        # Give the mock exactly what the prompt asks Gemini to return
        mock_response.text = """
        COMPLETED:
        - Setup GitHub
        - Created layout

        IN PROGRESS:
        - Working on DB

        BLOCKERS:
        - None
        """
        mock_client_instance.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client_instance

        result = categorize_update("Notes", ["Commits"], ["Deadlines"])

        # Check that the raw text got parsed into a clean python dictionary
        self.assertEqual(result["completed"], ["Setup GitHub", "Created layout"])
        self.assertEqual(result["in_progress"], ["Working on DB"])
        self.assertEqual(result["blockers"], [])  # '- None' should be cleaned out completely

    def test_parse_categorized_response_helper(self):
        # Test the string-splitting loop directly without calling the API
        raw_ai_text = "COMPLETED:\n- Task A\nIN PROGRESS:\n- Task B\nBLOCKERS:\n- Problem C"
        
        parsed = _parse_categorized_response(raw_ai_text)
        
        self.assertEqual(parsed["completed"], ["Task A"])
        self.assertEqual(parsed["in_progress"], ["Task B"])
        self.assertEqual(parsed["blockers"], ["Problem C"])

if __name__ == '__main__':
    unittest.main()