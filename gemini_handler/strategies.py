# Modified strategies.py
import time
from abc import ABC, abstractmethod
from typing import Dict, Optional

import google.generativeai as genai

from .data_models import GenerationConfig, ModelConfig, ModelResponse
from .key_rotation import KeyRotationManager
from .proxy import ProxyManager
from .response_handler import ResponseHandler


class ContentStrategy(ABC):
    """Abstract base class for content generation strategies."""
    def __init__(
        self,
        config: ModelConfig,
        key_manager: KeyRotationManager,
        system_instruction: Optional[str] = None,
        generation_config: Optional[GenerationConfig] = None,
        proxy_settings: Optional[Dict[str, str]] = None
    ):
        self.config = config
        self.key_manager = key_manager
        self.system_instruction = system_instruction
        self.generation_config = generation_config or GenerationConfig()
        self.proxy_settings = proxy_settings

    @abstractmethod
    def generate(self, prompt: str, model_name: str) -> ModelResponse:
        """Generate content using the specific strategy."""
        pass

    def _try_generate(self, model_name: str, prompt: str, start_time: float) -> ModelResponse:
        """Helper method for generating content with key rotation."""
        api_key, key_index = self.key_manager.get_next_key()
        try:
            # Configure with API key
            if self.proxy_settings:
                # When proxy settings are provided, we need to configure them for this call
                ProxyManager.configure_proxy(self.proxy_settings)
                
            genai.configure(api_key=api_key)
            gen_config = self.generation_config.to_dict()
            
            model = genai.GenerativeModel(
                model_name=model_name,
                generation_config=gen_config,
                system_instruction=self.system_instruction
            )
            
            response = model.generate_content(prompt)
            
            result = ResponseHandler.process_response(
                response, 
                model_name, 
                start_time, 
                key_index,
                self.generation_config.response_mime_type
            )
            
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
