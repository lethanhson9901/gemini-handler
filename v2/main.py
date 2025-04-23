import asyncio
import base64
import json
import logging
import os
import random
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import google.generativeai as genai
import litellm
import requests
import tls_requests
import uvicorn
import yaml
from fastapi import FastAPI, HTTPException
from fastapi.background import BackgroundTasks
from pydantic import BaseModel
from swiftshadow.classes import ProxyInterface

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("api_usage.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("gemini_api")

# Global dict to store API key information
request_info = {}
request_info_lock = threading.Lock()

# Initialize SwiftShadow proxy interface
swift = ProxyInterface(autoUpdate=False, autoRotate=True)

# FastAPI app
app = FastAPI(title="Gemini API Proxy Backend")

# Pydantic models for request validation
class CompletionRequest(BaseModel):
    model: str
    messages: List[Dict[str, Any]]
    temperature: Optional[float] = 0.7
    topP: Optional[float] = None
    topK: Optional[int] = None
    max_tokens: Optional[int] = None
    safety_settings: Optional[List[Dict[str, Any]]] = None
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Dict[str, Any]] = None
    response_format: Optional[Dict[str, Any]] = None
    reasoning_effort: Optional[str] = None
    thinking: Optional[Dict[str, Any]] = None

class ImageGenerationRequest(BaseModel):
    model: str = "gemini/gemini-2.0-flash-exp-image-generation"
    prompt: str
    modalities: List[str] = ["image", "text"]

# Browser profile manager (unchanged from original)
class BrowserProfileManager:
    def __init__(self):
        self.profiles = [
            "chrome_103", "chrome_104", "chrome_105", "chrome_106", "chrome_107", "chrome_108",
            "chrome_109", "chrome_110", "chrome_111", "chrome_112", "firefox_102", "firefox_104",
            "safari_15_3", "safari_15_6_1", "safari_16_0", "opera_89", "opera_90"
        ]
        self.api_key_profiles = {}
        self.profile_lock = threading.Lock()
    
    def get_profile_for_key(self, api_key):
        with self.profile_lock:
            if api_key not in self.api_key_profiles:
                hash_value = hash(api_key) % len(self.profiles)
                self.api_key_profiles[api_key] = self.profiles[hash_value]
            return self.api_key_profiles[api_key]

browser_manager = BrowserProfileManager()

# Custom completion response class (unchanged from original)
class CustomCompletion:
    class Message:
        def __init__(self, role, content, tool_calls=None):
            self.role = role
            self.content = content
            self.tool_calls = tool_calls
    
    class Choice:
        def __init__(self, index, message, finish_reason):
            self.index = index
            self.message = message
            self.finish_reason = finish_reason
    
    class Usage:
        def __init__(self, prompt_tokens, completion_tokens, total_tokens):
            self.prompt_tokens = prompt_tokens
            self.completion_tokens = completion_tokens
            self.total_tokens = total_tokens
    
    def __init__(self, id, object, created, model, choices, usage):
        self.id = id
        self.object = object
        self.created = created
        self.model = model
        self.choices = [self.Choice(
            choice["index"],
            self.Message(
                choice["message"]["role"],
                choice["message"]["content"],
                choice["message"].get("tool_calls")
            ),
            choice["finish_reason"]
        ) for choice in choices]
        self.usage = self.Usage(
            usage["prompt_tokens"],
            usage["completion_tokens"],
            usage["total_tokens"]
        )

# Proxy management
async def initialize_proxies():
    logger.info("Initializing proxy list...")
    await swift.async_update()
    logger.info(f"Loaded {len(swift.proxies)} proxies")

async def update_proxies_periodically():
    while True:
        logger.info("Updating proxy list...")
        await swift.async_update()
        logger.info(f"Updated proxy list, now have {len(swift.proxies)} proxies")
        await asyncio.sleep(300)  # Update every minute

