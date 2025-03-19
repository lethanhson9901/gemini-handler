from abc import ABC, abstractmethod
import google.generativeai as genai
import time
import os
import yaml
from typing import List, Dict, Any, Optional, Tuple, Union
from enum import Enum
from dataclasses import dataclass
from itertools import cycle
from pathlib import Path

@dataclass
class GenerationConfig:
    """Configuration for model generation parameters."""
    temperature: float = 1.0
    top_p: float = 1.0
    top_k: int = 40
    max_output_tokens: int = 8192
    stop_sequences: Optional[List[str]] = None
    response_mime_type: str = "text/plain"

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary, excluding None values."""
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class ModelResponse:
    """Represents a standardized response from any model."""
    success: bool
    model: str
    text: str = ""
    error: str = ""
    time: float = 0.0
    attempts: int = 1
    api_key_index: int = 0


class Strategy(Enum):
    """Available content generation strategies."""
    ROUND_ROBIN = "round_robin"
    FALLBACK = "fallback"
    RETRY = "retry"


class KeyRotationStrategy(Enum):
    """Available key rotation strategies."""
    SEQUENTIAL = "sequential"
    ROUND_ROBIN = "round_robin"
    LEAST_USED = "least_used"
    SMART_COOLDOWN = "smart_cooldown"


@dataclass
class KeyStats:
    """Track usage statistics for each API key."""
    uses: int = 0
    last_used: float = 0
    failures: int = 0
    rate_limited_until: float = 0


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


class ModelConfig:
    """Configuration for model settings."""
    def __init__(self):
        self.models = [
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-2.0-pro-exp-02-05",
            "gemini-1.5-flash",
            "gemini-1.5-flash-8b",
            "gemini-1.5-pro"
            "gemini-1.5-pro",
            "gemini-embedding-exp",
            "imagen-3.0-generate-002",
            "gemini-2.0-flash-thinking-exp-01-21",
            "gemini-exp-1206",            
        ]
        self.max_retries = 3
        self.retry_delay = 30
        self.default_model = "gemini-2.0-flash-exp"


class KeyRotationManager:
    """Enhanced key rotation manager with multiple strategies."""
    def __init__(
        self,
        api_keys: List[str],
        strategy: KeyRotationStrategy = KeyRotationStrategy.ROUND_ROBIN,
        rate_limit: int = 60,
        reset_window: int = 60
    ):
        if not api_keys:
            raise ValueError("At least one API key must be provided")
        
        self.api_keys = api_keys
        self.strategy = strategy
        self.rate_limit = rate_limit
        self.reset_window = reset_window
        
        # Initialize tracking
        self.key_stats = {i: KeyStats() for i in range(len(api_keys))}
        self._key_cycle = cycle(range(len(api_keys)))
        self.current_index = 0

    def _is_key_available(self, key_index: int) -> bool:
        """Check if a key is available based on rate limits and cooldown."""
        stats = self.key_stats[key_index]
        current_time = time.time()
        
        if current_time < stats.rate_limited_until:
            return False
            
        if current_time - stats.last_used > self.reset_window:
            stats.uses = 0
            
        return stats.uses < self.rate_limit

    def _get_sequential_key(self) -> Tuple[str, int]:
        """Get next key using sequential strategy."""
        start_index = self.current_index
        
        while True:
            if self._is_key_available(self.current_index):
                key_index = self.current_index
                self.current_index = (self.current_index + 1) % len(self.api_keys)
                return self.api_keys[key_index], key_index
                
            self.current_index = (self.current_index + 1) % len(self.api_keys)
            if self.current_index == start_index:
                self._handle_all_keys_busy()

    def _get_round_robin_key(self) -> Tuple[str, int]:
        """Get next key using round-robin strategy."""
        start_index = next(self._key_cycle)
        current_index = start_index
        
        while True:
            if self._is_key_available(current_index):
                return self.api_keys[current_index], current_index
                
            current_index = next(self._key_cycle)
            if current_index == start_index:
                self._handle_all_keys_busy()

    def _get_least_used_key(self) -> Tuple[str, int]:
        """Get key with lowest usage count."""
        while True:
            available_keys = [
                (idx, stats) for idx, stats in self.key_stats.items()
                if self._is_key_available(idx)
            ]
            
            if available_keys:
                key_index, _ = min(available_keys, key=lambda x: x[1].uses)
                return self.api_keys[key_index], key_index
                
            self._handle_all_keys_busy()

    def _get_smart_cooldown_key(self) -> Tuple[str, int]:
        """Get key using smart cooldown strategy."""
        while True:
            current_time = time.time()
            available_keys = [
                (idx, stats) for idx, stats in self.key_stats.items()
                if current_time >= stats.rate_limited_until and self._is_key_available(idx)
            ]
            
            if available_keys:
                key_index, _ = min(
                    available_keys,
                    key=lambda x: (x[1].failures, -(current_time - x[1].last_used))
                )
                return self.api_keys[key_index], key_index
                
            self._handle_all_keys_busy()

    def _handle_all_keys_busy(self) -> None:
        """Handle situation when all keys are busy."""
        current_time = time.time()
        any_reset = False
        
        for idx, stats in self.key_stats.items():
            if current_time - stats.last_used > self.reset_window:
                stats.uses = 0
                any_reset = True
                
        if not any_reset:
            time.sleep(1)

    def get_next_key(self) -> Tuple[str, int]:
        """Get next available API key based on selected strategy."""
        strategy_methods = {
            KeyRotationStrategy.SEQUENTIAL: self._get_sequential_key,
            KeyRotationStrategy.ROUND_ROBIN: self._get_round_robin_key,
            KeyRotationStrategy.LEAST_USED: self._get_least_used_key,
            KeyRotationStrategy.SMART_COOLDOWN: self._get_smart_cooldown_key
        }
        
        method = strategy_methods.get(self.strategy)
        if not method:
            raise ValueError(f"Unknown strategy: {self.strategy}")
            
        api_key, key_index = method()
        
        stats = self.key_stats[key_index]
        stats.uses += 1
        stats.last_used = time.time()
        
        return api_key, key_index

    def mark_success(self, key_index: int) -> None:
        """Mark successful API call."""
        if 0 <= key_index < len(self.api_keys):
            self.key_stats[key_index].failures = 0

    def mark_rate_limited(self, key_index: int) -> None:
        """Mark API key as rate limited."""
        if 0 <= key_index < len(self.api_keys):
            stats = self.key_stats[key_index]
            stats.failures += 1
            stats.rate_limited_until = time.time() + self.reset_window
            stats.uses = self.rate_limit


class ResponseHandler:
    """Handles and processes model responses."""
    @staticmethod
    def process_response(
        response: Any,
        model_name: str,
        start_time: float,
        key_index: int
    ) -> ModelResponse:
        """Process and validate model response."""
        try:
            if hasattr(response, 'candidates') and response.candidates:
                finish_reason = response.candidates[0].finish_reason
                if finish_reason == 4:  # Copyright material
                    return ModelResponse(
                        success=False,
                        model=model_name,
                        error='Copyright material detected in response',
                        time=time.time() - start_time,
                        api_key_index=key_index
                    )
            
            return ModelResponse(
                success=True,
                model=model_name,
                text=response.text,
                time=time.time() - start_time,
                api_key_index=key_index
            )
        except Exception as e:
            if "The `response.text` quick accessor requires the response to contain a valid `Part`" in str(e):
                return ModelResponse(
                    success=False,
                    model=model_name,
                    error='No valid response parts available',
                    time=time.time() - start_time,
                    api_key_index=key_index
                )
            raise


class ContentStrategy(ABC):
    """Abstract base class for content generation strategies."""
    def __init__(
        self,
        config: ModelConfig,
        key_manager: KeyRotationManager,
        system_instruction: Optional[str] = None,
        generation_config: Optional[GenerationConfig] = None
    ):
        self.config = config
        self.key_manager = key_manager
        self.system_instruction = system_instruction
        self.generation_config = generation_config or GenerationConfig()

    @abstractmethod
    def generate(self, prompt: str, model_name: str) -> ModelResponse:
        """Generate content using the specific strategy."""
        pass

    def _try_generate(self, model_name: str, prompt: str, start_time: float) -> ModelResponse:
        """Helper method for generating content with key rotation."""
        api_key, key_index = self.key_manager.get_next_key()
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(
                model_name=model_name,
                generation_config=self.generation_config.to_dict(),
                system_instruction=self.system_instruction
            )
            response = model.generate_content(prompt)
            
            result = ResponseHandler.process_response(response, model_name, start_time, key_index)
            if result.success:
                self.key_manager.mark_success(key_index)
            return result
            
        except Exception as e:
            if "429" in str(e):
                self.key_manager.mark_rate_limited(key_index)
            return ModelResponse(
                success=False,
                model=model_name,
                error=str(e),
                time=time.time() - start_time,
                api_key_index=key_index
            )


class RoundRobinStrategy(ContentStrategy):
    """Round robin implementation of content generation."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._current_index = 0

    def _get_next_model(self) -> str:
        """Get next model in round-robin fashion."""
        model = self.config.models[self._current_index]
        self._current_index = (self._current_index + 1) % len(self.config.models)
        return model

    def generate(self, prompt: str, _: str) -> ModelResponse:
        start_time = time.time()
        
        for _ in range(len(self.config.models)):
            model_name = self._get_next_model()
            result = self._try_generate(model_name, prompt, start_time)
            if result.success or 'Copyright' in result.error:
                return result

        return ModelResponse(
            success=False,
            model='all_models_failed',
            error='All models failed (rate limited or copyright issues)',
            time=time.time() - start_time
        )


