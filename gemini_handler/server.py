# gemini_handler/server.py

import os
import time
import uuid
from typing import Any, Dict, List, Optional, Union

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .data_models import GenerationConfig, KeyRotationStrategy, Strategy
from .gemini_handler import GeminiHandler

# --- Pydantic models for API request/response ---

class Message(BaseModel):
    role: str
    content: str
    name: Optional[str] = None

class CompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 1.0
    n: Optional[int] = 1
    max_tokens: Optional[int] = 1024
    stop: Optional[Union[str, List[str]]] = None
    stream: Optional[bool] = False
    user: Optional[str] = None
    response_format: Optional[Dict[str, str]] = None
    
class EmbeddingRequest(BaseModel):
    model: str
    input: Union[str, List[str]]
    user: Optional[str] = None

class ModelListResponse(BaseModel):
    object: str = "list"
    data: List[Dict[str, Any]]

# --- Server implementation ---

class GeminiServer:
    """OpenAI-compatible API server for Gemini."""
    
    def __init__(
        self, 
        api_keys=None, 
        host="0.0.0.0", 
        port=8000,
        proxy_settings=None,
        content_strategy=Strategy.ROUND_ROBIN,
        key_strategy=KeyRotationStrategy.ROUND_ROBIN,
        rate_limit=60,
        reset_window=60,
        max_retries=3,
        retry_delay=30,
        system_instruction=None,
        generation_config=None
    ):
        self.host = host
        self.port = port
        
        # Initialize Gemini Handler
        if api_keys is None:
            # Try to get from environment variables
            api_keys_str = os.getenv('GEMINI_API_KEYS')
            if api_keys_str:
                api_keys = [k.strip() for k in api_keys_str.split(',') if k.strip()]
            else:
                single_key = os.getenv('GEMINI_API_KEY')
                if single_key:
                    api_keys = [single_key]
                else:
                    raise ValueError(
                        "No API keys found. Please provide keys via api_keys parameter or "
                        "set GEMINI_API_KEYS or GEMINI_API_KEY environment variables."
                    )
        
        # Convert generation_config dict to GenerationConfig object if needed
        gen_config = None
        if generation_config:
            gen_config = GenerationConfig(**generation_config)
        
        # Initialize handler with all settings
        self.handler = GeminiHandler(
            api_keys=api_keys,
            content_strategy=content_strategy,
            key_strategy=key_strategy,
            system_instruction=system_instruction,
            generation_config=gen_config,
            proxy_settings=proxy_settings
        )
        
        # Configure key rotation manager if rate limits provided
        if hasattr(self.handler, 'key_manager') and rate_limit and reset_window:
            self.handler.key_manager.rate_limit = rate_limit
            self.handler.key_manager.reset_window = reset_window
        
        # Configure retry settings if provided
        if hasattr(self.handler, 'config') and max_retries:
            self.handler.config.max_retries = max_retries
        if hasattr(self.handler, 'config') and retry_delay:
            self.handler.config.retry_delay = retry_delay
        
        # Initialize FastAPI app
        self.app = FastAPI(
            title="Gemini API Server",
            description="OpenAI-compatible API server for Google Gemini models",
            version="1.0.0"
        )
        
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Register routes
        self._register_routes()

    def _register_routes(self):
        """Register API routes with FastAPI app."""
        @self.app.on_event("startup")
        async def startup_event():
            """Start background tasks when the server starts."""
            # Check if handler has auto proxy configured
            if (hasattr(self.handler, 'proxy_settings') and 
                self.handler.proxy_settings and 
                isinstance(self.handler.proxy_settings, dict) and
                'auto_proxy' in self.handler.proxy_settings and
                self.handler.proxy_settings['auto_proxy'].get('auto_update', False)):
                
                try:
                    from .auto_proxy import SWIFTSHADOW_AVAILABLE, AutoProxyManager
                    
                    if SWIFTSHADOW_AVAILABLE:
                        # Start async background task for proxy updates
                        import asyncio
                        
                        async def background_update():
                            """Update proxies periodically."""
                            update_interval = self.handler.proxy_settings['auto_proxy'].get('update_interval', 15)
                            while True:
                                print(f"Async updating proxies...")
                                await AutoProxyManager.async_update()
                                await asyncio.sleep(update_interval)
                        
                        # Start the task
                        asyncio.create_task(background_update())
                        print("Started background proxy updater task")
                except ImportError:
                    print("SwiftShadow not available, auto proxy updates disabled")
        
        @self.app.middleware("http")
        async def rotate_proxy_middleware(request: Request, call_next):
            # Rotate proxy before processing request
            if request.url.path.startswith("/v1/"):
                try:
                    from .proxy import ProxyManager
                    ProxyManager.apply_next_proxy()
                    print(f"Rotated proxy for request to {request.url.path}")
                except Exception as e:
                    print(f"Failed to rotate proxy: {e}")
            
            response = await call_next(request)
            return response


        @self.app.get("/v1/models")
        async def list_models():
            """List available models in OpenAI format."""
            model_list = [
                {
                    "id": "gemini-2.0-flash",
                    "object": "model",
                    "created": 1677610602,
                    "owned_by": "google",
                },
                {
                    "id": "gemini-2.0-pro",
                    "object": "model",
                    "created": 1677649963,
                    "owned_by": "google",
                },
                {
                    "id": "gemini-1.5-pro",
                    "object": "model", 
                    "created": 1677610602,
                    "owned_by": "google",
                },
                {
                    "id": "gemini-1.5-flash",
                    "object": "model",
                    "created": 1677610602,
                    "owned_by": "google",
                },
                {
                    "id": "gemini-embedding-exp-03-07",
                    "object": "model",
                    "created": 1677610602,
                    "owned_by": "google",
                }
            ]
            
            return {"object": "list", "data": model_list}
        
        @self.app.post("/v1/chat/completions")
        async def create_chat_completion(request: CompletionRequest):
            """Create a chat completion (OpenAI format)."""
            try:
                # Convert to standard format
                messages = [
                    {"role": msg.role, "content": msg.content}
                    for msg in request.messages
                ]
                
                # Convert messages to prompt
                prompt = self._convert_messages_to_prompt(messages)
                
                # Check if we need structured output (JSON)
                if request.response_format and request.response_format.get("type") == "json_object":
                    # Generate structured content
                    schema = {
                        "type": "object",
                        "properties": {},  # Generic JSON object
                        "additionalProperties": True
                    }
                    
                    result = self.handler.generate_structured_content(
                        prompt=prompt,
                        schema=schema,
                        model_name=request.model,
                        temperature=request.temperature,
                        top_p=request.top_p,
                        max_output_tokens=request.max_tokens
                    )
                else:
                    # Regular text generation
                    result = self.handler.generate_content(
                        prompt=prompt,
                        model_name=request.model,
                    )
                
                if not result.get("success", False):
                    raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
                
                # Get content
                text = result.get("text", "")
                
                # Handle structured data if present
                if structured_data := result.get("structured_data"):
                    text = str(structured_data)  # Use JSON string
                
                # Build OpenAI-style response
                completion_id = f"chatcmpl-{uuid.uuid4().hex}"
                
                # Extract proxy info if available
                proxy_info = result.get("proxy_info")
                safe_proxy_info = None
                
                if proxy_info:
                    # Redact sensitive information
                    safe_proxy_info = {k: v for k, v in proxy_info.items() if k not in ['credentials']}
                    
                    # Redact username/password from URLs if present
                    for key in ['http', 'https']:
                        if key in safe_proxy_info and safe_proxy_info[key] and '@' in safe_proxy_info[key]:
                            parts = safe_proxy_info[key].split('@', 1)
                            protocol = parts[0].split('://', 1)[0]
                            safe_proxy_info[key] = f"{protocol}://[REDACTED]@{parts[1]}"
                
                # Create response with proxy info
                response = {
                    "id": completion_id,
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": request.model,
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": text
                            },
                            "finish_reason": "stop"
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 0,  # Placeholder values
                        "completion_tokens": 0,
                        "total_tokens": 0
                    }
                }
                
                # Add proxy info to the response
                if safe_proxy_info:
                    response["proxy_info"] = safe_proxy_info
                
                return response
                
            except Exception as e:
                # Handle errors in OpenAI format
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": {
                            "message": str(e),
                            "type": "server_error",
                            "param": None,
                            "code": "500"
                        }
                    }
                )

        @self.app.post("/v1/embeddings")
        async def create_embeddings(request: EmbeddingRequest):
            """Create embeddings (OpenAI format)."""
            try:
                result = self.handler.generate_embeddings(
                    content=request.input,
                    model_name=request.model
                )
                
                if not result.get("success", False):
                    raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
                
                # Format response in OpenAI style
                data = []
                
                if isinstance(request.input, str):
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
                    "model": request.model,
                    "usage": {
                        "prompt_tokens": 0,  # Placeholder
                        "total_tokens": 0    # Placeholder
                    }
                }
                
            except Exception as e:
                # Handle errors in OpenAI format
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": {
                            "message": str(e),
                            "type": "server_error",
                            "param": None,
                            "code": "500"
                        }
                    }
                )
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {"status": "ok", "timestamp": time.time()}

        @self.app.get("/v1/proxy/info")
        async def get_proxy_info():
            """Get information about the current proxy configuration."""
            try:
                from .proxy import ProxyManager
                current_proxy = ProxyManager.get_current_proxy()
                
                # Create a safe version for display (hide credentials)
                safe_proxy = None
                if current_proxy:
                    safe_proxy = {k: v for k, v in current_proxy.items() if k != 'credentials'}
                    
                    # Redact username/password from URLs if present
                    for key in ['http', 'https']:
                        if key in safe_proxy and safe_proxy[key] and '@' in safe_proxy[key]:
                            parts = safe_proxy[key].split('@', 1)
                            protocol = parts[0].split('://', 1)[0]
                            safe_proxy[key] = f"{protocol}://[REDACTED]@{parts[1]}"
                
                return {
                    "current_proxy": safe_proxy,
                    "status": "active" if safe_proxy else "none"
                }
            except Exception as e:
                return {
                    "error": str(e),
                    "status": "error"
                }

        @self.app.get("/v1/proxy/stats")
        async def get_proxy_stats():
            """Get detailed proxy statistics."""
            try:
                from .proxy import ProxyManager
                stats = ProxyManager.get_proxy_stats()
                
                # Redact sensitive information
                if 'proxy_history' in stats:
                    for proxy in stats['proxy_history']:
                        if proxy:
                            # Redact username/password from URLs if present
                            for key in ['http', 'https']:
                                if key in proxy and proxy[key] and '@' in proxy[key]:
                                    parts = proxy[key].split('@', 1)
                                    protocol = parts[0].split('://', 1)[0]
                                    proxy[key] = f"{protocol}://[REDACTED]@{parts[1]}"
                
                if 'current_proxy' in stats and stats['current_proxy']:
                    proxy = stats['current_proxy']
                    for key in ['http', 'https']:
                        if key in proxy and proxy[key] and '@' in proxy[key]:
                            parts = proxy[key].split('@', 1)
                            protocol = parts[0].split('://', 1)[0]
                            proxy[key] = f"{protocol}://[REDACTED]@{parts[1]}"
                
                return stats
            except Exception as e:
                return {
                    "error": str(e),
                    "status": "error"
                }

        @self.app.post("/v1/proxy/rotate")
        async def rotate_proxy():
            """Manually rotate to the next proxy."""
            try:
                from .proxy import ProxyManager
                success = ProxyManager.apply_next_proxy()
                current = ProxyManager.get_current_proxy()
                
                # Redact sensitive information
                safe_proxy = None
                if current:
                    safe_proxy = {k: v for k, v in current.items() if k != 'credentials'}
                    
                    # Redact username/password from URLs if present
                    for key in ['http', 'https']:
                        if key in safe_proxy and safe_proxy[key] and '@' in safe_proxy[key]:
                            parts = safe_proxy[key].split('@', 1)
                            protocol = parts[0].split('://', 1)[0]
                            safe_proxy[key] = f"{protocol}://[REDACTED]@{parts[1]}"
                
                return {
                    "success": success,
                    "message": "Rotated to next proxy" if success else "Failed to rotate proxy",
                    "current_proxy": safe_proxy
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e)
                }
    
    def _convert_messages_to_prompt(self, messages: List[Dict[str, Any]]) -> str:
        """Convert OpenAI-format messages to a text prompt."""
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
    
    def run(self):
        """Run the API server."""
        uvicorn.run(self.app, host=self.host, port=self.port)

