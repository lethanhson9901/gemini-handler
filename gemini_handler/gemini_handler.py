from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import google.generativeai as genai

from .config import ConfigLoader
from .data_models import (
    EmbeddingConfig,
    GenerationConfig,
    KeyRotationStrategy,
    ModelConfig,
    Strategy,
)
from .embedding import EmbeddingHandler
from .key_rotation import KeyRotationManager
from .strategies import (
    ContentStrategy,
    FallbackStrategy,
    RetryStrategy,
    RoundRobinStrategy,
)


class GeminiHandler:
    """Main handler class for Gemini API interactions."""
    def __init__(
        self,
        api_keys: Optional[List[str]] = None,
        config_path: Optional[Union[str, Path]] = None,
        content_strategy: Strategy = Strategy.ROUND_ROBIN,
        key_strategy: KeyRotationStrategy = KeyRotationStrategy.ROUND_ROBIN,
        system_instruction: Optional[str] = None,
        generation_config: Optional[GenerationConfig] = None
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
        """
        # Load API keys from provided list or config sources
        self.api_keys = api_keys or ConfigLoader.load_api_keys(config_path)
        
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
        self.embedding_handler = EmbeddingHandler(self.key_manager)

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
            generation_config=self.generation_config
        )

    def generate_content(
        self,
        prompt: str,
        model_name: Optional[str] = None,
        return_stats: bool = False
    ) -> Dict[str, Any]:
        """
        Generate content using the selected strategies.
        
        Args:
            prompt: The input prompt for content generation
            model_name: Optional specific model to use (default: None)
            return_stats: Whether to include key usage statistics (default: False)
            
        Returns:
            Dictionary containing generation results and optionally key statistics
        """
        if not model_name:
            model_name = self.config.default_model
            
        response = self._strategy.generate(prompt, model_name)
        result = response.__dict__
        
        if return_stats:
            result["key_stats"] = {
                idx: {
                    "uses": stats.uses,
                    "last_used": stats.last_used,
                    "failures": stats.failures,
                    "rate_limited_until": stats.rate_limited_until
                }
                for idx, stats in self.key_manager.key_stats.items()
            }
            
        return result

    def generate_structured_content(
        self,
        prompt: str,
        schema: Dict[str, Any],
        model_name: Optional[str] = None,
        return_stats: bool = False,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        max_output_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate structured content according to the provided schema.
        
        Args:
            prompt: The input prompt for content generation
            schema: JSON schema that defines the structure of the response
            model_name: Optional specific model to use (default: None)
            return_stats: Whether to include key usage statistics (default: False)
            temperature: Optional temperature to override default
            top_p: Optional top_p to override default
            top_k: Optional top_k to override default
            max_output_tokens: Optional max_output_tokens to override default
            
        Returns:
            Dictionary containing generation results and optionally key statistics
        """
        # Create a structured generation config based on current config
        original_config = self.generation_config
        
        # Create new config with structured output settings
        structured_config = GenerationConfig(
            temperature=temperature if temperature is not None else original_config.temperature,
            top_p=top_p if top_p is not None else original_config.top_p,
            top_k=top_k if top_k is not None else original_config.top_k,
            max_output_tokens=max_output_tokens if max_output_tokens is not None else original_config.max_output_tokens,
            stop_sequences=original_config.stop_sequences,
            response_mime_type="application/json",
            response_schema=schema
        )
        
        # Update the strategy with the new config
        self._strategy.generation_config = structured_config
        
        try:
            # Generate the content
            result = self.generate_content(prompt, model_name, return_stats)
            return result
        finally:
            # Restore the original config
            self._strategy.generation_config = original_config

    def generate_embeddings(
        self,
        content: Union[str, List[str]],
        model_name: Optional[str] = None,
        task_type: Optional[str] = None,
        return_stats: bool = False
    ) -> Dict[str, Any]:
        """
        Generate embeddings for the provided content.
        
        Args:
            content: Text content to embed (string or list of strings)
            model_name: Embedding model to use (default: gemini-embedding-exp-03-07)
            task_type: Optional task type for specialized embeddings
            return_stats: Whether to include key usage statistics
            
        Returns:
            Dictionary containing embeddings or error information
        """
        if not model_name:
            model_name = self.config.default_embedding_model
            
        response = self.embedding_handler.generate_embeddings(
            content=content,
            model_name=model_name,
            task_type=task_type
        )
        
        result = response.__dict__
        
        if return_stats:
            result["key_stats"] = {
                idx: {
                    "uses": stats.uses,
                    "last_used": stats.last_used,
                    "failures": stats.failures,
                    "rate_limited_until": stats.rate_limited_until
                }
                for idx, stats in self.key_manager.key_stats.items()
            }
            
        return result

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
