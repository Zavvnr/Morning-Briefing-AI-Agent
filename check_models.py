# check_models.py
import os
import google.generativeai as genai
from dotenv import load_dotenv

print("--- Starting Model Check ---")

try:
    load_dotenv()
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    genai.configure(api_key=GOOGLE_API_KEY)

    print(f"--- Using google-generativeai version: {genai.__version__} ---")
    print("--- Attempting to list models... ---")

    found_models = False
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"Found model: {m.name}")
            found_models = True

    if not found_models:
        print("--- No models found that support 'generateContent'. ---")

except Exception as e:
    print(f"--- CRITICAL ERROR while listing models: {e} ---")

print("--- Model Check Finished ---")
