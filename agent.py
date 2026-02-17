import os
import smtplib
import requests
import google.generativeai as genai
import pytz
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from datetime import datetime, timedelta

print(f"--- Using google-generativeai version: {genai.__version__} ---")

# Load environment variables from .env file
load_dotenv()

# Configuration
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')
GMAIL_SENDER = os.getenv('GMAIL_SENDER')
GMAIL_APP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD')
RECIPIENT_EMAIL = os.getenv('RECIPIENT_EMAIL')
LOCATION = "Madison, Wisconsin"
TIMEZONE = "America/Chicago"

# Configure the Deepseek API
genai.configure(api_key=DEEPSEEK_API_KEY)

# System Instruction for the AI model
SYSTEM_INSTRUCTION = """
You are a helpful and motivational morning assistant.
Your task is to create a short, inspiring morning briefing for a university student.
The tone should be positive and encouraging. Start with a friendly greeting.

Format the output as a simple HTML email. Do not include <html> or <body> tags.
Use <h2> for the main title, <h3> for sub-sections, <p> for paragraphs, and <ul> and <li> for lists.

Based on the user's provided information (quote, weather, and callendar), generate:
1.  A "Today's Priorities" to-do list with 3-4 actionable items. Prioritize conferences/one-time events before anything due today or tomorrow.
2.  A "Weekly Outlook" section that lists the other Calendar items.
"""

MODEL_NAME = "models/DeepSeek-R1 / V3" 

model = genai.GenerativeModel(
    MODEL_NAME,
    system_instruction=SYSTEM_INSTRUCTION
)

def get_quote():
    print("DEBUG: Fetching quote...")
    try:
        response = requests.get("https://zenquotes.io/api/random")
        response.raise_for_status()
        data = response.json()[0]
        return f'"{data["q"]}" - {data["a"]}'
    except requests.exceptions.RequestException as e:
        print(f"DEBUG: Error fetching quote: {e}", file=sys.stderr)
        return "Could not fetch a quote today, but make it a great day!"

def get_weather(city):
    print("DEBUG: Fetching weather...")
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
        print(f"DEBUG: Error fetching weather: {e}", file=sys.stderr)
        return "Could not fetch the weather."

def generate_ai_briefing(quote, weather):
    print("DEBUG: Inside generate_ai_briefing function.")
    prompt = f"""
    Here is today's information for my briefing:
    - Today's date is {datetime.now().strftime('%A, %B %d, %Y')}.
    - Inspirational Quote: {quote}
    - Weather Forecast: {weather}
    - Upcoming from Calendar: 
    """
    
    try:
        print("DEBUG: Calling AI model (DeepSeek-R1 / V3)...")
        response = model.generate_content(prompt)
        
        if not response.text:
            print("DEBUG: AI returned an EMPTY response.")
        else:
            # Slice to avoid spamming the log
            print(f"DEBUG: AI returned a response. Start: {response.text[:70]}...")
            
        return response.text
        
    except Exception as e:
        # Use stderr to make sure this error appears
        print(f"CRITICAL: Error during AI generation: {e}", file=sys.stderr)
        return f"<h3>Error during AI generation</h3><p>{e}</p>" # Return an error message to email

def send_email(html_content):
    print("DEBUG: Inside send_email function.")
    
    if not html_content:
        print("DEBUG: HTML content is empty. Skipping email.")
        return # Don't send a blank email

    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"Your Morning Briefing - {datetime.now().strftime('%B %d')}"
    msg['From'] = GMAIL_SENDER
    msg['To'] = RECIPIENT_EMAIL
    msg.attach(MIMEText(html_content, 'html'))

    try:
        print("DEBUG: Attempting SMTP connection...")
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
            print("DEBUG: Attempting SMTP login...")
            smtp_server.login(GMAIL_SENDER, GMAIL_APP_PASSWORD)
            print("DEBUG: Attempting to send mail...")
            smtp_server.sendmail(GMAIL_SENDER, RECIPIENT_EMAIL, msg.as_string())
        print("Email sent successfully!") # This is the original, good print

    except Exception as e:
        # Use stderr to make sure this error appears
        print(f"CRITICAL: Error sending email: {e}", file=sys.stderr)

if __name__ == "__main__":
    print("Agent is running...")
    
    # Gather data
    daily_quote = get_quote()
    # Slice to keep log clean
    print(f"DEBUG: Quote retrieved: {daily_quote[:30]}...") 
    
    weather_forecast = get_weather(LOCATION)
    print(f"DEBUG: Weather retrieved: {weather_forecast}")

    # Think with AI
    print("DEBUG: Calling generate_ai_briefing...")
    ai_content = generate_ai_briefing(daily_quote, weather_forecast)

    # Send the email
    print("DEBUG: Calling send_email...")
    send_email(ai_content)
    
    print("Agent has finished its task.")
