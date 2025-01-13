# Gemini API Handler

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A robust Python library for managing Google's Gemini API with intelligent key rotation, multiple generation strategies, and comprehensive error handling.

## Features

🔄 **Smart Key Rotation**
- Multiple rotation strategies (Round Robin, Sequential, Least Used, Smart Cooldown)
- Automatic rate limit management
- Load balancing across multiple API keys

🚀 **Flexible Generation Strategies**
- Round Robin: Cycle through models for optimal performance
- Fallback: Gracefully handle model unavailability
- Retry: Automatic retries with configurable backoff

⚡ **High Performance**
- Parallel processing capabilities
- Efficient key usage management
- Optimized response handling

🛡 **Robust Error Handling**
- Comprehensive error recovery
- Rate limit protection
- Detailed error reporting

## Installation

```bash
pip install gemini-api-handler
```

## Quick Start

```python
from gemini_handler import GeminiHandler, Strategy, KeyRotationStrategy

# Initialize handler
handler = GeminiHandler(
    api_keys=['your-api-key-1', 'your-api-key-2'],
    content_strategy=Strategy.ROUND_ROBIN,
    key_strategy=KeyRotationStrategy.SMART_COOLDOWN
)

# Generate content
response = handler.generate_content(
    prompt="Your prompt here",
    model_name="gemini-2.0-flash-exp"
)

print(response['text'])
```

## Basic Usage

### Key Rotation Management

```python
# Configure handler with key rotation strategy
handler = GeminiHandler(
    api_keys=api_keys,
    key_strategy=KeyRotationStrategy.SMART_COOLDOWN,
    rate_limit=60,  # Requests per minute
    reset_window=60  # Reset window in seconds
)
```

### Content Generation Strategies

```python
# Round Robin Strategy - Cycle through models
handler = GeminiHandler(
    api_keys=api_keys,
    content_strategy=Strategy.ROUND_ROBIN
)

# Fallback Strategy - Try alternate models on failure
handler = GeminiHandler(
    api_keys=api_keys,
    content_strategy=Strategy.FALLBACK
)

# Retry Strategy - Multiple attempts with same model
handler = GeminiHandler(
    api_keys=api_keys,
    content_strategy=Strategy.RETRY
)
```

## Advanced Configuration

### Custom Generation Parameters

```python
from gemini_handler import GenerationConfig

config = GenerationConfig(
    temperature=0.7,
    top_p=0.9,
    top_k=40,
    max_output_tokens=8192
)

handler = GeminiHandler(
    api_keys=api_keys,
    generation_config=config
)
```

### Monitoring Key Usage

```python
# Get usage statistics
stats = handler.get_key_stats()

for key_index, key_stats in stats.items():
    print(f"Key {key_index}:")
    print(f"  Uses: {key_stats['uses']}")
    print(f"  Failures: {key_stats['failures']}")
    print(f"  Rate limited until: {key_stats['rate_limited_until']}")
```

## API Reference

### GeminiHandler

```python
GeminiHandler(
    api_keys: List[str],
    content_strategy: Strategy = Strategy.ROUND_ROBIN,
    key_strategy: KeyRotationStrategy = KeyRotationStrategy.ROUND_ROBIN,
    system_instruction: Optional[str] = None,
    generation_config: Optional[GenerationConfig] = None
)
```

#### Methods

- `generate_content(prompt: str, model_name: Optional[str] = None, return_stats: bool = False) -> Dict[str, Any]`
- `get_key_stats(key_index: Optional[int] = None) -> Dict[int, Dict[str, Any]]`

### Strategy Enum

- `ROUND_ROBIN`: Cycle through available models
- `FALLBACK`: Try alternate models on failure
- `RETRY`: Multiple attempts with same model

### KeyRotationStrategy Enum

- `SEQUENTIAL`: Use keys in order
- `ROUND_ROBIN`: Distribute load evenly
- `LEAST_USED`: Prioritize underutilized keys
- `SMART_COOLDOWN`: Advanced strategy considering multiple factors

## Error Handling

The handler provides comprehensive error handling:

```python
try:
    response = handler.generate_content(prompt)
    if not response['success']:
        print(f"Generation failed: {response['error']}")
except Exception as e:
    print(f"Error: {str(e)}")
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.