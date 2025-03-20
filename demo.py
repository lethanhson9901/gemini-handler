# Example usage
from typing import Any, Dict

from gemini_handler import GeminiHandler

# Define your schema
movie_schema: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "Title of the movie"},
        "director": {"type": "string", "description": "Director of the movie"},
        "year": {"type": "integer", "description": "Year of release"},
        "imdbRating": {"type": "number", "description": "IMDb rating of the movie"}
    },
    "required": ["title", "director", "year", "imdbRating"]
}

# Initialize your handler
handler = GeminiHandler(config_path="config.yaml")

# Generate structured content
result = handler.generate_structured_content(
    prompt="What's a good mystery movie?",
    schema=movie_schema,
    model_name="gemini-1.5-pro"
)

# Access the structured data
if result['success']:
    structured_data = result['structured_data']
    print(f"Title: {structured_data['title']}")
    print(f"Director: {structured_data['director']}")
    print(f"Year: {structured_data['year']}")
    print(f"Rating: {structured_data['imdbRating']}")
else:
    print(f"Error: {result['error']}")
