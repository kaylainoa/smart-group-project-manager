# Smart Group Project Manager

Smart Group Project Manager is a Flask web application that helps student teams organize project progress in one place. The app lets teams track meetings, deadlines, notes, tasks, GitHub commits, AI-generated progress summaries, and Slack updates.

## Project Description

Student project teams often struggle to stay organized because important project information is spread across different places, such as meeting notes, GitHub commits, deadlines, and Slack messages. This makes it harder to know who is responsible for each task, what progress has been made, and what still needs to be completed.

Smart Group Project Manager solves this by giving teams one central dashboard where they can:

- View upcoming Google Calendar meetings and deadlines
- Save meeting notes
- Generate action items from notes
- Track tasks with statuses
- View recent GitHub commits
- Generate progress summaries with Gemini
- Send updates to a Slack channel

## Why We Built This

Group projects can become confusing when communication and progress tracking are scattered across multiple tools. Our app centralizes the most important project information and helps teams quickly create organized progress updates for a manager or instructor.

This improves accountability, saves time, and makes it easier for instructors or managers to understand the team’s current progress.

## Features

### Dashboard

The dashboard acts as the central home page for the project. It displays project information, saved notes, upcoming meetings, deadlines, and links to other pages.

### Google Calendar Integration

The app uses Google Calendar OAuth to let users sign in and choose a calendar. After a calendar is selected, the app pulls upcoming events from that calendar.

Calendar events are separated into:

- Meetings
- Deadlines

Meeting and deadline data is saved in the SQLite database by Google user email and selected calendar ID so different users do not see each other’s calendar data.

### Meetings Page

The Meetings page displays upcoming meetings pulled from Google Calendar. Users can add meeting notes for each meeting.

### Meeting Notes

Users can enter meeting notes either from the dashboard or from the Meetings page. Notes are saved to the SQLite database.

### Task Generation

The app includes a simple action-item generator that scans meeting notes and creates tasks from key phrases such as:

- need to
- must
- fix
- finish
- complete

Generated tasks are saved to the database with a default status of `Not Started`.

### Task Status Tracking

Tasks are stored with a status field. Current task statuses include:

- Not Started
- In Progress
- Done

### Deadlines Page

The Deadlines page displays calendar events that look like project deadlines. The app identifies deadlines using keywords such as:

- deadline
- due

### GitHub Integration

The app connects to the GitHub API and pulls recent commits from the team repository. It retrieves commit information such as:

- Commit message
- Author
- Date

This helps the team track recent code progress.

### Gemini Integration

The app uses Gemini to categorize and summarize project updates. Meeting notes, deadlines, and commit information can be turned into a clean project progress report.

Gemini organizes updates into categories such as:

- Completed
- In Progress
- Blockers

### Slack Integration

The app sends formatted progress reports to a team Slack channel. This allows a manager or instructor to quickly see what the team has completed, what is still in progress, and what blockers exist.

## Tech Stack

- Python
- Flask
- SQLite
- HTML/CSS
- Google Calendar API
- Google OAuth
- GitHub API
- Gemini API
- Slack API
- python-dotenv

## Project Structure

```text
smart-group-project-manager/
│
├── app.py
├── database.py
├── config.py
├── client_info.json
├── requirements.txt
├── smart_group_project_manager.db
│
├── services/
│   ├── calendar_service.py
│   ├── github_service.py
│   ├── gemini_service.py
│   └── slack_service.py
│
├── templates/
│   ├── dashboard.html
│   ├── meetings.html
│   ├── deadlines.html
│   ├── reports.html
│   └── github.html
│
├── static/
│   └── style.css
│
└── tests/
    ├── test_calendar.py
    ├── test_calendar_service.py
    ├── test_meeting_notes.py
    ├── test_tasks.py
    ├── test_slack.py
    └── test_github.py

# Created by  Asyat Sow, Biftu Mohammed, Jakha Cham, & Kayla Inoa
# SEO Tech Developer - Project #2