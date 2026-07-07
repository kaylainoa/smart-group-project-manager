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

