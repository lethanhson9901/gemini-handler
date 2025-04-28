# config.py
import os

# --- Centralized Configuration ---
# Use the shorter model ID suitable for genai.GenerativeModel
MODEL_ID = "gemini-2.5-flash-preview-04-17"
# Full name used for get_model/list_models if needed
FULL_MODEL_NAME_FOR_LISTING = f"models/{MODEL_ID}"

# --- API Key ---
# Load API key from environment variable
API_KEY = os.getenv("GEMINI_API_KEY")