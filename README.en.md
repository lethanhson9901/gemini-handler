# Gemini Handler

A powerful Python library for interacting with Google's Gemini API, featuring intelligent key management and flexible response handling.

## Key Features

- **Multi-API Key Management**: Automatic rotation, usage optimization, and rate limit handling
- **Diverse Content Generation Strategies**: Support for round-robin, fallback, and retry approaches
- **Structured Output Support**: Generate JSON data based on custom schemas
- **Intelligent Error Handling**: Automatic retries and fallback options when errors occur
- **Performance Monitoring**: Track API usage and response times

## Installation

```bash
pip install gemini-handler
```

Or install from source:

```bash
git clone https://github.com/yourusername/gemini-handler.git
cd gemini-handler
pip install -e .
```

## Basic Usage

### Simple Content Generation

```python
from gemini_handler import GeminiHandler

# Initialize handler with configuration file
handler = GeminiHandler(config_path="config.yaml")

# Generate content
response = handler.generate_content("Explain artificial intelligence to beginners")

# Check and display results
if response['success']:
    print(response['text'])
else:
    print(f"Error: {response['error']}")
```

### Structured Data Generation

```python
# Define desired data structure
movie_schema = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "Movie title"},
        "director": {"type": "string", "description": "Movie director"},
        "year": {"type": "integer", "description": "Release year"},
        "rating": {"type": "number", "description": "Movie rating"}
    },
    "required": ["title", "director", "year", "rating"]
}

# Generate structured data
result = handler.generate_structured_content(
    prompt="Recommend a good science fiction movie",
    schema=movie_schema
)

# Display results
if result['success']:
    movie = result['structured_data']
    print(f"Title: {movie['title']}")
    print(f"Director: {movie['director']}")
    print(f"Year: {movie['year']}")
    print(f"Rating: {movie['rating']}")
```

## Configuration

Create a `config.yaml` file with the following settings:

```yaml
gemini:
  # API Keys (required)
  api_keys:
    - "your-api-key-1"
    - "your-api-key-2"

  # Generation settings (optional)
  generation:
    temperature: 0.7          # Creativity level (0.0-1.0)
    top_p: 1.0                # Sampling threshold
    top_k: 40                 # Number of tokens to consider
    max_output_tokens: 8192   # Maximum response length

  # Rate limits (optional)
  rate_limits:
    requests_per_minute: 60   # Maximum requests per minute
    reset_window: 60          # Reset time (seconds)

  # Strategies (optional)
  strategies:
    content: "round_robin"    # Content generation strategy
    key_rotation: "smart_cooldown"  # Key rotation strategy

  # Retry settings (optional)
  retry:
    max_attempts: 3           # Maximum retry attempts
    delay: 30                 # Wait time between retries (seconds)

  # Default model (optional)
  default_model: "gemini-2.0-flash-exp"
```

## Strategies

### Content Generation Strategies

| Strategy | Description | When to Use |
|----------|-------------|-------------|
| **Round Robin** | Uses models in rotation | When you want to distribute load evenly across models |
| **Fallback** | Tries models in order, switching to next when errors occur | When high reliability is needed |
| **Retry** | Retries the same model multiple times when errors occur | When consistency in model usage is important |

### API Key Rotation Strategies

| Strategy | Description | When to Use |
|----------|-------------|-------------|
| **Sequential** | Uses keys in fixed order | When you want to prioritize certain keys |
| **Round Robin** | Uses keys in rotation | When you want to distribute requests evenly |
| **Least Used** | Prioritizes keys with lowest usage count | When balancing load across keys is important |
| **Smart Cooldown** | Automatically adjusts key usage based on errors | When high self-recovery capability is needed |

## Advanced Usage

### Custom Strategy Selection

```python
from gemini_handler import GeminiHandler, Strategy, KeyRotationStrategy

# Initialize with custom strategies
handler = GeminiHandler(
    config_path="config.yaml",
    content_strategy=Strategy.FALLBACK,         # Use fallback strategy
    key_strategy=KeyRotationStrategy.SMART_COOLDOWN  # Use smart cooldown strategy
)
```

### Performance Monitoring

```python
# Generate content with performance information
response = handler.generate_content(
    prompt="Write an analysis of AI trends in 2023",
    return_stats=True
)

# Display performance information
print(f"Generation time: {response['time']} seconds")
print(f"Model used: {response['model']}")
```

### API Key Usage Monitoring

```python
# Get key usage statistics
key_stats = handler.get_key_stats()

# Display information for each key
for key_idx, stats in key_stats.items():
    print(f"Key {key_idx}:")
    print(f"  Uses: {stats['uses']}")
    print(f"  Last used: {stats['last_used']}")
    print(f"  Failures: {stats['failures']}")
```

## Error Handling

```python
# Generate content with error handling
response = handler.generate_content("Your prompt")

# Check results
if response['success']:
    print(response['text'])
else:
    print(f"Error: {response['error']}")
    print(f"Attempts: {response['attempts']}")
    print(f"Model tried: {response['model']}")
```

## Environment Variables

You can also configure through environment variables:

```bash
# Multiple keys
export GEMINI_API_KEYS="key1,key2,key3"

# Single key
export GEMINI_API_KEY="your-key"

# Other settings
export GEMINI_DEFAULT_MODEL="gemini-2.0-flash-exp"
export GEMINI_MAX_RETRIES="3"
```

## Real-World Example

### Building a Chatbot with Robust Error Handling

```python
from gemini_handler import GeminiHandler, Strategy, KeyRotationStrategy

# Initialize handler with optimal strategies
handler = GeminiHandler(
    config_path="config.yaml",
    content_strategy=Strategy.FALLBACK,
    key_strategy=KeyRotationStrategy.SMART_COOLDOWN
)

def chat_with_user():
    print("Chatbot: Hello! How can I help you today?")
    
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["goodbye", "bye", "exit"]:
            print("Chatbot: Goodbye! See you next time!")
            break
            
        # Generate response with error handling
        response = handler.generate_content(
            prompt=f"User: {user_input}\nChatbot:",
            model_name="gemini-2.0-flash-exp"
        )
        
        if response['success']:
            print(f"Chatbot: {response['text']}")
        else:
            # Try with different model if error occurs
            fallback_response = handler.generate_content(
                prompt=f"User: {user_input}\nChatbot:",
                model_name="gemini-1.5-flash"
            )
            
            if fallback_response['success']:
                print(f"Chatbot: {fallback_response['text']}")
            else:
                print("Chatbot: I'm sorry, I'm experiencing technical difficulties. Please try again later.")

# Run chatbot
if __name__ == "__main__":
    chat_with_user()
```

## License

This project is released under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please create a Pull Request or open an Issue if you have ideas for improvement.