# Initialize router and API keys
def initialize_router():
    model_list, api_key_map, api_keys = auto_generate_model_list("../config.yaml")
    return model_list, api_key_map, api_keys

def get_available_gemini_models(api_key: str) -> List[str]:
    genai.configure(api_key=api_key)
    try:
        models = genai.list_models()
        formatted_models = []
        for model in models:
            if "gemini" in model.name.lower() or "imagen" in model.name.lower():
                model_name = model.name.split('/')[-1]
                if re.search(r'-(00\d|latest)$', model_name):
                    continue
                if model_name not in formatted_models:
                    formatted_models.append(model_name)
        return formatted_models
    except Exception as e:
        logger.warning(f"Error retrieving model list: {e}")
        return ["gemini-2.0-flash"]

def auto_generate_model_list(config_path: str) -> tuple:
    if os.path.isabs(config_path):
        full_path = config_path
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.normpath(os.path.join(script_dir, config_path))
    
    if not os.path.exists(full_path):
        raise FileNotFoundError(f"Config file not found at: {full_path}")
    
    with open(full_path, 'r') as f:
        config = yaml.safe_load(f)
    
    api_keys = config.get('gemini', {}).get('api_keys', [])
    if not api_keys:
        raise ValueError("No Gemini API keys found in the config file")
    
    available_models = get_available_gemini_models(api_keys[0])
    logger.info(f"Found {len(available_models)} Gemini models")
    
    model_list = []
    api_key_map = {}
    for i, key in enumerate(api_keys):
        key_id = f"key{i+1}"
        api_key_map[key] = f"{key_id} (***{key[-4:]})"
    
    for model_name in available_models:
        for i, key in enumerate(api_keys):
            deployment_id = f"{model_name}-key{i+1}"
            with request_info_lock:
                request_info[deployment_id] = {
                    "api_key": key,
                    "friendly_name": api_key_map[key],
                    "model": model_name
                }
            model_deployment = {
                "model_name": f"gemini/{model_name}",
                "litellm_params": {
                    "model": f"gemini/{model_name}",
                    "api_key": key
                },
                "deployment_id": deployment_id
            }
            model_list.append(model_deployment)
    
    logger.info(f"Model list length: {len(model_list)}")
    return model_list, api_key_map, api_keys

