from gemini_handler import GeminiHandler

# Configure with auto proxy
handler = GeminiHandler(
    config_path="../config.yaml",
    proxy_settings={
        'auto_proxy': {
            'auto_update': True,
            'auto_rotate': True,
            'update_interval': 15
        }
    }
)

# Each request will use a different proxy
result = handler.generate_content("Just say Hi")
print(result)