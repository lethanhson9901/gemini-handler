# gemini_handler/config_loader.py

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml


class ServerConfig:
    """Configuration for the Gemini API Server."""
    
    def __init__(
        self,
        config_path: Optional[Union[str, Path]] = None,
        env_prefix: str = "GEMINI_"
    ):
        self.config_path = config_path
        self.env_prefix = env_prefix
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file and environment variables."""
        # Start with default config
        config = {
            "server": {
                "host": "0.0.0.0",
                "port": 8000,
                "workers": 1,
                "log_level": "info"
            },
            "gemini": {
                "api_keys": [],
                "default_model": "gemini-2.0-flash",
                "content_strategy": "round_robin",
                "key_strategy": "round_robin",
                "rate_limit": 60,
                "reset_window": 60
            },
            "security": {
                "require_auth": False,
                "api_keys": []
            }
        }
        
        # Override with YAML config if provided
        if self.config_path:
            try:
                with open(self.config_path, 'r') as f:
                    yaml_config = yaml.safe_load(f)
                    if yaml_config:
                        # Update each section that exists in the YAML
                        for section in config:
                            if section in yaml_config:
                                config[section].update(yaml_config[section])
            except Exception as e:
                print(f"Warning: Failed to load config from {self.config_path}: {e}")
        
        # Override with environment variables
        self._update_from_env(config)
        
        return config
    
    def _update_from_env(self, config: Dict[str, Any]) -> None:
        """Update config from environment variables."""
        # Server settings
        if host := os.getenv(f"{self.env_prefix}HOST"):
            config["server"]["host"] = host
            
        if port := os.getenv(f"{self.env_prefix}PORT"):
            try:
                config["server"]["port"] = int(port)
            except ValueError:
                pass
                
        if workers := os.getenv(f"{self.env_prefix}WORKERS"):
            try:
                config["server"]["workers"] = int(workers)
            except ValueError:
                pass
                
        if log_level := os.getenv(f"{self.env_prefix}LOG_LEVEL"):
            config["server"]["log_level"] = log_level
            
        # API keys (highest priority)
        api_keys = []
        
        # Multiple keys from env
        if keys_str := os.getenv(f"{self.env_prefix}API_KEYS"):
            api_keys = [k.strip() for k in keys_str.split(',') if k.strip()]
            
        # Single key from env
        elif single_key := os.getenv(f"{self.env_prefix}API_KEY"):
            api_keys = [single_key]
            
        # Update if we found any keys
        if api_keys:
            config["gemini"]["api_keys"] = api_keys
            
        # Security settings
        if require_auth_str := os.getenv(f"{self.env_prefix}REQUIRE_AUTH"):
            config["security"]["require_auth"] = require_auth_str.lower() in ("true", "yes", "1")
            
        if auth_keys_str := os.getenv(f"{self.env_prefix}AUTH_KEYS"):
            config["security"]["api_keys"] = [k.strip() for k in auth_keys_str.split(',') if k.strip()]
    
    @property
    def host(self) -> str:
        """Get server host."""
        return self._config["server"]["host"]
    
    @property
    def port(self) -> int:
        """Get server port."""
        return self._config["server"]["port"]
    
    @property
    def workers(self) -> int:
        """Get number of worker processes."""
        return self._config["server"]["workers"]
    
    @property
    def log_level(self) -> str:
        """Get log level."""
        return self._config["server"]["log_level"]
    
    @property
    def api_keys(self) -> List[str]:
        """Get Gemini API keys."""
        return self._config["gemini"]["api_keys"]
    
    @property
    def default_model(self) -> str:
        """Get default model."""
        return self._config["gemini"]["default_model"]
    
    @property
    def content_strategy(self) -> str:
        """Get content strategy."""
        return self._config["gemini"]["content_strategy"]
    
    @property
    def key_strategy(self) -> str:
        """Get key rotation strategy."""
        return self._config["gemini"]["key_strategy"]
    
    @property
    def rate_limit(self) -> int:
        """Get rate limit."""
        return self._config["gemini"]["rate_limit"]
    
    @property
    def reset_window(self) -> int:
        """Get reset window."""
        return self._config["gemini"]["reset_window"]
    
    @property
    def require_auth(self) -> bool:
        """Check if authentication is required."""
        return self._config["security"]["require_auth"]
    
    @property
    def auth_keys(self) -> List[str]:
        """Get authentication API keys."""
        return self._config["security"]["api_keys"]
    
    def get_config_dict(self) -> Dict[str, Any]:
        """Get the full configuration as a dictionary."""
        return self._config
