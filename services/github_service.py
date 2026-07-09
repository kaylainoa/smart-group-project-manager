# This file handles GitHub API requests for the project.
#  connect our Flask app to GitHub project data.

import re
import requests
from config import GITHUB_TOKEN


# fallback if no repo has been configured through the UI yet
OWNER = "kaylainoa"
REPO = "smart-group-project-manager"

def get_github_headers():
    """
    Creates headers needed for GitHub API requests.
    The token comes from the .env file through config.py.
    """
    headers = {"Accept": "application/vnd.github+json"}
    # public repos work fine with zero auth - but sending "Bearer None" when
    # GITHUB_TOKEN isn't set gets flat-out rejected by GitHub, so only add it
    # if we actually have one
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


# accepts full GitHub URLs (https://github.com/owner/repo, with or without
# .git/trailing slash), git@ SSH URLs, or plain "owner/repo" shorthand
def parse_repo_url(repo_url):
    repo_url = repo_url.strip()

    match = re.search(r"github\.com[/:]([^/\s]+)/([^/\s]+?)(?:\.git)?/?$", repo_url)
    if match:
        return match.group(1), match.group(2)

    match = re.match(r"^([^/\s]+)/([^/\s]+)$", repo_url)
    if match:
        return match.group(1), match.group(2)

    return None, None


def get_repo_info(owner=OWNER, repo=REPO):
    """

    GitHub API endpoint:
    GET /repos/{owner}/{repo}

    Returns basic repository details that can be displayed
    on the Smart Group Project Manager dashboard.
    """

    # Build the API URL for our repository.
    url = f"https://api.github.com/repos/{owner}/{repo}"

    # Send a GET request to GitHub.
    response = requests.get(url, headers=get_github_headers())

    # If the request failed, return None.
    if response.status_code != 200:
        return None

    # Convert the JSON response into a Python dictionary.
    repo_data = response.json()

    # Return only the information our application needs.
    return {
        "name": repo_data["name"],
        "owner": repo_data["owner"]["login"],
        "description": repo_data["description"],
        "open_issues": repo_data["open_issues_count"],
        "updated_at": repo_data["updated_at"]
    }

def get_recent_commits(owner=OWNER, repo=REPO, limit=5):
    """
    Gets the most recent commits from the GitHub repository.
    """

    url = f"https://api.github.com/repos/{owner}/{repo}/commits"

    response = requests.get(url, headers=get_github_headers(), params={"per_page": limit})

    if response.status_code != 200:
        return []

    commits = response.json()
    recent_commits = []

    for commit in commits[:limit]:
        recent_commits.append({
            "sha": commit["sha"][:7],
            "author": commit["commit"]["author"]["name"],
            "message": commit["commit"]["message"].split("\n")[0],
            "date": commit["commit"]["author"]["date"],
            "url": commit["html_url"]
        })

    return recent_commits


def get_contributors(owner=OWNER, repo=REPO):
    """
    Gets every contributor on the repo and how many commits each has made,
    most active first (that's the order GitHub's API already returns them in).
    """

    url = f"https://api.github.com/repos/{owner}/{repo}/contributors"

    response = requests.get(url, headers=get_github_headers())

    if response.status_code != 200:
        return []

    return [
        {"login": c["login"], "contributions": c["contributions"]}
        for c in response.json()
    ]


# one-stop call for the dashboard/Slack report: takes whatever repo URL the
# team configured, and returns repo info + recent commits + contributors
# together, or None if the URL doesn't parse or the repo can't be reached
def get_project_activity(repo_url, limit=10):
    owner, repo = parse_repo_url(repo_url)
    if owner is None:
        return None

    info = get_repo_info(owner, repo)
    if info is None:
        return None

    return {
        "repo": info,
        "commits": get_recent_commits(owner, repo, limit=limit),
        "contributors": get_contributors(owner, repo)
    }
