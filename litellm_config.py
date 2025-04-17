# litellm_config.py
# This should be used in projects that import litellm

from gemini_handler.litellm_integration import LiteLLMGeminiAdapter


# Register Gemini Handler as a custom provider to LiteLLM
def register_gemini_to_litellm():
    """
    Register Gemini Handler as a custom provider to LiteLLM.
    Call this function at the start of your application.
    """
    import litellm

    # Register completion endpoint
    litellm.register_completion_function(
        custom_llm_provider="gemini",  # Provider name
        completion_function=LiteLLMGeminiAdapter.completion  # Function to call
    )
    
    # Register embeddings endpoint
    litellm.register_embedding_function(
        custom_llm_provider="gemini",  # Provider name
        embedding_function=LiteLLMGeminiAdapter.embeddings  # Function to call
    )
    
    # Optional: Print confirmation
    print("Gemini Handler has been registered as a LiteLLM provider")
