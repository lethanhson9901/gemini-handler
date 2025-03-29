import os
import re

import google.generativeai as genai
import yaml

# Read API key from config.yaml file
config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.yaml')

try:
    with open(config_path, 'r') as config_file:
        config = yaml.safe_load(config_file)
        
    # Validate config structure and get API key
    if config and 'gemini' in config and 'api_keys' in config['gemini'] and config['gemini']['api_keys']:
        api_key = config['gemini']['api_keys'][0]  # Get the first key from the list
    else:
        raise ValueError("API key not found in config.yaml")
        
except FileNotFoundError:
    raise FileNotFoundError(f"Config file not found at {config_path}")
except yaml.YAMLError:
    raise ValueError("config.yaml is not a valid YAML file")
except Exception as e:
    raise Exception(f"Error reading config file: {str(e)}")

# Configure API key
genai.configure(api_key=api_key)

# List all available models
try:
    models = genai.list_models()
    
    # Filter Gemini models and format output
    formatted_models = []
    for model in models:
        if "gemini" in model.name.lower() or "imagen" in model.name.lower():
            # Extract model name from full path (models/gemini-xxx)
            model_name = model.name.split('/')[-1]
            
            # Skip specific versions (like -001, -002) and -latest
            if re.search(r'-(00\d|latest)$', model_name):
                continue
                
            # Skip duplicate models
            if model_name not in formatted_models:
                formatted_models.append(model_name)
    
    # Add imagen-3.0-generate-002 if needed
    if "imagen-3.0-generate-002" not in formatted_models:
        formatted_models.append("imagen-3.0-generate-002")
    
    # Sort models by priority (specific models first)
    priority_order = {
        "gemini-2.0-flash": 0,
        "gemini-2.5-pro-exp-03-25": 1,
        "gemini-2.0-flash-lite": 2,
        "gemini-2.0-pro-exp-02-05": 3,
        "gemini-1.5-flash": 4,
        "gemini-1.5-flash-8b": 5,
        "gemini-1.5-pro": 6,
        "gemini-embedding-exp-03-07": 7,
        "imagen-3.0-generate-002": 8,
        "gemini-2.0-flash-thinking-exp-01-21": 9,
        "gemini-exp-1206": 10
    }
    
    # Sort by priority order
    formatted_models.sort(key=lambda x: priority_order.get(x, 999))
    
    # Print in desired format
    print("[")
    for i, model in enumerate(formatted_models):
        comma = "," if i < len(formatted_models) - 1 else ""
        print(f'    "{model}"{comma}')
    print("]")
    
except Exception as e:
    print(f"Error retrieving model list: {e}")