def proxy_completion(api_keys, **kwargs):
    proxy = swift.get()
    proxy_url = proxy.as_string() if proxy else None
    api_key = random.choice(api_keys)
    model_full = kwargs.pop("model")
    model = model_full.replace("gemini/", "")
    browser_profile = browser_manager.get_profile_for_key(api_key)
    
    proxies = None
    if proxy_url:
        if proxy_url.startswith('socks5://'):
            proxies = {"https": proxy_url, "http": proxy_url}
        else:
            proxies = {"https": proxy_url, "http": proxy_url}
        logger.info(f"Using proxy: {proxy_url} with browser profile: {browser_profile}")
    else:
        logger.info(f"No proxy available, using direct connection with browser profile: {browser_profile}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
        "Origin": "https://ai.google.dev",
        "Referer": "https://ai.google.dev/",
        "Connection": "keep-alive"
    }
    
    payload = {
        "contents": [],
        "generationConfig": {},
        "safetySettings": [],
        "toolConfig": {}
    }
    
    messages = kwargs.pop("messages", [])
    search_context = None
    
    # Handle Google Search tool externally
    if "tools" in kwargs and any("googleSearch" in tool for tool in kwargs["tools"]):
        logger.warning("googleSearchRetrieval is not natively supported; attempting external search or direct model response")
        # Optional: Integrate Google Custom Search API (requires API key)
        # Replace with your Google Search API key and CSE ID
        google_search_api_key = "YOUR_GOOGLE_SEARCH_API_KEY"
        google_cse_id = "YOUR_CUSTOM_SEARCH_ENGINE_ID"
        if google_search_api_key and google_cse_id:
            query = messages[-1]["content"] if messages else ""
            try:
                search_url = f"https://www.googleapis.com/customsearch/v1?key={google_search_api_key}&cx={google_cse_id}&q={query}"
                search_response = requests.get(search_url, proxies=proxies)
                search_response.raise_for_status()
                search_results = search_response.json()
                search_context = "\n".join(item["snippet"] for item in search_results.get("items", [])[:3])
                logger.info(f"Retrieved search context: {search_context[:100]}...")
            except Exception as e:
                logger.error(f"Error fetching Google Search results: {e}")
        # Remove googleSearch tool to avoid API error
        kwargs["tools"] = [tool for tool in kwargs.get("tools", []) if "googleSearch" not in tool]
    
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        
        # Add search context to user message if available
        if search_context and role == "user" and msg is messages[-1]:
            content = f"{content}\n\nSearch context: {search_context}"
        
        if isinstance(content, str):
            gemini_role = "user" if role in ["user", "system"] else "model"
            payload["contents"].append({
                "role": gemini_role,
                "parts": [{"text": content}]
            })
        elif isinstance(content, list):
            gemini_role = "user" if role in ["user", "system"] else "model"
            parts = []
            
            for item in content:
                if item["type"] == "text":
                    parts.append({"text": item["text"]})
                elif item["type"] == "image_url":
                    image_url = item["image_url"]["url"]
                    if image_url.startswith("http"):
                        try:
                            img_response = tls_requests.get(
                                image_url,
                                proxies=proxies,
                                tls_identifier=browser_profile,
                                http2=True
                            )
                            if img_response.status_code == 200:
                                img_data = base64.b64encode(img_response.content).decode('utf-8')
                                parts.append({
                                    "inlineData": {
                                        "mimeType": "image/jpeg",
                                        "data": img_data
                                    }
                                })
                        except Exception as e:
                            logger.error(f"Error fetching image: {e}")
                            parts.append({"text": f"[Image not loaded: {image_url}]"})
                    else:
                        parts.append({
                            "inlineData": {
                                "mimeType": "image/jpeg",
                                "data": image_url
                            }
                        })
            
            payload["contents"].append({
                "role": gemini_role,
                "parts": parts
            })
    
    # Map parameters to generationConfig
    generation_config = payload["generationConfig"]
    for key, value in kwargs.items():
        if key == "temperature":
            generation_config["temperature"] = value
        elif key == "topP":
            generation_config["topP"] = value
        elif key == "topK":
            generation_config["topK"] = value
        elif key == "max_tokens" or key == "maxOutputTokens":
            generation_config["maxOutputTokens"] = value
        elif key == "response_format":
            if value.get("type") == "json_object":
                generation_config["responseMimeType"] = "application/json"
                if "response_schema" in value:
                    generation_config["responseSchema"] = value["response_schema"]
    
    # Handle safety settings
    if "safety_settings" in kwargs:
        sprite["safetySettings"] = kwargs["safety_settings"]
    
    # Handle tools and tool choice
    if "tools" in kwargs and kwargs["tools"]:
        tools = kwargs["tools"]
        gemini_tools = []
        for tool in tools:
            if "function" in tool:
                gemini_tools.append({
                    "functionDeclarations": [{
                        "name": tool["function"]["name"],
                        "description": tool["function"]["description"],
                        "parameters": tool["function"]["parameters"]
                    }]
                })
        if gemini_tools:
            payload["tools"] = gemini_tools
        
        if "tool_choice" in kwargs:
            tool_choice = kwargs["tool_choice"]
            if tool_choice.get("type") == "function":
                payload["toolConfig"] = {
                    "functionCallingConfig": {
                        "mode": "ANY",
                        "allowedFunctionNames": [tool_choice["function"]["name"]]
                    }
                }
    
    # Handle thinking/reasoning effort
    if "reasoning_effort" in kwargs or "thinking" in kwargs:
        logger.warning("Thinking parameter is experimental and not supported in public API; ignoring")
    
    # For image generation
    if "modalities" in kwargs and "image" in kwargs["modalities"]:
        generation_config["responseMimeType"] = "image/png"
    
    # Remove empty toolConfig if not used
    if not payload["toolConfig"]:
        del payload["toolConfig"]
    
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    
    start_time = time.time()
    try:
        response = tls_requests.post(
            api_url,
            json=payload,
            headers=headers,
            proxies=proxies,
            timeout=60,
            tls_identifier=browser_profile,
            http2=True
        )
        response.raise_for_status()
        data = response.json()
        
        content = ""
        finish_reason = "stop"
        tool_calls = None
        
        if "candidates" in data and len(data["candidates"]) > 0:
            candidate = data["candidates"][0]
            
            if "content" in candidate and "parts" in candidate["content"]:
                for part in candidate["content"]["parts"]:
                    if "text" in part:
                        content += part["text"]
                    elif "inlineData" in part:
                        content = part["inlineData"]["data"]
                    elif "functionCall" in part:
                        if tool_calls is None:
                            tool_calls = []
                        func_call = part["functionCall"]
                        tool_calls.append({
                            "id": f"call_{len(tool_calls)}",
                            "type": "function",
                            "function": {
                                "name": func_call.get("name", ""),
                                "arguments": json.dumps(func_call.get("args", {}))
                            }
                        })
            
            if "finishReason" in candidate:
                finish_reason = candidate["finishReason"].lower()
        
        response_obj = CustomCompletion(
            id=data.get("id", f"gemini-{int(time.time())}"),
            object="chat.completion",
            created=int(time.time()),
            model=f"gemini/{model}",
            choices=[{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content,
                    "tool_calls": tool_calls
                },
                "finish_reason": finish_reason
            }],
            usage={
                "prompt_tokens": data.get("usageMetadata", {}).get("promptTokenCount", 0),
                "completion_tokens": data.get("usageMetadata", {}).get("candidatesTokenCount", 0),
                "total_tokens": data.get("usageMetadata", {}).get("totalTokenCount", 0)
            }
        )
        
    except Exception as e:
        logger.error(f"Error making request with TLS fingerprinting: {e}")
        logger.debug(f"Request payload: {json.dumps(payload, indent=2)}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")
    
    end_time = time.time()
    logger.info(f"Request completed using TLS fingerprinting and proxy: {proxy_url}, Time: {end_time - start_time:.2f}s")
    
    return response_obj

