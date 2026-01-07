import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("GEMINI_API_KEY not found in .env")
else:
    genai.configure(api_key=api_key)
    try:
        print("Checking API key and listing models...")
        models = [m.name for m in genai.list_models()]
        print("Available models:")
        for m in models:
            print(f" - {m}")
    except Exception as e:
        print(f"Error: {e}")
