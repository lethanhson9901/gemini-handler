from gemini_handler import GeminiHandler

# Initialize with config file path
handler = GeminiHandler(
    config_path="../config.yaml",  # Path to your config file with proxy settings
)

# Generate content (request will use your configured proxy)
result = handler.generate_content(
    prompt="What's the current tech trend in artificial intelligence?",
)

print(f"Success: {result['success']}")
print(f"Model used: {result['model']}")
print(f"Generation time: {result['time']:.2f} seconds")
print("\nResponse:")
print(result['text'])
