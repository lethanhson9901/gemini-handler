# gemini_handler/response_handler.py
import json
import time
from typing import Any, Dict, Optional

from .data_models import ModelResponse

# No need to import ProxyManager here anymore


class ResponseHandler:
    """Handles and processes model responses."""
    @staticmethod
    def process_response(
        response: Any,
        model_name: str,
        start_time: float,
        key_index: int,
        response_mime_type: str = "text/plain",
        proxy_info: Optional[Dict[str, Any]] = None # New parameter to accept proxy info
    ) -> ModelResponse:
        """Process and validate model response."""
        try:
            # Check for copyright block first
            finish_reason = None
            if hasattr(response, 'candidates') and response.candidates:
                # Check finish reason if available
                if hasattr(response.candidates[0], 'finish_reason'):
                     finish_reason = response.candidates[0].finish_reason
                     if finish_reason == 4:  # SAFETY / Copyright block
                         return ModelResponse(
                             success=False,
                             model=model_name,
                             error='Blocked: Response stopped due to safety settings (e.g., copyright, harm).',
                             time=time.time() - start_time,
                             api_key_index=key_index,
                             proxy_info=proxy_info # Include proxy info even on block
                         )
                # Check if text is missing even if finish_reason isn't 4
                if not hasattr(response, 'text') or not response.text:
                    # Check for prompt feedback if text is missing
                    prompt_feedback = None
                    if hasattr(response, 'prompt_feedback') and hasattr(response.prompt_feedback, 'block_reason'):
                        prompt_feedback = response.prompt_feedback.block_reason
                    if prompt_feedback:
                        return ModelResponse(
                            success=False,
                            model=model_name,
                            error=f'Blocked: Prompt blocked due to safety settings (Reason: {prompt_feedback}).',
                            time=time.time() - start_time,
                            api_key_index=key_index,
                            proxy_info=proxy_info
                        )
                    # If no text and no clear block reason, return generic error
                    # This might catch cases where the response structure is unexpected
                    # but doesn't throw the specific "quick accessor" error below.
                    return ModelResponse(
                        success=False,
                        model=model_name,
                        error='Blocked: No text content received and no specific block reason found.',
                        time=time.time() - start_time,
                        api_key_index=key_index,
                        proxy_info=proxy_info
                    )


            # If we have text, proceed
            result = ModelResponse(
                success=True,
                model=model_name,
                text=response.text, # This might raise the "quick accessor" error if no valid part exists
                time=time.time() - start_time,
                api_key_index=key_index,
                proxy_info=proxy_info # Assign passed proxy info
            )

            # Handle structured data if requested
            if response_mime_type == "application/json":
                try:
                    result.structured_data = json.loads(response.text)
                except json.JSONDecodeError:
                    # If JSON parsing fails, mark as failure but keep text
                    result.success = False
                    result.error = "Failed to parse JSON response"
                    # Keep result.text as it might contain useful error info from the model

            # Proxy info is already added via the parameter

            return result

        except Exception as e:
            # Handle the specific error when response.text is accessed incorrectly
            if "The `response.text` quick accessor requires the response to contain a valid `Part`" in str(e):
                # Check for prompt feedback for more specific error message
                prompt_feedback_reason = "Unknown"
                if hasattr(response, 'prompt_feedback') and hasattr(response.prompt_feedback, 'block_reason'):
                     prompt_feedback_reason = str(response.prompt_feedback.block_reason)

                return ModelResponse(
                    success=False,
                    model=model_name,
                    error=f'Blocked: No valid response parts available (Safety/Block Reason: {prompt_feedback_reason}).',
                    time=time.time() - start_time,
                    api_key_index=key_index,
                    proxy_info=proxy_info # Include proxy info in error response
                )
            # Re-raise other unexpected exceptions
            print(f"Unexpected error in ResponseHandler: {e}") # Log unexpected errors
            raise # Re-raise the original exception for higher-level handling