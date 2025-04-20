# Modified strategies.py
import os
import time
import traceback  # Keep traceback
from abc import ABC, abstractmethod
from typing import Dict, Optional

import google.generativeai as genai

from .data_models import GenerationConfig, ModelConfig, ModelResponse
from .key_rotation import KeyRotationManager
from .proxy import ProxyManager  # Keep import for reporting
from .response_handler import ResponseHandler


class ContentStrategy(ABC):
    """Abstract base class for content generation strategies."""
    def __init__(
        self,
        config: ModelConfig,
        key_manager: KeyRotationManager,
        system_instruction: Optional[str] = None,
        generation_config: Optional[GenerationConfig] = None,
        proxy_settings: Optional[Dict[str, str]] = None # Keep for config info
    ):
        self.config = config
        self.key_manager = key_manager
        self.system_instruction = system_instruction
        self.generation_config = generation_config or GenerationConfig()
        self.proxy_settings = proxy_settings # Store original settings if needed

    @abstractmethod
    def generate(self, prompt: str, model_name: str) -> ModelResponse:
        """Generate content using the specific strategy."""
        pass

    def _try_generate(self, model_name: str, prompt: str, start_time: float) -> ModelResponse:
        """Helper method for generating content with key rotation. Assumes proxy environment is pre-configured."""
        api_key, key_index = self.key_manager.get_next_key()
        current_proxy_info_for_reporting = None # Initialize

        try:
            # --- Proxy Handling Removed ---
            # The proxy environment variables (HTTP_PROXY, HTTPS_PROXY)
            # are now expected to be set by the middleware before this method is called.
            # We only need to *get* the current proxy for reporting purposes later.
            print("Executing API call (proxy env vars should be pre-set by middleware)")

            # --- API Call ---
            print(f"Configuring genai with key index {key_index}...")
            # Configure API key globally. The genai library should automatically
            # pick up HTTP_PROXY/HTTPS_PROXY from the environment variables.
            genai.configure(api_key=api_key)

            gen_config = self.generation_config.to_dict()

            # Create model instance WITHOUT client_options
            model = genai.GenerativeModel(
                model_name=model_name,
                generation_config=gen_config,
                system_instruction=self.system_instruction
                # No client_options needed; relies on env vars
            )

            print(f"Making API call with model {model_name}...")
            response = model.generate_content(prompt)
            print("API call finished.")

            # --- Process Response ---
            # Get the proxy info *after* the call for accurate reporting
            current_proxy_info_for_reporting = ProxyManager.get_current_proxy()

            result = ResponseHandler.process_response(
                response,
                model_name,
                start_time,
                key_index,
                self.generation_config.response_mime_type,
                proxy_info=current_proxy_info_for_reporting # Pass proxy info directly
            )

            # Mark key status based on result
            if result.success:
                self.key_manager.mark_success(key_index)
            else:
                 # Only mark as generic failure if not rate limited (rate limit handled below)
                 if "Rate limit" not in result.error and "429" not in result.error:
                      self.key_manager.mark_failure(key_index)

            return result

        except Exception as e:
            # Log the exception traceback for detailed debugging
            print(f"Error during API call or processing for key index {key_index}:")
            traceback.print_exc()

            # Get the proxy info even on exception for reporting
            current_proxy_info_for_reporting = ProxyManager.get_current_proxy()
            proxy_string_for_error = current_proxy_info_for_reporting.get('proxy_string', 'N/A') if current_proxy_info_for_reporting else 'None'


            # Handle specific errors and mark key status
            error_msg = f"Unhandled Exception (Key Index {key_index}, Proxy: {proxy_string_for_error}). Details: {str(e)}" # Default
            if "429" in str(e) or "rate limit" in str(e).lower():
                self.key_manager.mark_rate_limited(key_index)
                error_msg = f"Rate limit exceeded (Key Index {key_index}, Proxy: {proxy_string_for_error}). Details: {str(e)}"
            elif "API key not valid" in str(e) or "permission denied" in str(e).lower() or "authentication" in str(e).lower():
                 self.key_manager.mark_failure(key_index) # Mark as failed, maybe permanent
                 error_msg = f"Authentication/Permission Error (Key Index {key_index}, Proxy: {proxy_string_for_error}). Check API key validity/permissions. Details: {str(e)}"
            elif "proxy" in str(e).lower() or "connection" in str(e).lower() or "timeout" in str(e).lower():
                 # More general connection/proxy error handling
                 self.key_manager.mark_failure(key_index) # Treat proxy/connection errors as failures for the key
                 error_msg = f"Connection/Proxy Error (Key Index {key_index}, Proxy: {proxy_string_for_error}). Details: {str(e)}"
            else:
                # Generic failure for other exceptions
                self.key_manager.mark_failure(key_index)
                # error_msg is already set to the default


            return ModelResponse(
                success=False,
                model=model_name,
                error=error_msg,
                time=time.time() - start_time,
                api_key_index=key_index,
                proxy_info=current_proxy_info_for_reporting # Include proxy info in error
            )

# --- No changes needed in RoundRobinStrategy, FallbackStrategy, RetryStrategy ---
# They all call the updated _try_generate method above.

