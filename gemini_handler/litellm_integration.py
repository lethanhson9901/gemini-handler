# gemini_handler/litellm_integration.py

import os
import time
from typing import Any, Dict, List, Optional, Union

import google.generativeai as genai
from google import genai as google_genai

from .data_models import GenerationConfig, KeyRotationStrategy, ModelConfig, Strategy

# Import your existing components
from .gemini_handler import GeminiHandler
from .key_rotation import KeyRotationManager


class LiteLLMGeminiAdapter:
    """Adapter for using GeminiHandler with LiteLLM's custom provider interface."""
    
    # Class-level handler to reuse across requests and avoid re-initialization
    _handler_instance = None
    
    @classmethod
    def get_handler(cls, api_key: Optional[str] = None, api_keys: Optional[List[str]] = None) -> GeminiHandler:
        """
        Get or create a GeminiHandler instance.
        
        Args:
            api_key: Single API key (optional)
            api_keys: List of API keys (optional)
            
        Returns:
            GeminiHandler instance
        """
        if cls._handler_instance is None:
            # Collect keys from different sources
            keys_to_use = []
            
            # Add explicit API keys if provided
            if api_keys:
                keys_to_use.extend(api_keys)
            
            # Add single API key if provided
            if api_key:
                keys_to_use.append(api_key)
                
            # If no keys were provided directly, check for environment variables
            if not keys_to_use:
                # Check for LiteLLM convention for keys
                litellm_key = os.getenv('LITELLM_GEMINI_API_KEY')
                if litellm_key:
                    keys_to_use.append(litellm_key)
                
                # Check for comma-separated keys
                gemini_keys = os.getenv('GEMINI_API_KEYS')
                if gemini_keys:
                    keys_to_use.extend([k.strip() for k in gemini_keys.split(',') if k.strip()])
                
                # Check for single key
                gemini_key = os.getenv('GEMINI_API_KEY')
                if gemini_key:
                    keys_to_use.append(gemini_key)
            
            if not keys_to_use:
                raise ValueError(
                    "No API keys found. Please provide keys via api_key/api_keys parameters or "
                    "set LITELLM_GEMINI_API_KEY, GEMINI_API_KEYS, or GEMINI_API_KEY environment variables."
                )
            
            # Initialize handler with the collected keys
            cls._handler_instance = GeminiHandler(
                api_keys=keys_to_use,
                content_strategy=Strategy.ROUND_ROBIN,  # Default strategy
                key_strategy=KeyRotationStrategy.ROUND_ROBIN
            )
            
        return cls._handler_instance

    @classmethod
    def completion(
        cls,
        model: str,
        messages: List[Dict[str, Any]],
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        stream: Optional[bool] = False,
        stop: Optional[Union[str, List[str]]] = None,
        user: Optional[str] = None,
        system_instruction: Optional[str] = None,
        response_format: Optional[Dict[str, str]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Process completion requests from LiteLLM in the expected format.
        
        This method adapts LiteLLM's expected parameters to GeminiHandler format.
        
        Args:
            model: Model name (e.g., "custom/gemini-1.5-pro")
            messages: List of messages in the OpenAI format
            api_key: Optional API key to use
            api_base: Optional API base URL
            temperature: Control randomness (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            stream: Whether to stream the response
            stop: Stop sequences
            user: User identifier
            system_instruction: System instructions
            response_format: Format specification (e.g., JSON)
            tools: Tools/functions available to the model
            tool_choice: Preference for tool usage
            **kwargs: Additional parameters
            
        Returns:
            Response in OpenAI-compatible format
        """
        try:
            # Strip the "custom/" prefix that LiteLLM adds
            gemini_model = model.replace("custom/", "") if model.startswith("custom/") else model
            
            # Get or create the handler
            handler = cls.get_handler(api_key=api_key)
            
            # Create appropriate generation config
            gen_config = GenerationConfig(
                temperature=temperature if temperature is not None else 0.7,
                top_p=top_p if top_p is not None else 1.0,
                max_output_tokens=max_tokens if max_tokens is not None else 1024,
                stop_sequences=stop if isinstance(stop, list) else [stop] if stop else None
            )
            
            # Handle system instruction
            if system_instruction:
                handler.system_instruction = system_instruction
            elif "system" in kwargs:
                handler.system_instruction = kwargs.pop("system")
                
            # Convert OpenAI-style messages to prompt text
            prompt = cls._convert_messages_to_prompt(messages)
            
            # Check if we need to handle structured output (JSON)
            if response_format and response_format.get("type") == "json_object":
                # Create a simple JSON schema validation
                schema = {
                    "type": "object",
                    "properties": {},  # Generic JSON object
                    "additionalProperties": True
                }
                
                # Generate structured content
                response_dict = handler.generate_structured_content(
                    prompt=prompt,
                    schema=schema,
                    model_name=gemini_model,
                    temperature=temperature,
                    top_p=top_p,
                    max_output_tokens=max_tokens
                )
            else:
                # Regular text generation
                response_dict = handler.generate_content(
                    prompt=prompt,
                    model_name=gemini_model
                )
            
            # Convert to OpenAI-style response
            return cls._convert_to_openai_response(response_dict, model)
            
        except Exception as e:
            # Format exception in OpenAI-compatible way
            error_type = "server_error"
            if "rate limit" in str(e).lower() or "429" in str(e):
                error_type = "rate_limit_error"
            elif "authentication" in str(e).lower() or "key" in str(e).lower():
                error_type = "authentication_error"
            
            # Construct error response
            return {
                "error": {
                    "message": str(e),
                    "type": error_type,
                    "param": None,
                    "code": 500
                }
            }
    
    @classmethod
    def embeddings(
        cls,
        model: str,
        input: Union[str, List[str]],
        api_key: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate embeddings from input text.
        
        Args:
            model: Model name (e.g., "custom/gemini-embedding-exp-03-07")
            input: Text or list of texts to embed
            api_key: Optional API key
            **kwargs: Additional parameters
            
        Returns:
            Embeddings in OpenAI-compatible format
        """
        try:
            # Strip the "custom/" prefix that LiteLLM adds
            gemini_model = model.replace("custom/", "") if model.startswith("custom/") else model
            
            # Get or create the handler
            handler = cls.get_handler(api_key=api_key)
            
            # Generate embeddings
            result = handler.generate_embeddings(
                content=input,
                model_name=gemini_model
            )
            
            # Format response in OpenAI-compatible way
            if result["success"]:
                # Handle single input vs list input
                data = []
                
                if isinstance(input, str):
                    # Single input
                    data = [{
                        "object": "embedding",
                        "embedding": result["embeddings"],
                        "index": 0
                    }]
                else:
                    # List input
                    data = [
                        {
                            "object": "embedding",
                            "embedding": emb,
                            "index": i
                        }
                        for i, emb in enumerate(result["embeddings"])
                    ]
                
                return {
                    "object": "list",
                    "data": data,
                    "model": model,
                    "usage": {
                        "prompt_tokens": -1,  # Not tracked by Gemini Handler
                        "total_tokens": -1    # Not tracked by Gemini Handler
                    }
                }
            else:
                # Return error in OpenAI format
                return {
                    "error": {
                        "message": result["error"],
                        "type": "server_error",
                        "param": None,
                        "code": 500
                    }
                }
                
        except Exception as e:
            # Format exception in OpenAI-compatible way
            return {
                "error": {
                    "message": str(e),
                    "type": "server_error",
                    "param": None,
                    "code": 500
                }
            }
    
    @staticmethod
    def _convert_messages_to_prompt(messages: List[Dict[str, Any]]) -> str:
        """
        Convert OpenAI-format messages to a text prompt.
        
        Args:
            messages: List of message objects with role and content
            
        Returns:
            Formatted prompt string
        """
        prompt_parts = []
        
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            
            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
            elif role == "function" or role == "tool":
                name = message.get("name", "function")
                prompt_parts.append(f"Function {name}: {content}")
                
        return "\n\n".join(prompt_parts)
    
    @staticmethod
    def _convert_to_openai_response(response_dict: Dict[str, Any], model: str) -> Dict[str, Any]:
        """
        Convert GeminiHandler response to OpenAI format.
        
        Args:
            response_dict: Response from GeminiHandler
            model: Model name
            
        Returns:
            Response in OpenAI format
        """
        if not response_dict.get("success", False):
            # Handle error case
            return {
                "error": {
                    "message": response_dict.get("error", "Unknown error"),
                    "type": "server_error",
                    "param": None,
                    "code": 500
                }
            }
        
        # Extract text content
        text_content = response_dict.get("text", "")
        
        # Check for structured data
        structured_data = response_dict.get("structured_data")
        if structured_data:
            text_content = str(structured_data)  # JSON string representation
        
        # Build OpenAI-style response
        completion_response = {
            "id": f"gemini-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": text_content
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": -1,  # Not tracked by Gemini Handler
                "completion_tokens": -1,  # Not tracked by Gemini Handler
                "total_tokens": -1  # Not tracked by Gemini Handler
            }
        }
        
        # Add proxy information if available
        if "proxy_info" in response_dict and response_dict["proxy_info"]:
            # Redact sensitive information
            proxy_info = response_dict["proxy_info"]
            safe_proxy_info = {k: v for k, v in proxy_info.items() if k not in ['credentials']}
            
            # Redact username/password from URLs if present
            for key in ['http', 'https']:
                if key in safe_proxy_info and safe_proxy_info[key] and '@' in safe_proxy_info[key]:
                    parts = safe_proxy_info[key].split('@', 1)
                    protocol = parts[0].split('://', 1)[0]
                    safe_proxy_info[key] = f"{protocol}://[REDACTED]@{parts[1]}"
                    
            completion_response["proxy_info"] = safe_proxy_info
        
        return completion_response