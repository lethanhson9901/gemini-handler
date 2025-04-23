# gemini_handler/litellm_provider.py

import litellm
from litellm.llms.custom_llm import CustomLLM
from litellm.utils import ModelResponse, EmbeddingResponse, Usage, Choices, Message
from typing import Optional, List, Union, Dict, Any, Mapping
import time
import traceback
import json

# Import necessary components from your gemini_handler
from .gemini_handler import GeminiHandler
from .data_models import GenerationConfig, ModelResponse as GeminiModelResponse
from .config import ConfigLoader # To potentially load config if needed

class GeminiHandlerLiteLLM(CustomLLM):
    """
    LiteLLM Custom Provider for gemini-handler library.

    Leverages gemini-handler's key rotation, strategies, proxy,
    and file handling capabilities.
    """
    handler_instance: GeminiHandler = None # Class variable to hold the handler

    def __init__(self):
        """
        Initializes the provider.
        Requires GeminiHandlerLiteLLM.initialize() to be called separately
        before making API calls to set up the handler instance.
        """
        if GeminiHandlerLiteLLM.handler_instance is None:
            # Warn or raise error if not initialized
            # For now, we assume initialize() will be called externally
            print("Warning: GeminiHandlerLiteLLM not initialized. Call GeminiHandlerLiteLLM.initialize() before use.")
            pass

    @classmethod
    def initialize(cls, handler_instance: Optional[GeminiHandler] = None, **kwargs):
        """
        Initializes the underlying GeminiHandler.

        Can accept a pre-configured GeminiHandler instance or kwargs to create one.

        Args:
            handler_instance: A pre-initialized GeminiHandler instance.
            **kwargs: Arguments to pass to the GeminiHandler constructor
                      (e.g., api_keys, config_path, content_strategy, etc.)
                      if handler_instance is not provided.
        """
        if handler_instance:
            cls.handler_instance = handler_instance
        elif kwargs:
            cls.handler_instance = GeminiHandler(**kwargs)
        else:
            # Try default initialization (e.g., from env vars or default config)
            try:
                cls.handler_instance = GeminiHandler()
            except Exception as e:
                 raise ValueError(f"Failed to initialize GeminiHandler. Provide either 'handler_instance' or configuration kwargs (e.g., 'config_path'). Error: {e}")

        if cls.handler_instance is None:
             raise ValueError("GeminiHandler instance could not be initialized.")
        print("GeminiHandlerLiteLLM initialized successfully.")


    def completion(self,
                   model: str,
                   messages: List[Dict[str, Any]],
                   # LiteLLM specific params
                   stream: bool = False,
                   logic: Optional[Dict[str, Any]] = None,
                   # Gemini specific params (passed via litellm)
                   temperature: Optional[float] = None,
                   top_p: Optional[float] = None,
                   top_k: Optional[int] = None,
                   max_tokens: Optional[int] = None,
                   stop: Optional[Union[str, List[str]]] = None,
                   response_format: Optional[Dict[str, Any]] = None, # For structured output
                   **kwargs) -> ModelResponse:
        """
        LiteLLM completion method implementation.

        Args:
            model (str): Model name (e.g., "custom_gemini/gemini-1.5-pro")
            messages (List[Dict]): List of message dictionaries
            stream (bool): Whether to stream responses (Not currently supported by gemini-handler)
            logic (Optional[Dict]): LiteLLM internal logic params (ignored)
            temperature (Optional[float]): Sampling temperature
            top_p (Optional[float]): Top-p sampling
            top_k (Optional[int]): Top-k sampling
            max_tokens (Optional[int]): Maximum output tokens
            stop (Optional[Union[str, List[str]]]): Stop sequences
            response_format (Optional[Dict]): For structured output (expects {"type": "json_object", "schema": {...}})
            **kwargs: Additional arguments (e.g., return_stats)

        Returns:
            litellm.utils.ModelResponse: Standardized LiteLLM response object.

        Raises:
            NotImplementedError: If streaming is requested.
            Exception: For API errors or configuration issues.
        """
        if self.handler_instance is None:
            raise RuntimeError("GeminiHandlerLiteLLM must be initialized before calling completion.")

        if stream:
            raise NotImplementedError("Streaming is not currently supported by the gemini-handler integration.")

        # --- Parameter Mapping ---
        # Extract actual model name
        actual_model_name = model.split('/')[-1] if '/' in model else model

        # Convert messages to a single prompt string (simple concatenation for now)
        # TODO: Improve this based on roles if needed
        prompt = "\n".join([msg.get("content", "") for msg in messages if isinstance(msg.get("content"), str)])
        # Handle potential vision content (basic check, no processing yet)
        has_vision_content = any(
            isinstance(part, dict) and part.get("type") == "image_url"
            for msg in messages
            for part in (msg.get("content") if isinstance(msg.get("content"), list) else [])
        )
        if has_vision_content:
             # For now, raise error. Future: Implement file handling bridge.
             raise NotImplementedError("Vision/Image input via LiteLLM messages is not yet supported by this gemini-handler integration. Use gemini-handler directly for vision tasks.")


        # Check for structured output request
        schema = None
        if response_format and response_format.get("type") == "json_object":
            schema = response_format.get("schema")
            if not schema or not isinstance(schema, dict):
                 raise ValueError("Invalid or missing 'schema' in response_format for json_object type.")

        # --- Call GeminiHandler ---
        start_time = time.time()
        gemini_response: Optional[GeminiModelResponse] = None
        try:
            # Use handler's config as base, override with LiteLLM params
            gen_config_overrides = {
                "temperature": temperature,
                "top_p": top_p,
                "top_k": top_k,
                "max_output_tokens": max_tokens,
                # Map 'stop' to 'stop_sequences'
                "stop_sequences": [stop] if isinstance(stop, str) else stop,
            }
            # Filter out None values
            gen_config_overrides = {k: v for k, v in gen_config_overrides.items() if v is not None}

            return_stats = kwargs.get("return_stats", False) # Pass through extra args

            if schema:
                # Call structured content generation
                result_dict = self.handler_instance.generate_structured_content(
                    prompt=prompt,
                    schema=schema,
                    model_name=actual_model_name,
                    return_stats=return_stats,
                    **gen_config_overrides # Pass overrides
                )
                # Convert dict back to GeminiModelResponse for consistent handling below
                gemini_response = GeminiModelResponse(**result_dict)

            else:
                 # Call standard content generation
                # Need to temporarily modify the handler's generation config for this call
                original_config = self.handler_instance.generation_config
                temp_config_dict = original_config.to_dict()
                temp_config_dict.update(gen_config_overrides)
                temp_config = GenerationConfig(**temp_config_dict)

                # Temporarily set the config on the strategy object
                # This is a bit hacky, ideally the generate method would take config overrides
                original_strategy_config = self.handler_instance._strategy.generation_config
                self.handler_instance._strategy.generation_config = temp_config
                try:
                    result_dict = self.handler_instance.generate_content(
                        prompt=prompt,
                        model_name=actual_model_name,
                        return_stats=return_stats
                    )
                    gemini_response = GeminiModelResponse(**result_dict)
                finally:
                    # Restore original config on the strategy
                    self.handler_instance._strategy.generation_config = original_strategy_config


        except Exception as e:
            end_time = time.time()
            error_str = f"GeminiHandlerLiteLLM Error: {str(e)}\nTraceback: {traceback.format_exc()}"
            # Map to LiteLLM exceptions if possible
            if "429" in str(e) or "rate limit" in str(e).lower():
                raise litellm.RateLimitError(message=error_str, llm_provider="custom_gemini", model=actual_model_name)
            elif "permission denied" in str(e).lower() or "invalid api key" in str(e).lower():
                raise litellm.AuthenticationError(message=error_str, llm_provider="custom_gemini", model=actual_model_name)
            # Add more specific error mapping if needed
            raise litellm.APIError(status_code=500, message=error_str, llm_provider="custom_gemini", model=actual_model_name)

        # --- Process Response ---
        if not gemini_response:
             raise litellm.APIError(status_code=500, message="GeminiHandler did not return a response.", llm_provider="custom_gemini", model=actual_model_name)

        if not gemini_response.success:
            error_msg = gemini_response.error or "Unknown error from GeminiHandler"
            # Map specific gemini-handler errors
            if "Copyright material" in error_msg:
                 raise litellm.ContentPolicyViolationError(message=error_msg, llm_provider="custom_gemini", model=gemini_response.model)
            elif "rate limit" in error_msg.lower() or "429" in error_msg:
                 raise litellm.RateLimitError(message=error_msg, llm_provider="custom_gemini", model=gemini_response.model)
            elif "invalid json" in error_msg.lower():
                 # This might happen if structured output failed parsing
                 raise litellm.APIResponseError(message=error_msg, llm_provider="custom_gemini", model=gemini_response.model)
            # General API Error
            raise litellm.APIError(status_code=500, message=error_msg, llm_provider="custom_gemini", model=gemini_response.model)

        # --- Build LiteLLM Response ---
        llm_response = ModelResponse(id=f"chatcmpl-{int(time.time())}") # Generate a simple ID
        llm_response.model = f"custom_gemini/{gemini_response.model}" # Include prefix
        llm_response._hidden_params["custom_llm_provider"] = "custom_gemini" # Identify provider

        # Create Choices structure
        choice = Choices(finish_reason="stop", index=0) # Assuming 'stop' for now
        message = Message()

        if gemini_response.structured_data:
            # Handle structured data - LiteLLM expects string content
            message.content = json.dumps(gemini_response.structured_data)
            # Indicate tool use/function call if LiteLLM standard emerges
            # For now, just put JSON string in content
        elif gemini_response.text:
            message.content = gemini_response.text
        else:
             message.content = "" # Should not happen if success is True

        message.role = "assistant"
        choice.message = message
        llm_response.choices = [choice]

        # Add usage info - Gemini API often doesn't return tokens directly
        # We can estimate or leave it as 0 for now.
        llm_response.usage = Usage(prompt_tokens=0, completion_tokens=0, total_tokens=0)

        # Pass through extra info from gemini-handler if available
        llm_response._hidden_params["gemini_handler_response_time"] = gemini_response.time
        llm_response._hidden_params["gemini_handler_api_key_index"] = gemini_response.api_key_index
        if hasattr(gemini_response, "attempts"):
             llm_response._hidden_params["gemini_handler_attempts"] = gemini_response.attempts
        if hasattr(gemini_response, "key_stats") and gemini_response.key_stats:
             llm_response._hidden_params["gemini_handler_key_stats"] = gemini_response.key_stats

        return llm_response


    def embedding(self,
                  model: str,
                  input: List[str],
                  # LiteLLM specific params
                  logic: Optional[Dict[str, Any]] = None,
                  # Gemini specific params (passed via litellm)
                  task_type: Optional[str] = None,
                  **kwargs) -> EmbeddingResponse:
        """
        LiteLLM embedding method implementation.

        Args:
            model (str): Embedding model name (e.g., "custom_gemini/gemini-embedding-exp-03-07")
            input (List[str]): List of texts to embed.
            logic (Optional[Dict]): LiteLLM internal logic params (ignored)
            task_type (Optional[str]): Gemini task type for embeddings.
            **kwargs: Additional arguments (e.g., return_stats)

        Returns:
            litellm.utils.EmbeddingResponse: Standardized LiteLLM response object.

        Raises:
            Exception: For API errors or configuration issues.
        """
        if self.handler_instance is None:
            raise RuntimeError("GeminiHandlerLiteLLM must be initialized before calling embedding.")

        # --- Parameter Mapping ---
        actual_model_name = model.split('/')[-1] if '/' in model else model
        return_stats = kwargs.get("return_stats", False)

        # --- Call GeminiHandler ---
        start_time = time.time()
        gemini_response: Optional[GeminiModelResponse] = None
        try:
            result_dict = self.handler_instance.generate_embeddings(
                content=input,
                model_name=actual_model_name,
                task_type=task_type,
                return_stats=return_stats
            )
            gemini_response = GeminiModelResponse(**result_dict)

        except Exception as e:
            end_time = time.time()
            error_str = f"GeminiHandlerLiteLLM Embedding Error: {str(e)}\nTraceback: {traceback.format_exc()}"
            if "429" in str(e) or "rate limit" in str(e).lower():
                raise litellm.RateLimitError(message=error_str, llm_provider="custom_gemini", model=actual_model_name)
            elif "permission denied" in str(e).lower() or "invalid api key" in str(e).lower():
                raise litellm.AuthenticationError(message=error_str, llm_provider="custom_gemini", model=actual_model_name)
            raise litellm.APIError(status_code=500, message=error_str, llm_provider="custom_gemini", model=actual_model_name)

        # --- Process Response ---
        if not gemini_response:
             raise litellm.APIError(status_code=500, message="GeminiHandler did not return an embedding response.", llm_provider="custom_gemini", model=actual_model_name)

        if not gemini_response.success or not gemini_response.embeddings:
            error_msg = gemini_response.error or "Unknown embedding error from GeminiHandler"
            if "rate limit" in error_msg.lower() or "429" in error_msg:
                 raise litellm.RateLimitError(message=error_msg, llm_provider="custom_gemini", model=gemini_response.model)
            raise litellm.APIError(status_code=500, message=error_msg, llm_provider="custom_gemini", model=gemini_response.model)

        # --- Build LiteLLM Response ---
        response_data = []
        for i, embedding_list in enumerate(gemini_response.embeddings):
             # Ensure embedding_list is actually a list of floats
             if isinstance(embedding_list, Mapping) and 'values' in embedding_list:
                 # Handle potential google.ai.generativelanguage.ContentEmbedding structure
                 processed_embedding = embedding_list['values']
             elif isinstance(embedding_list, list):
                 processed_embedding = embedding_list
             else:
                 # Attempt conversion or raise error
                 try:
                     processed_embedding = list(embedding_list)
                 except TypeError:
                     raise litellm.APIResponseError(f"Unexpected embedding format received from gemini-handler: {type(embedding_list)}", llm_provider="custom_gemini", model=gemini_response.model)

             response_data.append({
                "object": "embedding",
                "index": i,
                "embedding": processed_embedding,
            })

        llm_response = EmbeddingResponse(
            model=f"custom_gemini/{gemini_response.model}",
            data=response_data,
        )
        # Add usage info (typically not provided for embeddings)
        llm_response.usage = Usage(prompt_tokens=0, total_tokens=0)

        # Pass through extra info
        llm_response._hidden_params["custom_llm_provider"] = "custom_gemini"
        llm_response._hidden_params["gemini_handler_response_time"] = gemini_response.time
        llm_response._hidden_params["gemini_handler_api_key_index"] = gemini_response.api_key_index
        if hasattr(gemini_response, "key_stats") and gemini_response.key_stats:
             llm_response._hidden_params["gemini_handler_key_stats"] = gemini_response.key_stats

        return llm_response

    # Optional: Add logging method
    def log(self, message: str):
        # Implement your preferred logging mechanism
        print(f"GeminiHandlerLiteLLM Log: {message}")

    # Optional: Health check
    def health_check(self):
        """Performs a basic health check."""
        if self.handler_instance is None:
            raise RuntimeError("Handler not initialized.")
        # Could potentially try a very simple, cheap API call if needed
        # For now, just check if the handler exists
        return {"status": "healthy"}