class RoundRobinStrategy(ContentStrategy):
    """Round robin implementation of content generation."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._current_index = 0

    def _get_next_model(self) -> str:
        """Get next model in round-robin fashion."""
        if not self.config.models:
             raise ValueError("No models configured for RoundRobinStrategy.")
        model = self.config.models[self._current_index]
        self._current_index = (self._current_index + 1) % len(self.config.models)
        return model

    def generate(self, prompt: str, _: str) -> ModelResponse: # Model name arg ignored
        start_time = time.time()

        if not self.config.models:
            return ModelResponse(
                success=False,
                model='no_models_configured',
                error='No models available in configuration for RoundRobinStrategy.',
                time=time.time() - start_time
            )

        initial_model_index = self._current_index
        last_error = "No models attempted."
        first_failing_result = None # Store the first failure for better error reporting

        for i in range(len(self.config.models)):
            model_name = self._get_next_model()
            print(f"[RoundRobin] Attempting model: {model_name}")
            result = self._try_generate(model_name, prompt, start_time)
            last_error = result.error # Update last error

            if result.success or 'Copyright' in result.error:
                print(f"[RoundRobin] Success or non-retryable error with {model_name}.")
                return result
            else:
                 print(f"[RoundRobin] Failed with {model_name}: {result.error}")
                 if first_failing_result is None:
                      first_failing_result = result # Keep the first failure details

            # This check might be redundant if _get_next_model works correctly, but safe to keep
            if i > 0 and self._current_index == initial_model_index:
                 print("[RoundRobin] Cycled through all models.")
                 break


        print("[RoundRobin] All models failed.")
        # Return the first failing result if available, otherwise a generic message
        if first_failing_result:
             # Update model field and error message of the first failure
             first_model_name = first_failing_result.model
             first_failing_result.model = 'all_models_failed'
             first_failing_result.error = f'All models failed. First error ({first_model_name}): {first_failing_result.error}'
             return first_failing_result
        else:
             # Should only happen if the models list was empty initially (already checked)
             # or if _try_generate somehow didn't return a ModelResponse (unlikely)
             return ModelResponse(
                success=False,
                model='all_models_failed',
                error=f'All models failed. Last error: {last_error}', # Use last_error as fallback
                time=time.time() - start_time
             )


class FallbackStrategy(ContentStrategy):
    """Fallback implementation of content generation."""
    def generate(self, prompt: str, start_model: str) -> ModelResponse:
        start_time = time.time()

        try:
            start_index = self.config.models.index(start_model)
        except ValueError:
            print(f"Warning: Start model '{start_model}' not found in config. Defaulting to first model.")
            if not self.config.models:
                 return ModelResponse(success=False, model=start_model, error="No models configured.", time=time.time()-start_time)
            start_index = 0
            start_model = self.config.models[0]

        last_error = "No models attempted."
        first_failing_result = None

        for model_name in self.config.models[start_index:]:
            print(f"[Fallback] Attempting model: {model_name}")
            result = self._try_generate(model_name, prompt, start_time)
            last_error = result.error

            if result.success or 'Copyright' in result.error:
                print(f"[Fallback] Success or non-retryable error with {model_name}.")
                return result
            else:
                 print(f"[Fallback] Failed with {model_name}: {result.error}")
                 if first_failing_result is None:
                      first_failing_result = result

        print("[Fallback] All models failed.")
        if first_failing_result:
             first_model_name = first_failing_result.model
             first_failing_result.model = 'all_models_failed'
             first_failing_result.error = f'All models failed starting from {start_model}. First error ({first_model_name}): {first_failing_result.error}'
             return first_failing_result
        else:
             return ModelResponse(
                success=False,
                model='all_models_failed',
                error=f'All models failed starting from {start_model}. Last error: {last_error}',
                time=time.time() - start_time
             )


class RetryStrategy(ContentStrategy):
    """Retry implementation of content generation."""
    def generate(self, prompt: str, model_name: str) -> ModelResponse:
        start_time = time.time()
        last_result = None

        if model_name not in self.config.models:
             # Try to find the default model if the requested one isn't listed
             default_model = self.config.default_model
             print(f"Warning: Model '{model_name}' not found in config. Attempting default model '{default_model}'.")
             if default_model not in self.config.models:
                  # If even the default isn't found (config issue)
                  return ModelResponse(
                      success=False,
                      model=model_name,
                      error=f"Model '{model_name}' not found in configuration, and default model '{default_model}' is also missing.",
                      time=time.time() - start_time,
                      attempts=0
                  )
             model_name = default_model # Use the default model instead


        for attempt in range(self.config.max_retries):
            print(f"[Retry] Attempt {attempt + 1}/{self.config.max_retries} for model: {model_name}")
            result = self._try_generate(model_name, prompt, start_time)
            result.attempts = attempt + 1
            last_result = result # Store the latest result

            # Check for success or non-retryable errors
            if result.success or 'Copyright' in result.error or 'Authentication/Permission Error' in result.error:
                print(f"[Retry] Success or non-retryable error on attempt {attempt + 1}.")
                return result # Return immediately

            # If failed and more retries left, wait and continue
            if attempt < self.config.max_retries - 1:
                print(f"[Retry] Error encountered: {result.error}. Waiting {self.config.retry_delay}s...")
                time.sleep(self.config.retry_delay)
            else:
                 # This is the last attempt, loop will end
                 print(f"[Retry] Max retries exceeded for {model_name}.")

        # If loop finished without returning, it means all retries failed
        if last_result:
             # Ensure the final result indicates failure and aggregates info
             last_result.success = False
             last_result.error = f"Max retries ({self.config.max_retries}) exceeded for model '{model_name}'. Last error: {last_result.error}"
             return last_result
        else:
             # Should not happen if max_retries >= 1, but as a safeguard
             return ModelResponse(
                success=False,
                model=model_name,
                error=f'Max retries ({self.config.max_retries}) exceeded for model {model_name} (no attempts recorded).',
                time=time.time() - start_time,
                attempts=self.config.max_retries
             )