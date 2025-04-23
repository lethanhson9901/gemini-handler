import logging
from typing import AsyncGenerator, List, Union, Optional, Dict, Any
from openai import AsyncOpenAI, APIError, OpenAIError
from openai.types.chat import ChatCompletion, ChatCompletionChunk
from openai.types.embedding import Embedding
from openai.types import ImagesResponse
from openai.types.model import Model
from fastapi import HTTPException, status

from config import settings
from models import ChatCompletionRequest, EmbeddingRequest, ImageGenerationRequest

logger = logging.getLogger(__name__)

class GeminiService:
    """Service layer for interacting with the Gemini API via OpenAI client."""

    def __init__(self) -> None:
        try:
            self.client = AsyncOpenAI(
                api_key=settings.gemini_api_key.get_secret_value(),
                base_url=settings.gemini_base_url,
            )
            logger.info("GeminiService initialized successfully.")
        except Exception as e:
            logger.exception("Failed to initialize AsyncOpenAI client.")
            raise RuntimeError(f"Could not initialize Gemini client: {e}") from e

    async def _handle_api_error(self, error: OpenAIError) -> None:
        """Centralized handling of OpenAI/Gemini API errors."""
        logger.error(f"Gemini API Error: {error}", exc_info=True)
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        detail = f"An error occurred with the Gemini API: {error}"

        if isinstance(error, APIError):
            status_code = error.status_code or status_code
            # Try to parse the error body if available for more details
            try:
                # error.body might be None or not contain the expected structure
                if error.body and isinstance(error.body, dict):
                    gemini_error = error.body.get('error', {})
                    if gemini_error:
                         detail = f"Error code: {error.status_code} - {gemini_error.get('message', str(error))}"
                    else: # Fallback if 'error' key is missing
                         detail = f"Error code: {error.status_code} - {error.body}"
                elif error.message:
                    detail = f"Error code: {error.status_code} - {error.message}"

            except Exception:
                # Fallback if parsing fails
                detail = f"Error code: {error.status_code} - {str(error)}"


        raise HTTPException(status_code=status_code, detail=detail)

    async def create_chat_completion(
        self, request: ChatCompletionRequest
    ) -> Union[ChatCompletion, AsyncGenerator[ChatCompletionChunk, None]]:
        """Creates a chat completion, handling streaming."""
        model = request.model or settings.default_chat_model
        messages_dict = [msg.model_dump(exclude_unset=True) for msg in request.messages]
        tools_dict = [tool.model_dump(exclude_unset=True) for tool in request.tools] if request.tools else None

        # Dynamically build arguments, excluding None values
        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": messages_dict,
            "stream": request.stream or False, # Default to False if None/missing
        }
        if request.n is not None:
            kwargs["n"] = request.n
        if tools_dict is not None:
            kwargs["tools"] = tools_dict
        # *** Crucially, only add tool_choice if it's explicitly provided ***
        if request.tool_choice is not None:
            kwargs["tool_choice"] = request.tool_choice
        if request.temperature is not None:
            kwargs["temperature"] = request.temperature
        if request.max_tokens is not None:
            kwargs["max_tokens"] = request.max_tokens
        # Add other optional parameters here similarly if needed

        try:
            logger.debug(f"Calling Gemini chat completion with args: {kwargs}")
            response = await self.client.chat.completions.create(**kwargs)
            return response
        except OpenAIError as e:
            await self._handle_api_error(e)
            raise # pragma: no cover

    async def list_models(self) -> List[Model]:
        """Lists available models."""
        try:
            logger.debug("Listing Gemini models")
            models_page = await self.client.models.list()
            return models_page.data
        except OpenAIError as e:
            await self._handle_api_error(e)
            raise # pragma: no cover

    async def retrieve_model(self, model_id: str) -> Model:
        """Retrieves a specific model."""
        try:
            logger.debug(f"Retrieving Gemini model: {model_id}")
            model = await self.client.models.retrieve(model_id)
            return model
        except OpenAIError as e:
            await self._handle_api_error(e)
            raise # pragma: no cover

    async def create_embedding(self, request: EmbeddingRequest) -> List[Embedding]:
        """Creates text embeddings."""
        model = request.model or settings.default_embedding_model
        kwargs: Dict[str, Any] = {
            "input": request.input,
            "model": model,
        }
        # Add other optional embedding params if needed (e.g., encoding_format)
        # if request.encoding_format is not None:
        #     kwargs["encoding_format"] = request.encoding_format

        try:
            logger.debug(f"Creating Gemini embeddings with args: {kwargs}")
            response = await self.client.embeddings.create(**kwargs)
            return response.data
        except OpenAIError as e:
            await self._handle_api_error(e)
            raise # pragma: no cover

    async def generate_image(self, request: ImageGenerationRequest) -> ImagesResponse:
        """Generates an image."""
        model = request.model or settings.default_image_gen_model
        kwargs: Dict[str, Any] = {
            "model": model,
            "prompt": request.prompt,
        }
        if request.n is not None:
            kwargs["n"] = request.n
        if request.size is not None: # Note: Verify Gemini compatibility
            kwargs["size"] = request.size
        if request.response_format is not None:
            kwargs["response_format"] = request.response_format
        # Add other optional image params here if needed

        try:
            logger.debug(f"Generating Gemini image with args: {kwargs}")
            response: ImagesResponse = await self.client.images.generate(**kwargs)
            return response
        except OpenAIError as e:
            await self._handle_api_error(e)
            raise # pragma: no cover

