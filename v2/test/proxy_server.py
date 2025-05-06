"""
LiteLLM Proxy Server for Gemini
===============================
This is a FastAPI-based proxy server that provides OpenAI-compatible API endpoints
for Google's Gemini models using LiteLLM.

Features:
- OpenAI API compatibility
- Support for Google Search and Code Execution tools
- Advanced parameters like reasoning_effort and response schema
- API key management
- Comprehensive API documentation
- Model listing endpoint

Usage:
    python proxy_server.py
"""

import asyncio
import json
import logging
import os
import uuid
from typing import Any, Dict, List, Optional, Union

import google.generativeai as genai
import uvicorn
import yaml
from fastapi import Body, Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from litellm import Router, acompletion, completion

# Removing import of RouterSettings as it's not available in this LiteLLM version
from litellm.exceptions import (
    BadRequestError,
    JSONSchemaValidationError,
    RateLimitError,
)
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Config file path
CONFIG_FILE = 'config.yaml'

# Initialize FastAPI app
app = FastAPI(
    title="LiteLLM Gemini Proxy",
    description="An OpenAI-compatible API server for Google's Gemini models powered by LiteLLM",
    version="1.0.0",
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for API requests and responses
class ModelData(BaseModel):
    id: str
    object: str = "model"
    created: int = 1686935002
    owned_by: str = "google"

class ModelsResponse(BaseModel):
    object: str = "list"
    data: List[ModelData]

class Message(BaseModel):
    role: str
    content: str

class CompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 1.0
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False
    reasoning_effort: Optional[str] = None
    thinking: Optional[Dict[str, Any]] = None
    response_format: Optional[Dict[str, Any]] = None
    tools: Optional[List[Dict[str, Any]]] = None
    safety_settings: Optional[List[Dict[str, Any]]] = None
    topK: Optional[int] = None

class CompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]

# Router instance as a global variable
router = None

def load_api_keys(config_path: str) -> list:
    """Load API keys from the config file."""
    try:
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)
        keys = data.get('gemini', {}).get('api_keys', [])
        if isinstance(keys, list) and keys:
            logging.info(f"Loaded {len(keys)} API keys.")
            return keys
        raise ValueError("API keys list is empty or invalid.")
    except Exception as e:
        logging.error(f"Failed to load API keys: {e}")
        return []

def get_supported_models(api_key: str) -> list:
    """Get list of supported Gemini models for a given API key."""
    try:
        genai.configure(api_key=api_key)
        return [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods and 'gemini' in m.name]
    except Exception as e:
        logging.error(f"Error fetching models with API key: {e}")
        return []

def create_model_list(api_keys: list) -> list:
    """Create a model list configuration for LiteLLM Router."""
    model_list = []
    for api_key in api_keys:
        models = get_supported_models(api_key)
        for m in models:
            short_name = m.split('/')[-1]
            model_list.append({
                "model_name": short_name,
                "litellm_params": {"model": f"gemini/{short_name}", "api_key": api_key}
            })
    return model_list

async def initialize_router():
    """Initialize the LiteLLM Router with API keys from config."""
    global router
    api_keys = load_api_keys(CONFIG_FILE)
    if not api_keys:
        raise ValueError("No API keys found in config file")

    model_list = create_model_list(api_keys)
    if not model_list:
        raise ValueError("No supported Gemini models found")

    try:
        # Initialize Router with simpler configuration compatible with older LiteLLM versions
        router = Router(
            model_list=model_list, 
            routing_strategy="simple-shuffle",
        )
        logging.info("LiteLLM Router initialized.")
        return router
    except Exception as e:
        logging.error(f"Router initialization failed: {e}")
        raise

@app.on_event("startup")
async def startup_event():
    """Initialize router on startup."""
    try:
        await initialize_router()
    except Exception as e:
        logging.error(f"Failed to initialize router: {e}")

def get_model_data(model_list: list) -> List[ModelData]:
    """Convert model list to API response format."""
    models = []
    seen = set()
    
    for item in model_list:
        model_name = item["model_name"]
        if model_name not in seen:
            seen.add(model_name)
            models.append(ModelData(id=model_name))
    
    return models

@app.get("/v1/models", response_model=ModelsResponse, tags=["Models"])
async def list_models():
    """
    List all available models.
    
    Returns a list of model objects that are available through the API.
    """
    if not router:
        raise HTTPException(status_code=500, detail="Router not initialized")
    
    try:
        model_data = get_model_data(router.model_list)
        return {"object": "list", "data": model_data}
    except Exception as e:
        logging.error(f"Error listing models: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/chat/completions", response_model=CompletionResponse, tags=["Chat"])
