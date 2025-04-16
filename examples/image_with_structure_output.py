import json
import os
from pathlib import Path

from gemini_handler import (
    GeminiHandler,
    GenerationConfig,
    KeyRotationStrategy,
    Strategy,
)

# Define schema
person_schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "The person's full name."},
        "age_estimate": {"type": "integer", "description": "Estimated age of the person."},
        "mood": {"type": "string", "description": "Apparent mood or emotion."},
        "has_glasses": {"type": "boolean", "description": "Does the person wear glasses?"}
    },
    "required": ["name", "age_estimate", "mood"]
}

# Create dummy image file for testing
image_path = Path("1.jpeg")
try:
    from PIL import Image
    img = Image.new('RGB', (60, 30), color = 'red')
    img.save(image_path)
    print(f"Created dummy image: {image_path}")
except ImportError:
    print("Pillow not installed. Cannot create dummy image.")

# Initialize Handler
handler = GeminiHandler(
    config_path="../config.yaml",
    content_strategy=Strategy.RETRY,
    key_strategy=KeyRotationStrategy.ROUND_ROBIN,
    generation_config=GenerationConfig(temperature=0.7)
)

# Generate content with local file directly
prompt = "Describe the person in this image according to the provided schema."
print(f"\nGenerating structured content for local file {image_path}...")

# Use the new method that works directly with local files
structured_result = handler.generate_with_local_file(
    file_path=image_path,
    prompt=prompt,
    schema=person_schema,
    model_name="gemini-2.0-flash",  # Use a vision-capable model
    return_stats=True
)

# Process the result
print("\n--- Structured Generation Result ---")
if structured_result["success"]:
    print(f"Model Used: {structured_result['model']}")
    print(f"Time Taken: {structured_result['time']:.2f}s")
    print(f"API Key Index Used: {structured_result['api_key_index']}")
    print(f"File Info: {structured_result.get('file_info')}")

    # Access the parsed JSON data
    parsed_data = structured_result.get("structured_data")
    if parsed_data:
        print("Parsed JSON Output:")
        print(json.dumps(parsed_data, indent=2))
    else:
        print("Structured data is missing, raw text:")
        print(structured_result.get("text"))

    if structured_result.get("key_stats"):
        print("\nKey Usage Stats:")
        print(json.dumps(structured_result["key_stats"], indent=2))
else:
    print(f"Error generating structured content: {structured_result['error']}")
    print(f"Model Attempted: {structured_result['model']}")
    print(f"API Key Index Used: {structured_result['api_key_index']}")
    print(f"File Info: {structured_result.get('file_info')}")

# Clean up
if image_path.exists():
    os.remove(image_path)
    print(f"Deleted image file: {image_path}")
