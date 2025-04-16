from typing import Any, Dict, List, Optional, Union


class ContentGenerationMixin:
    """Mixin for content generation methods."""
    
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
        from .data_models import GenerationConfig
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
