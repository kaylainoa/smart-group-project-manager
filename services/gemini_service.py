import os
from google import genai
from google.genai import types

def project_summary(meeting_notes, commits, deadlines):
    """ Summarizes raw team data into a clean, highlighted update for Slack """
    client = genai.Client()
    
    raw_data = f"""
    Meeting notes to review: {meeting_notes}
    Recent GitHub activity: {commits}
    Upcoming deadlines: {deadlines}
    """
    
    # Writing the prompt like a standard, professional instruction note
    system_prompt = """
    Please take these raw meeting notes, commits, and deadlines and organize them into a clean project update for Slack.  Keep the tone completely professional and do not use any emojis. Start the message with a section called *Focus Areas* and use bolding to highlight the most important takeaways, risks, or urgent items right away. Underneath that, use standard bullet points to break down the general progress and next steps. Make sure to use Slack's markdown style, like asterisks for bolding.
    """
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=raw_data,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.3
        )
    )

    return response.text


def categorize_update(meeting_notes, commits, deadlines):
    """ Sorts raw team data into Completed / In Progress / Blockers for the Slack report """
    client = genai.Client()

    raw_data = f"""
    Meeting notes to review: {meeting_notes}
    Recent GitHub activity: {commits}
    Upcoming deadlines: {deadlines}
    """

    system_prompt = """
    Sort the information below into three categories: Completed, In Progress, and Blockers.
    Keep the tone professional and do not use emojis. Respond in EXACTLY this format, with
    no extra commentary before or after it:

    COMPLETED:
    - item
    - item

    IN PROGRESS:
    - item

    BLOCKERS:
    - item

    If a category has nothing to put in it, write "- None" under that heading instead of
    leaving it empty.
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=raw_data,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.3
            )
        )
    except Exception as e:
        print("Gemini categorization failed:", e)

        return {
            "completed": [],
            "in_progress": [meeting_notes] if meeting_notes else [],
            "blockers": [
                "Gemini was temporarily unavailable, so this update was not AI-categorized."
            ]
        }


# turns Gemini's "COMPLETED:\n- foo\n- bar" style reply into
# {"completed": ["foo", "bar"], "in_progress": [...], "blockers": [...]}
def _parse_categorized_response(text):
    sections = {"completed": [], "in_progress": [], "blockers": []}
    headers = {
        "completed:": "completed",
        "in progress:": "in_progress",
        "blockers:": "blockers",
    }
    current = None

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.lower() in headers:
            current = headers[stripped.lower()]
            continue
        if current and stripped.startswith("-"):
            item = stripped.lstrip("-").strip()
            if item and item.lower() != "none":
                sections[current].append(item)

    return sections

