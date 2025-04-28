# utils.py
import mimetypes
from pathlib import Path

import google.generativeai as genai
import requests

# --- Helper Functions ---

def print_section_header(title):
    """Prints a formatted section header."""
    print("\n" + "=" * 60)
    print(f"--- {title} ---")
    print("=" * 60)

def check_and_download(filename, url, description):
    """Checks if a file exists, downloads it if not."""
    path = Path(filename)
    if not path.exists():
        print(f"Local file '{filename}' not found. Attempting to download sample {description}...")
        try:
            headers = {'User-Agent': 'Mozilla/5.0'} # Needed for some sites like arXiv
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            with open(filename, 'wb') as f:
                f.write(response.content)
            print(f"Sample {description} saved as '{filename}'.")
            return path
        except requests.exceptions.RequestException as e:
            print(f"Failed to download sample {description}: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred during download: {e}")
            return None
    else:
        print(f"Using existing local file: '{filename}'")
        return path

def get_mime_type(path, fallback_prefix):
    """Guesses MIME type, provides fallback if needed."""
    mime_type, _ = mimetypes.guess_type(path)
    if not mime_type or not mime_type.startswith(fallback_prefix + '/'):
         print(f"Warning: Could not determine valid {fallback_prefix} MIME type for {path}. Falling back.")
         if fallback_prefix == 'image':
             return 'image/jpeg'
         elif fallback_prefix == 'audio':
             return 'audio/mpeg'
         elif fallback_prefix == 'application':
              return 'application/pdf'
         else:
             return None # Should not happen for these types
    return mime_type

def print_response_summary(response):
    """Prints key details from a generate_content response."""
    print(f"Response Text: {response.text[:100]}...") # Show snippet
    if response.candidates:
        print(f"Number of Candidates: {len(response.candidates)}")
        candidate = response.candidates[0] # Use index 0
        # Convert finish_reason enum to name if possible
        finish_reason_str = getattr(candidate.finish_reason, 'name', str(candidate.finish_reason))
        print(f"  Candidate Finish Reason: {finish_reason_str}")
        print(f"  Candidate Safety Ratings: {candidate.safety_ratings if candidate.safety_ratings else '[]'}")
    if hasattr(response, 'prompt_feedback') and response.prompt_feedback: # Check attribute existence
        block_reason_str = getattr(response.prompt_feedback.block_reason, 'name', str(response.prompt_feedback.block_reason))
        print(f"Prompt Feedback Block Reason: {block_reason_str}")
        print(f"Prompt Feedback Safety Ratings: {response.prompt_feedback.safety_ratings if response.prompt_feedback.safety_ratings else '[]'}")
    else:
         print("Prompt Feedback: Not available in this response.")
    if hasattr(response, 'usage_metadata') and response.usage_metadata: # Check attribute existence
         print(f"Usage Metadata:")
         print(f"  Prompt Tokens: {getattr(response.usage_metadata, 'prompt_token_count', 'N/A')}")
         print(f"  Candidates Tokens: {getattr(response.usage_metadata, 'candidates_token_count', 'N/A')}")
         print(f"  Total Tokens: {getattr(response.usage_metadata, 'total_token_count', 'N/A')}")
         # Check for thinking tokens
         if hasattr(response.usage_metadata, 'thinking_token_count'):
             print(f"  Thinking Tokens: {response.usage_metadata.thinking_token_count}")
         else:
             print("  Thinking Tokens: (Not reported in this response)")
    else:
         print("Usage Metadata: Not available in this response.")

def initialize_gemini(api_key, model_id_to_check):
    """Configures genai and verifies access to a model."""
    if not api_key:
        print("ERROR: API Key not provided.")
        return None, False

    try:
        print("Configuring Google AI Studio access (using API Key)...")
        genai.configure(api_key=api_key)

        print(f"Verifying access to model: {model_id_to_check}")
        model_info = genai.get_model(model_id_to_check)
        print(f"Successfully verified access. Model: {model_info.display_name}")

        print(f"Initialization successful for model family.")
        return genai, True # Return the configured module

    except Exception as e:
        print(f"ERROR: Failed to configure or verify access: {e}")
        return None, False