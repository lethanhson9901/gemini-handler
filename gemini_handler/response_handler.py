import json
import time
from typing import Any

from .data_models import ModelResponse


class ResponseHandler:
    """Handles and processes model responses."""
    @staticmethod
    def process_response(
        response: Any,
        model_name: str,
        start_time: float,
        key_index: int,
        response_mime_type: str = "text/plain"
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
            
            result = ModelResponse(
                success=True,
                model=model_name,
                text=response.text,
                time=time.time() - start_time,
                api_key_index=key_index
            )
            
            # Handle structured data
            if response_mime_type == "application/json":
                try:
                    result.structured_data = json.loads(response.text)
                except json.JSONDecodeError:
                    result.success = False
                    result.error = "Failed to parse JSON response"
            
            return result
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
