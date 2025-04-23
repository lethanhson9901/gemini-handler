import litellm
from gemini_handler import GeminiHandlerLiteLLM, GeminiHandler # Import your classes

# --- Option A: Initialize handler first ---
# Initialize your GeminiHandler as needed (e.g., from config file)
my_handler = GeminiHandler(config_path="../config.yaml")
# Initialize the LiteLLM provider wrapper with the handler instance
GeminiHandlerLiteLLM.initialize(handler_instance=my_handler)

# --- Option B: Initialize handler via kwargs ---
# GeminiHandlerLiteLLM.initialize(config_path="config.yaml", key_strategy="smart_cooldown")

# Register the provider class with a specific prefix
litellm.register_provider(
    "custom_gemini", # The prefix you'll use in model names
    provider_class=GeminiHandlerLiteLLM # Your custom class
)

# --- Example Usage ---

# Text Generation
try:
    response = litellm.completion(
        model="custom_gemini/gemini-2.0-flash", # Use the registered prefix
        messages=[{"role": "user", "content": "Explain quantum physics simply."}],
        temperature=0.6,
        # Pass extra args supported by your handler if needed (via kwargs)
        # return_stats=True
    )
    print("Completion Response:")
    print(response.choices[0].message.content)
    # print(response) # Print full response object

except Exception as e:
    print(f"Completion Error: {e}")

# Structured Output
try:
    movie_schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "director": {"type": "string"},
            "year": {"type": "integer"}
        },
        "required": ["title", "director", "year"]
    }
    response_structured = litellm.completion(
        model="custom_gemini/gemini-1.5-pro", # Use a model good at JSON
        messages=[{"role": "user", "content": "Suggest a sci-fi movie."}],
        response_format={"type": "json_object", "schema": movie_schema}
    )
    print("\nStructured Response:")
    print(response_structured.choices[0].message.content)

except Exception as e:
    print(f"Structured Completion Error: {e}")


# Embedding
try:
    embedding_response = litellm.embedding(
        model="custom_gemini/gemini-embedding-exp-03-07", # Use embedding model name
        input=["Hello world", "How are you?"]
        # task_type="SEMANTIC_SIMILARITY" # Pass gemini specific params
    )
    print("\nEmbedding Response:")
    print(f"Received {len(embedding_response.data)} embeddings.")
    # print(embedding_response.data[0].embedding[:5]) # Print first 5 dims of first embedding

except Exception as e:
    print(f"Embedding Error: {e}")