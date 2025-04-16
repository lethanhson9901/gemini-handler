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
        proxy_settings: Optional[Dict[str, str]] = None
    ):
        """
        Initialize GeminiHandler with flexible configuration options.
        
        Args:
            api_keys: Optional list of API keys
            config_path: Optional path to YAML config file
            content_strategy: Strategy for content generation
            key_strategy: Strategy for key rotation
            system_instruction: Optional system instruction
            generation_config: Optional generation configuration
            proxy_settings: Optional dictionary with proxy settings
        """
        # Load API keys from provided list or config sources
        self.api_keys = api_keys or ConfigLoader.load_api_keys(config_path)
        
        # Load proxy settings if not explicitly provided
        self.proxy_settings = proxy_settings
        if config_path and not proxy_settings:
            self.proxy_settings = ConfigLoader.load_proxy_settings(config_path)
            
        # Configure proxy if settings are provided
        if self.proxy_settings:
            ProxyManager.configure_proxy(self.proxy_settings)
            
        self.config = ModelConfig()
        self.key_manager = KeyRotationManager(
            api_keys=self.api_keys,
            strategy=key_strategy,
            rate_limit=60,
            reset_window=60
        )
        self.system_instruction = system_instruction
        self.generation_config = generation_config or GenerationConfig()
        self._strategy = self._create_strategy(content_strategy)
        self.embedding_handler = EmbeddingHandler(self.key_manager, proxy_settings=self.proxy_settings)
        
        # Initialize file handler with a client, configured with proxy if needed
        api_key, _ = self.key_manager.get_next_key()
        
        # Get client options if proxy is configured
        client_options = None
        if self.proxy_settings:
            client_options = ProxyManager.get_client_options(self.proxy_settings)
            
        # Initialize client with proxy settings if available
        if client_options:
            self.client = google_genai.Client(api_key=api_key, client_options=client_options)
        else:
            self.client = google_genai.Client(api_key=api_key)
            
        self.file_handler = FileHandler(self.client)

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
