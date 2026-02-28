from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

flow = InstalledAppFlow.from_client_secrets_file(
    "credentials.json",
    SCOPES
)

creds = flow.run_local_server(
    host="localhost",
    port=8080,
    authorization_prompt_message="Please visit this URL: {url}",
    success_message="Authentication complete. You may close this window.",
    open_browser=True,
)

with open("token.json", "w") as token:
    token.write(creds.to_json())

print("Token generated successfully!")