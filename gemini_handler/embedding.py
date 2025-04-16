# Modified embedding.py
"""Module for handling Gemini embedding functionality."""
import time
from typing import Any, Dict, List, Optional, Union

from google import genai
from google.api_core import client_options
from google.genai import types

from .data_models import EmbeddingConfig, ModelResponse
from .key_rotation import KeyRotationManager
from .proxy import ProxyManager


class EmbeddingHandler:
    """Handles embedding generation using Gemini API."""
    
    def __init__(
        self, 
        key_manager: KeyRotationManager,
        proxy_settings: Optional[Dict[str, str]] = None
    ):
        """
        Initialize the embedding handler with a key manager.
        
        Args:
            key_manager: The key rotation manager instance
            proxy_settings: Optional dictionary with proxy settings
        """
        self.key_manager = key_manager
        self.proxy_settings = proxy_settings
        
    def generate_embeddings(
        self,
        content: Union[str, List[str]],
        model_name: str = "gemini-embedding-exp-03-07",
        task_type: Optional[str] = None
    ) -> ModelResponse:
        """
        Generate embeddings for the provided content.
        
        Args:
            content: Text content to embed (string or list of strings)
            model_name: Embedding model to use
            task_type: Optional task type for specialized embeddings
            
        Returns:
            ModelResponse object containing embeddings or error information
        """
        start_time = time.time()
        api_key, key_index = self.key_manager.get_next_key()
        
        try:
            # Configure client with the selected API key and proxy if needed
            client_opts = None
            if self.proxy_settings:
                client_opts = ProxyManager.get_client_options(self.proxy_settings)
                
            if client_opts:
                client = genai.Client(api_key=api_key, client_options=client_opts)
            else:
                client = genai.Client(api_key=api_key)
            
            # Prepare embedding configuration
            config = None
            if task_type:
                config = types.EmbedContentConfig(task_type=task_type)
            
            # Generate embeddings
            result = client.models.embed_content(
                model=model_name,
                contents=content,
                config=config
            )
            
            # Mark successful API call
            self.key_manager.mark_success(key_index)
            
            # Process embeddings to extract values
            processed_embeddings = result.embeddings
            
            # Prepare response
            return ModelResponse(
                success=True,
                model=model_name,
                time=time.time() - start_time,
                api_key_index=key_index,
                embeddings=processed_embeddings
            )
            
        except Exception as e:
            # Handle rate limiting
            if "429" in str(e):
                self.key_manager.mark_rate_limited(key_index)
            
            return ModelResponse(
                success=False,
                model=model_name,
                error=str(e),
                time=time.time() - start_time,
                api_key_index=key_index
            )
