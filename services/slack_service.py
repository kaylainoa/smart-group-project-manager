# formats a progress report and posts it to the team's private Slack channel
import ssl

import certifi
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

import config
import database

# macOS's python.org builds don't ship with system CA certs wired up, which makes
# HTTPS calls fail with CERTIFICATE_VERIFY_FAILED - point at certifi's bundle instead
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


def format_progress_report(report):
    lines = [f"*Progress Report — {report.get('team_name', 'Team')}*"]

    if report.get("period"):
        lines.append(f"_Period: {report['period']}_")

    def add_section(title, items):
        if not items:
            return
        lines.append(f"\n*{title}:*")
        for item in items:
            lines.append(f"• {item}")

    add_section("Completed", report.get("completed"))
    add_section("In Progress", report.get("in_progress"))
    add_section("Blockers", report.get("blockers"))

    return "\n".join(lines)


def send_progress_report(report, channel=None):
    channel = channel or config.SLACK_CHANNEL_ID
    message = format_progress_report(report)

    client = WebClient(token=config.SLACK_BOT_TOKEN, ssl=SSL_CONTEXT)

    try:
        client.chat_postMessage(channel=channel, text=message)
        database.log_notification(channel, message, success=True)
        return True, None
    except SlackApiError as e:
        error = e.response.get("error", str(e))
        database.log_notification(channel, message, success=False, error=error)
        return False, error
