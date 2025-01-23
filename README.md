# Gemini API Handler Configuration Guide

A comprehensive guide to configuring and using the Gemini API Handler with detailed examples and best practices.

## Table of Contents
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration File](#configuration-file)
- [Configuration Options](#configuration-options)
- [Advanced Usage Examples](#advanced-usage-examples)
- [Security Best Practices](#security-best-practices)
- [Environment Variables](#environment-variables)
- [Troubleshooting](#troubleshooting)

## Installation

```bash
pip install google-generativeai
```

## Quick Start

1. Create a `config.yaml` file:
```yaml
gemini:
  api_keys:
    - "your-api-key-1"
    - "your-api-key-2"
  generation:
    temperature: 0.7
```

2. Basic usage:
```python
from gemini_handler import GeminiHandler

handler = GeminiHandler(config_path="config.yaml")
response = handler.generate_content("Write a story about space exploration")
print(response['text'])
```

## Configuration File

Complete `config.yaml` structure with default values:

```yaml
gemini:
  # Required: API Keys
  api_keys:
    - "your-api-key-1"
    - "your-api-key-2"

  # Optional: Generation Settings
  generation:
    temperature: 0.7
    top_p: 1.0
    top_k: 40
    max_output_tokens: 8192
    stop_sequences: []
    response_mime_type: "text/plain"

  # Optional: Rate Limiting
  rate_limits:
    requests_per_minute: 60
    reset_window: 60  # seconds

  # Optional: Strategies
  strategies:
    content: "fallback"  # round_robin, fallback, retry
    key_rotation: "smart_cooldown"  # smart_cooldown, sequential, round_robin, least_used

  # Optional: Retry Settings
  retry:
    max_attempts: 3
    delay: 30  # seconds

  # Optional: Model Settings
  default_model: "gemini-2.0-flash-exp"
  system_instruction: null  # Custom system prompt
```

## Configuration Options

### API Keys
Required authentication credentials:
```yaml
gemini:
  api_keys:
    - "key1"  # Primary key
    - "key2"  # Backup key
```

### Generation Settings
Fine-tune output generation:
```yaml
generation:
  temperature: 0.7        # Higher = more creative
  top_p: 0.95            # Nucleus sampling threshold
  top_k: 40              # Top-k sampling parameter
  max_output_tokens: 4096 # Maximum response length
```

### Rate Limiting
Control API usage:
```yaml
rate_limits:
  requests_per_minute: 60  # Maximum requests per key
  reset_window: 60         # Reset period in seconds
```

### Strategies
Configure content generation behavior:
```yaml
strategies:
  content: "round_robin"    # Model selection strategy
  key_rotation: "smart_cooldown"  # API key management
```

## Advanced Usage Examples

### 1. Basic Content Generation
```python
from gemini_handler import GeminiHandler

handler = GeminiHandler(config_path="config.yaml")

# Simple generation
response = handler.generate_content(
    prompt="Explain quantum computing"
)
print(response['text'])
```

### 2. Custom Model Selection
```python
# Use specific model
response = handler.generate_content(
    prompt="Write a poem",
    model_name="gemini-2.0-flash-exp"
)

# With generation stats
response = handler.generate_content(
    prompt="Write a technical analysis",
    model_name="gemini-1.5-pro",
    return_stats=True
)
```

### 3. Strategy-Specific Usage
```python
from gemini_handler import GeminiHandler, Strategy, KeyRotationStrategy

# Round-robin strategy
handler = GeminiHandler(
    config_path="config.yaml",
    content_strategy=Strategy.ROUND_ROBIN,
    key_strategy=KeyRotationStrategy.SMART_COOLDOWN
)

# Generate with monitoring
response = handler.generate_content(
    prompt="Complex analysis task",
    return_stats=True
)

# Print performance metrics
print(f"Generation time: {response['time']}s")
print(f"API key usage: {response['key_stats']}")
```

### 4. Error Handling
```python
response = handler.generate_content("Your prompt")
if response['success']:
    print(response['text'])
else:
    print(f"Error: {response['error']}")
    print(f"Attempts made: {response['attempts']}")
```

## Security Best Practices

1. Protect your configuration:
```bash
# Add to .gitignore
echo "config.yaml" >> .gitignore
```

2. Use environment variables in production:
```bash
# Set variables
export GEMINI_API_KEYS="key1,key2,key3"

# Use in code
handler = GeminiHandler()  # Automatically reads from env
```

3. Implement key rotation:
```python
# Configure smart key rotation
handler = GeminiHandler(
    config_path="config.yaml",
    key_strategy=KeyRotationStrategy.SMART_COOLDOWN
)
```

## Environment Variables

Alternative to `config.yaml`:
```bash
# Multiple keys
export GEMINI_API_KEYS="key1,key2,key3"

# Single key
export GEMINI_API_KEY="your-key"

# Optional settings
export GEMINI_DEFAULT_MODEL="gemini-2.0-flash-exp"
export GEMINI_MAX_RETRIES="3"
```

## Troubleshooting

Common issues and solutions:

1. Rate Limiting
```python
# Monitor key usage
stats = handler.get_key_stats()
print(stats)  # Check rate limit status
```

2. Model Availability
```python
# Fallback strategy for reliability
handler = GeminiHandler(
    config_path="config.yaml",
    content_strategy=Strategy.FALLBACK
)
```

3. Performance Optimization
```python
# Optimize for high-throughput
handler = GeminiHandler(
    config_path="config.yaml",
    key_strategy=KeyRotationStrategy.ROUND_ROBIN,
    content_strategy=Strategy.RETRY
)
```

For more detailed information and updates, refer to the [official documentation](#).
