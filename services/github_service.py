# This file handles GitHub API requests for the project.
#  connect our Flask app to GitHub project data.

import requests
from config import GITHUB_TOKEN


OWNER = "kaylainoa"
REPO = "smart-group-project-manager"

def get_github_headers():
    """
    Creates headers needed for GitHub API requests.
    The token comes from the .env file through config.py.
    """
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
