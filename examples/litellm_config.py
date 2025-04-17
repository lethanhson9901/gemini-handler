# examples/litellm_config.py

import os
import sys
from pathlib import Path

# Add the parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from litellm import completion

import gemini_handler

# Optional: Set up API keys via environment variables
os.environ["GEMINI_API_KEY"] = "your-api-key-here"  # Replace with your key

def test_gemini_with_litellm():
    """Test using Gemini Handler with LiteLLM."""
    
    # This is a standard LiteLLM call using your custom provider
    response = completion(
        model="custom/gemini-2.0-flash",  # The 'custom/' prefix tells LiteLLM to use a custom provider
        messages=[
            {"role": "system", "content": "You are a helpful AI assistant."},
            {"role": "user", "content": "What is the capital of France?"}
        ],
        temperature=0.7,
        max_tokens=1024,
        custom_llm_provider="gemini",  # This is how LiteLLM identifies your provider
    )
    
    print("Response from LiteLLM using Gemini:")
    print(response)

# Execute the test
if __name__ == "__main__":
    test_gemini_with_litellm()