class FallbackStrategy(ContentStrategy):
    """Fallback implementation of content generation."""
    def generate(self, prompt: str, start_model: str) -> ModelResponse:
        start_time = time.time()
        
        try:
            start_index = self.config.models.index(start_model)
        except ValueError:
            return ModelResponse(
                success=False,
                model=start_model,
                error=f"Model {start_model} not found in available models",
                time=time.time() - start_time
            )

        for model_name in self.config.models[start_index:]:
            result = self._try_generate(model_name, prompt, start_time)
            if result.success or 'Copyright' in result.error:
                return result

        return ModelResponse(
            success=False,
            model='all_models_failed',
            error='All models failed (rate limited or copyright issues)',
            time=time.time() - start_time
        )


class RetryStrategy(ContentStrategy):
    """Retry implementation of content generation."""
    def generate(self, prompt: str, model_name: str) -> ModelResponse:
        start_time = time.time()
        
        for attempt in range(self.config.max_retries):
            result = self._try_generate(model_name, prompt, start_time)
            result.attempts = attempt + 1
            
            if result.success or 'Copyright' in result.error:
                return result
                
            if attempt < self.config.max_retries - 1:
                print(f"Error encountered. Waiting {self.config.retry_delay}s... "
                      f"(Attempt {attempt + 1}/{self.config.max_retries})")
                time.sleep(self.config.retry_delay)
        
        return ModelResponse(
            success=False,
            model=model_name,
            error='Max retries exceeded',
            time=time.time() - start_time,
            attempts=self.config.max_retries
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
        self.generation_config = generation_config
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