async def create_chat_completion(request: CompletionRequest):
    """
    Creates a completion for the chat message.
    
    This endpoint is compatible with OpenAI's chat completion API but provides 
    access to Google's Gemini models with advanced features like Google Search integration.
    
    Parameters:
    - **model**: The model to use for completion
    - **messages**: A list of messages comprising the conversation so far
    - **temperature**: Sampling temperature between 0 and 2 (default: 0.7)
    - **top_p**: Nucleus sampling parameter (default: 1.0)
    - **max_tokens**: Maximum tokens to generate (default: varies by model)
    - **stream**: Whether to stream back partial progress (default: false)
    - **reasoning_effort**: "low", "default", or "high" to control reasoning depth
    - **thinking**: Dictionary with "type": "enabled"/"disabled" and optional "budget_tokens"
    - **response_format**: Format specification for responses (e.g., JSON)
    - **tools**: List of tools to use (e.g., googleSearch, codeExecution)
    - **safety_settings**: List of safety settings to apply
    - **topK**: Top-K sampling parameter
    
    Returns a completion object with the generated response.
    """
    if not router:
        raise HTTPException(status_code=500, detail="Router not initialized")
    
    try:
        # Convert request to litellm format
        litellm_params = {
            "model": request.model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "temperature": request.temperature,
            "top_p": request.top_p,
            "stream": request.stream,
        }
        
        # Add optional parameters if provided
        if request.max_tokens is not None:
            litellm_params["max_tokens"] = request.max_tokens
        
        if request.reasoning_effort is not None:
            litellm_params["reasoning_effort"] = request.reasoning_effort
        
        if request.thinking is not None:
            litellm_params["thinking"] = request.thinking
        
        if request.response_format is not None:
            litellm_params["response_format"] = request.response_format
        
        if request.tools is not None:
            litellm_params["tools"] = request.tools
        
        if request.safety_settings is not None:
            litellm_params["safety_settings"] = request.safety_settings
        
        if request.topK is not None:
            litellm_params["topK"] = request.topK
        
        # Make the completion call
        response = await router.acompletion(**litellm_params)
        
        # Convert choices to dictionary format instead of using objects directly
        choices_dict = []
        for choice in response.choices:
            # Check if choice is already a dict
            if isinstance(choice, dict):
                choices_dict.append(choice)
            else:
                # Convert the Choice object to dict
                choice_dict = {
                    "index": choice.index,
                    "finish_reason": choice.finish_reason,
                    "message": {
                        "role": choice.message.role,
                        "content": choice.message.content
                    }
                }
                choices_dict.append(choice_dict)
        
        # Convert usage to dictionary format
        if isinstance(response.usage, dict):
            usage_dict = response.usage
        else:
            usage_dict = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        
        return {
            "id": response.id,
            "object": "chat.completion",
            "created": response.created,
            "model": response.model,
            "choices": choices_dict,
            "usage": usage_dict,
        }
    except JSONSchemaValidationError as e:
        raise HTTPException(status_code=400, detail=f"JSON Schema validation error: {str(e)}")
    except RateLimitError as e:
        raise HTTPException(status_code=429, detail=f"Rate limit exceeded: {str(e)}")
    except BadRequestError as e:
        raise HTTPException(status_code=400, detail=f"Bad request: {str(e)}")
    except Exception as e:
        logging.error(f"Error in chat completion: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Example endpoint using Google Search tool
@app.post("/v1/examples/google-search", tags=["Examples"])
async def example_google_search(query: str = Body(..., embed=True, description="Search query")):
    """
    Example endpoint demonstrating Google Search tool integration.
    
    This endpoint shows how to use the Google Search tool with Gemini models.
    
    Parameters:
    - **query**: The search query to process
    
    Returns the model's response after using Google Search.
    """
    if not router:
        raise HTTPException(status_code=500, detail="Router not initialized")
    
    try:
        response = await router.acompletion(
            model="gemini-2.5-flash-preview-04-17",  # Using the latest model
            messages=[
                {"role": "user", "content": f"Use Google Search to answer this question: {query}"}
            ],
            tools=[{"googleSearch": {}}],  # Enable Google Search tool
            temperature=0.2,  # Lower temperature for more factual responses
        )
        
        return {
            "query": query,
            "response": response.choices[0].message.content,
            "model": response.model
        }
    except Exception as e:
        logging.error(f"Error in Google Search example: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", include_in_schema=False)
async def redirect_to_docs():
    """Redirect root to API docs."""
    return JSONResponse({"message": "API is running. Visit /docs for API documentation."})

# Sample configuration file creation
@app.post("/setup", tags=["Admin"])
async def create_config_file(api_keys: List[str] = Body(..., description="List of Gemini API keys")):
    """
    Create a configuration file with the provided API keys.
    
    This endpoint is for initial setup only and should be protected in production.
    
    Parameters:
    - **api_keys**: List of Gemini API keys to save in the config file
    
    Returns confirmation of config file creation.
    """
    try:
        config = {
            "gemini": {
                "api_keys": api_keys
            }
        }
        
        with open(CONFIG_FILE, 'w') as f:
            yaml.dump(config, f)
        
        # Reinitialize router with new config
        await initialize_router()
        
        return {"message": "Configuration created successfully"}
    except Exception as e:
        logging.error(f"Error creating config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("proxy_server:app", host="0.0.0.0", port=8000, reload=True)