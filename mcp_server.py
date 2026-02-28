import os
import smtplib
import requests
import sys
from email.mime.text import MIMEText
from dotenv import load_dotenv
from datetime import datetime
from openai import OpenAI
from mcp.server.fastmcp import FastMCP

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

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
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    service = build("calendar", "v3", credentials=creds)

    events = service.events().list(
        calendarId="primary",
        maxResults=5,
        singleEvents=True,
        orderBy="startTime"
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
    Here is today's information for my briefing:
    - Today's date is {datetime.now().strftime('%A, %B %d, %Y')}.
    - Inspirational Quote: {quote}
    - Weather Forecast: {weather}
    - Upcoming from Calendar: {', '.join(calendar_items) if calendar_items else 'None'}
    """
    
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        response = client.responses.create(
            model="gpt-4.1",
            input=prompt
        )

        text = response.output_text

        if not text:
            text = "AI generated no content."

        return text

    except Exception as e:
        return f"<h3>Error during AI generation</h3><p>{e}</p>"

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
    # Get quote and weather in parallel to save time
    daily_quote = get_quote()
    # Slice to keep log clean
    
    weather_forecast = get_weather(LOCATION)

    # Think with AI
    ai_content = generate_ai_briefing(daily_quote, weather_forecast)

    # Google Calendar events
    calendar_events = get_calendar_events()

    # Send the email
    send_email(ai_content)

if __name__ == "__main__":
    if os.getenv("RUN_DAILY") == "true":
        print("Running daily briefing...", file=sys.stderr)
        gather_all_data()
    else:
        mcp.run(transport="stdio")