# FastAPI startup and shutdown events
@app.on_event("startup")
async def startup_event():
    await initialize_proxies()
    app.state.model_list, app.state.api_key_map, app.state.api_keys = initialize_router()
    app.state.proxy_update_task = asyncio.create_task(update_proxies_periodically())

@app.on_event("shutdown")
async def shutdown_event():
    if hasattr(app.state, "proxy_update_task"):
        app.state.proxy_update_task.cancel()
        try:
            await app.state.proxy_update_task
        except asyncio.CancelledError:
            pass

# FastAPI endpoints
@app.post("/completion")
async def completion(request: CompletionRequest):
    response = proxy_completion(
        api_keys=app.state.api_keys,
        **request.dict(exclude_unset=True)
    )
    return {
        "id": response.id,
        "object": response.object,
        "created": response.created,
        "model": response.model,
        "choices": [{
            "index": choice.index,
            "message": {
                "role": choice.message.role,
                "content": choice.message.content,
                "tool_calls": choice.message.tool_calls
            },
            "finish_reason": choice.finish_reason
        } for choice in response.choices],
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }
    }

@app.post("/image-generation")
async def image_generation(request: ImageGenerationRequest):
    response = proxy_completion(
        api_keys=app.state.api_keys,
        model=request.model,
        messages=[{"role": "user", "content": request.prompt}],
        modalities=request.modalities
    )
    image_data = response.choices[0].message.content
    return {"image_data": image_data}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "proxy_count": len(swift.proxies)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 