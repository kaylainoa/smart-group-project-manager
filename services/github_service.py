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

def get_repo_info():
    """

    GitHub API endpoint:
    GET /repos/{owner}/{repo}

    Returns basic repository details that can be displayed
    on the Smart Group Project Manager dashboard.
    """

    # Build the API URL for our repository.
    url = f"https://api.github.com/repos/{OWNER}/{REPO}"

    # Send a GET request to GitHub.
    response = requests.get(url, headers=get_github_headers())
    print("Status Code:", response.status_code)

    # If the request failed, return None.
    if response.status_code != 200:
        print("Response:", response.text)
        return None

    # Convert the JSON response into a Python dictionary.
    repo = response.json()

    # Return only the information our application needs.
    return {
        "name": repo["name"],
        "owner": repo["owner"]["login"],
        "description": repo["description"],
        "open_issues": repo["open_issues_count"],
        "updated_at": repo["updated_at"]
    }

