import os
from pathlib import Path
from typing import List, Optional, Union

import yaml


class ConfigLoader:
    """Handles loading configuration from various sources."""
    
    @staticmethod
    def load_api_keys(config_path: Optional[Union[str, Path]] = None) -> List[str]:
        """
        Load API keys from multiple sources in priority order:
        1. YAML config file if provided
        2. Environment variables (GEMINI_API_KEYS as comma-separated string)
        3. Single GEMINI_API_KEY environment variable
        """
        # Try loading from YAML config
        if config_path:
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    if config and 'gemini' in config and 'api_keys' in config['gemini']:
                        keys = config['gemini']['api_keys']
                        if isinstance(keys, list) and all(isinstance(k, str) for k in keys):
                            return keys
            except Exception as e:
                print(f"Warning: Failed to load config from {config_path}: {e}")

        # Try loading from GEMINI_API_KEYS environment variable
        api_keys_str = os.getenv('GEMINI_API_KEYS')
        if api_keys_str:
            keys = [k.strip() for k in api_keys_str.split(',') if k.strip()]
            if keys:
                return keys

        # Try loading single API key
        single_key = os.getenv('GEMINI_API_KEY')
        if single_key:
            return [single_key]

        raise ValueError(
            "No API keys found. Please provide keys via config file, "
            "GEMINI_API_KEYS environment variable (comma-separated), "
            "or GEMINI_API_KEY environment variable."
        )
