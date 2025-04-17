# Modified gemini_handler.py
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import google.generativeai as genai
from google import genai as google_genai

from .config import ConfigLoader
from .content_generation import ContentGenerationMixin
from .data_models import (
    EmbeddingConfig,
    GenerationConfig,
    KeyRotationStrategy,
    ModelConfig,
    Strategy,
)
from .embedding import EmbeddingHandler
from .file_handler import FileHandler
from .file_operations import FileOperationsMixin
from .key_rotation import KeyRotationManager
from .proxy import ProxyManager
from .strategies import (
    ContentStrategy,
    FallbackStrategy,
    RetryStrategy,
    RoundRobinStrategy,
)

# Define sentinel object to detect when parameter is not provided
_SENTINEL = object()

class GeminiHandler(ContentGenerationMixin, FileOperationsMixin):
    """Main handler class for Gemini API interactions."""
    
    def __init__(
        self,
        api_keys: Optional[List[str]] = None,
        config_path: Optional[Union[str, Path]] = None,
        content_strategy: Strategy = Strategy.ROUND_ROBIN,
        key_strategy: KeyRotationStrategy = KeyRotationStrategy.ROUND_ROBIN,
        system_instruction: Optional[str] = None,
        generation_config: Optional[GenerationConfig] = None,
        proxy_settings: Any = _SENTINEL  # Use sentinel to detect if provided
    ):
        """
        Initialize GeminiHandler with flexible configuration options.

        Args:
            api_keys: List of API keys (optional, can be loaded from config_path)
            config_path: Path to configuration file (optional)
            content_strategy: Strategy for content generation
            key_strategy: Strategy for API key rotation
            system_instruction: System instruction for models
            generation_config: Configuration for generation parameters
            proxy_settings: Explicit proxy settings dictionary:
                            - If provided (even {}, or explicitly None), this value is used directly
                            - If not provided, may be loaded from config_path if available
        """
        # Load API keys first
        self.api_keys = api_keys or ConfigLoader.load_api_keys(config_path)

        # --- Simple and clear proxy settings logic ---
        if proxy_settings is not _SENTINEL:
            # Case: Parameter was explicitly provided - use it exactly as given
            self.proxy_settings = proxy_settings
            print(f"Proxy settings explicitly provided: {proxy_settings}")
        elif config_path:
            # Case: Parameter not provided, try loading from config
            try:
                self.proxy_settings = ConfigLoader.load_proxy_settings(config_path)
                if self.proxy_settings:
                    print(f"Loaded proxy settings from config: {self.proxy_settings}")
                else:
                    print("No proxy settings found in config file.")
                    self.proxy_settings = None
            except Exception as e:
                print(f"Error loading proxy settings from config: {e}")
                self.proxy_settings = None
        else:
            # Case: No sources for proxy settings
            self.proxy_settings = None
            print("No proxy settings sources available.")

        # Apply proxy configuration if we have valid settings
        if self.proxy_settings:
            print(f"Configuring ProxyManager with: {self.proxy_settings}")
            ProxyManager.configure_proxy(self.proxy_settings)
        else:
            print("No proxy configuration applied.")
            # Optionally clear environment variables to ensure no proxy is used
            import os
            os.environ.pop('HTTP_PROXY', None)
            os.environ.pop('HTTPS_PROXY', None)

        # Initialize other components
        self.config = ModelConfig()
        self.system_instruction = system_instruction
        self.generation_config = generation_config or GenerationConfig()
        
        # Initialize key rotation manager
        self.key_manager = KeyRotationManager(
            api_keys=self.api_keys,
            strategy=key_strategy
        )
        
        # Initialize embedding handler
        self.embedding_handler = EmbeddingHandler(
            key_manager=self.key_manager,
            proxy_settings=self.proxy_settings
        )
        
        # Initialize client for file operations
        api_key, _ = self.key_manager.get_next_key()
        self.client = google_genai.Client(api_key=api_key)
        
        # Create file handler
        self.file_handler = FileHandler(client=self.client)
        
        # Create strategy
        self._strategy = self._create_strategy(content_strategy)

    def _create_strategy(self, strategy: Strategy) -> ContentStrategy:
        """Factory method to create appropriate strategy."""
        strategies = {
            Strategy.ROUND_ROBIN: RoundRobinStrategy,
            Strategy.FALLBACK: FallbackStrategy,
            Strategy.RETRY: RetryStrategy
        }
        
        strategy_class = strategies.get(strategy)
        if not strategy_class:
            raise ValueError(f"Unknown strategy: {strategy}")
            
        return strategy_class(
            config=self.config,
            key_manager=self.key_manager,
            system_instruction=self.system_instruction,
            generation_config=self.generation_config,
            proxy_settings=self.proxy_settings
        )

    def get_key_stats(self, key_index: Optional[int] = None) -> Dict[int, Dict[str, Any]]:
        """
        Get current key usage statistics.
        
        Args:
            key_index: Optional specific key index to get stats for
            
        Returns:
            Dictionary of key statistics
        """
        if key_index is not None:
            if 0 <= key_index < len(self.key_manager.api_keys):
                stats = self.key_manager.key_stats[key_index]
                return {
                    key_index: {
                        "uses": stats.uses,
                        "last_used": stats.last_used,
                        "failures": stats.failures,
                        "rate_limited_until": stats.rate_limited_until
                    }
                }
            raise ValueError(f"Invalid key index: {key_index}")
        
        return {
            idx: {
                "uses": stats.uses,
                "last_used": stats.last_used,
                "failures": stats.failures,
                "rate_limited_until": stats.rate_limited_until
            }
            for idx, stats in self.key_manager.key_stats.items()
        }
