import os
import os.path
import smtplib
from h11 import Request
import requests
import sys
from email.mime.text import MIMEText
from dotenv import load_dotenv
from datetime import datetime
from openai import OpenAI
from mcp.server.fastmcp import FastMCP

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Tells where our tells the script exactly where it lives on our computer
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_PATH = os.path.join(BASE_DIR, 'token.json')
CREDS_PATH = os.path.join(BASE_DIR, 'credentials.json')

# Setting up Google Calendar API and Google Gmail API credentials
SERVICE_ACCOUNT_FILE = 'credentials.json'
# Define the scopes for Google Calendar API and Gmail API
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly', 'https://www.googleapis.com/auth/gmail.send']

# Initialize services
# Define MCP tools
# System Instruction for the AI model
SYSTEM_PROMPT = ""

def get_system_prompt() -> str:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    PROMPT_PATH = os.path.join(BASE_DIR, "system_prompt.txt")
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        SYSTEM_PROMPT = f.read()
    return SYSTEM_PROMPT

# Create an MCP server
mcp = FastMCP(
    name="Morning Briefing AI Agent",
    instructions=get_system_prompt(),
)

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

@mcp.tool()
def get_calendar_events():
    creds = None
    # Check if the token already exists using the exact path
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        
    # If there are no valid credentials, trigger the browser login
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(GoogleRequest())
        else:
            # Use the exact path to the credentials file
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
            
        # Save the new token using the exact path
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())
            
    service = build('calendar', 'v3', credentials=creds, cache_discovery=False)

    # Get the current time in the exact format Google requires
    now = datetime.utcnow().isoformat() + 'Z'
    
    # Fetch the events, using timeMin to only get events from right now onward
    events = service.events().list(
        calendarId='primary', 
        timeMin=now,
        maxResults=10, 
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    return events.get("items", [])

# Load environment variables from .env file
load_dotenv()

# Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')
RECIPIENT_EMAIL = os.getenv('RECIPIENT_EMAIL')
LOCATION = "Madison, Wisconsin"
TIMEZONE = "America/Chicago"

MODEL_NAME = "gpt-4.1"

model = OpenAI(
    api_key=OPENAI_API_KEY, 
    base_url="https://api.openai.com"
)

@mcp.tool()
def get_quote() -> str:
    try:
        response = requests.get("https://zenquotes.io/api/random")
        response.raise_for_status()
        data = response.json()[0]
        return f'"{data["q"]}" - {data["a"]}'
    except requests.exceptions.RequestException as e:
        return "Could not fetch a quote today, but make it a great day!"

@mcp.tool()
def get_weather(city):
    try:
        url = f"http://api.weatherapi.com/v1/forecast.json?key={WEATHER_API_KEY}&q={city}&days=1&aqi=no&alerts=no"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        forecast = data['forecast']['forecastday'][0]['day']
        condition = forecast['condition']['text']
        temp_f = forecast['avgtemp_f']
        return f"Today in {city}, expect {condition} with an average temperature of {temp_f}°F."
    except requests.exceptions.RequestException as e:
        return "Could not fetch the weather."

@mcp.tool()
def generate_ai_briefing(quote, weather, calendar_items=[]):
    prompt = f"""
        Create a concise, elegant morning briefing.

        Return the response in this exact structure:

        QUOTE:
        WEATHER:
        CALENDAR:
        CLOSING:

        Today's date: {datetime.now().strftime('%A, %B %d, %Y')}
        Quote: {quote}
        Weather: {weather}
        Calendar: {', '.join(calendar_items) if calendar_items else 'None'}
        """
    
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        text = response.choices[0].message.content

        if not text:
            text = "AI generated no content."

        return text

    except Exception as e:
        return f"<h3>Error during AI generation</h3><p>{e}</p>"

def format_email_html(ai_text):
    sections = {
        "QUOTE": "",
        "WEATHER": "",
        "CALENDAR": "",
        "CLOSING": ""
    }

    current_key = None
    for line in ai_text.splitlines():
        # Clean the line by removing AI markdown like ** or ##
        clean_line = line.replace("*", "").replace("#", "").strip()
        upper_line = clean_line.upper()
        
        # Check if the line starts with our keywords, regardless of markdown
        if upper_line.startswith("QUOTE:"):
            current_key = "QUOTE"
            sections[current_key] += clean_line[6:].strip() + " "
        elif upper_line.startswith("WEATHER:"):
            current_key = "WEATHER"
            sections[current_key] += clean_line[8:].strip() + " "
        elif upper_line.startswith("CALENDAR:"):
            current_key = "CALENDAR"
            sections[current_key] += clean_line[9:].strip() + " "
        elif upper_line.startswith("CLOSING:"):
            current_key = "CLOSING"
            sections[current_key] += clean_line[8:].strip() + " "
        elif current_key and clean_line:
            # If we are under a header, keep adding the text
            sections[current_key] += clean_line + "<br><br>"

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color:#f4f6f8; padding:20px;">
        <div style="max-width:600px; margin:auto; background:white; padding:25px; border-radius:10px;">
            
            <h2 style="color:#2c3e50;">☀️ Good Morning!</h2>
            <p style="color:#7f8c8d;">
                {datetime.now().strftime('%A, %B %d, %Y')}
            </p>

            <hr>

            <h3 style="color:#34495e;">🌿 Inspirational Quote</h3>
            <p style="font-style:italic;">{sections["QUOTE"]}</p>

            <h3 style="color:#34495e;">🌤 Weather</h3>
            <p>{sections["WEATHER"]}</p>

            <h3 style="color:#34495e;">📅 Calendar</h3>
            <p>{sections["CALENDAR"]}</p>

            <hr>

            <p style="margin-top:20px;">{sections["CLOSING"]}</p>

        </div>
    </body>
    </html>
    """
    return html

@mcp.tool()
def send_email(html_content):
    sender = os.getenv("EMAIL_ADDRESS")
    password = os.getenv("EMAIL_PASSWORD")
    recipient = os.getenv("RECIPIENT_EMAIL")

    msg = MIMEText(html_content, 'html')
    msg["Subject"] = f"Your Morning Briefing - {datetime.now().strftime('%B %d')}"
    msg["From"] = sender
    msg["To"] = recipient

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.sendmail(sender, recipient, msg.as_string())

@mcp.tool()
def gather_all_data():
    # Gather ALL the raw data first
    daily_quote = get_quote()
    weather_forecast = get_weather(LOCATION)
    
    # Fetch calendar events (and pull just the 'summary' or title of each event so the AI can read it)
    raw_events = get_calendar_events()
    
    # Format the events into a simple text list for the AI
    calendar_items = []
    for event in raw_events:
        # Get the event name (defaults to "Busy" if no title)
        title = event.get('summary', 'Busy')
        
        # Try to get the start time
        start = event['start'].get('dateTime', event['start'].get('date'))
        
        calendar_items.append(f"{title} at {start}")

    # Hand ALL the data to the AI to think and write the briefing
    ai_content = generate_ai_briefing(daily_quote, weather_forecast, calendar_items)

    # Format and send the email
    html_content = format_email_html(ai_content)
    send_email(html_content)

if __name__ == "__main__":
    if os.getenv("RUN_DAILY") == "true":
        # print("Running daily briefing...", file=sys.stderr)
        gather_all_data()
    else:
        mcp.run(transport="stdio")