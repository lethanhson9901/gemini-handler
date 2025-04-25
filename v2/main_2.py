import asyncio
import base64
import json
import logging
import os
import random
import re
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import google.generativeai as genai

# import litellm # Removed as it's not used directly in this version
import tls_requests
import uvicorn
import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from swiftshadow.classes import ProxyInterface  # Keep if swiftshadow mode is used

# --- Constants ---
CONFIG_FILE_PATH = "../config.yaml" # Relative path to config

# --- Set up logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("api_usage.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("gemini_api")

# --- Global state ---
request_info = {}
request_info_lock = threading.Lock()
app_config = {} # To store loaded config

# --- Initialize SwiftShadow proxy interface (conditionally used) ---
# Initialize SwiftShadow only if needed to avoid unnecessary setup/updates
swift_proxy: Optional[ProxyInterface] = None

# --- FastAPI app ---
app = FastAPI(title="Gemini API Proxy Backend")

# --- Pydantic models (unchanged) ---
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

# --- Browser profile manager (unchanged) ---
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

# --- Custom completion response class (unchanged) ---
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

# --- Configuration Loading ---
def load_config(config_path: str) -> Dict[str, Any]:
    """Loads configuration from a YAML file."""
    if os.path.isabs(config_path):
        full_path = config_path
    else:
        # Assume relative to the script's directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.normpath(os.path.join(script_dir, config_path))

    if not os.path.exists(full_path):
        logger.error(f"Config file not found at: {full_path}")
        raise FileNotFoundError(f"Config file not found at: {full_path}")

    logger.info(f"Loading configuration from: {full_path}")
    with open(full_path, 'r') as f:
        try:
            config = yaml.safe_load(f)
            if config is None:
                config = {}
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file {full_path}: {e}")
            raise ValueError(f"Error parsing YAML file {full_path}: {e}") from e

    # --- Validate Gemini API Keys ---
    api_keys = config.get('gemini', {}).get('api_keys', [])
    if not api_keys or not isinstance(api_keys, list) or not all(isinstance(k, str) for k in api_keys):
        raise ValueError("Config error: 'gemini.api_keys' must be a non-empty list of strings.")
    logger.info(f"Loaded {len(api_keys)} Gemini API keys.")

    # --- Validate Proxy Settings ---
    proxy_config = config.get('proxy', {})
    proxy_mode = proxy_config.get('mode', 'swiftshadow').lower() # Default to swiftshadow
    custom_proxy_list = proxy_config.get('custom_list', [])

    if proxy_mode not in ['swiftshadow', 'custom']:
        logger.warning(f"Invalid proxy mode '{proxy_mode}' in config. Defaulting to 'swiftshadow'.")
        proxy_mode = 'swiftshadow'

    if proxy_mode == 'custom':
        if not custom_proxy_list or not isinstance(custom_proxy_list, list) or not all(isinstance(p, str) for p in custom_proxy_list):
            logger.error("Config error: Proxy mode is 'custom' but 'proxy.custom_list' is missing, empty, or not a list of strings.")
            raise ValueError("Proxy mode is 'custom' but 'proxy.custom_list' is invalid.")
        logger.info(f"Proxy mode set to 'custom'. Loaded {len(custom_proxy_list)} custom proxies.")
    else:
        logger.info("Proxy mode set to 'swiftshadow'.")
        # Ensure custom_proxy_list is empty if not in custom mode
        custom_proxy_list = []

    # Store validated config
    validated_config = {
        'gemini_api_keys': api_keys,
        'proxy_mode': proxy_mode,
        'custom_proxy_list': custom_proxy_list
    }
    return validated_config

# --- Proxy management ---
async def initialize_swiftshadow():
    """Initializes the SwiftShadow instance and loads proxies."""
    global swift_proxy
    logger.info("Initializing SwiftShadow proxy list...")
    swift_proxy = ProxyInterface(autoUpdate=False, autoRotate=True)
    await swift_proxy.async_update()
    logger.info(f"SwiftShadow: Loaded {len(swift_proxy.proxies)} proxies")

async def update_swiftshadow_periodically():
    """Periodically updates the SwiftShadow proxy list."""
    global swift_proxy
    if swift_proxy is None:
        logger.warning("SwiftShadow proxy is not initialized. Cannot start update task.")
        return
    while True:
        logger.info("Updating SwiftShadow proxy list...")
        try:
            await swift_proxy.async_update()
            logger.info(f"Updated SwiftShadow proxy list, now have {len(swift_proxy.proxies)} proxies")
        except Exception as e:
            logger.error(f"Error updating SwiftShadow proxies: {e}")
        await asyncio.sleep(60) # Update every minute

def get_proxy() -> Optional[str]:
    """Selects a proxy based on the configured mode."""
    global swift_proxy
    proxy_mode = app_config.get('proxy_mode', 'swiftshadow')
    custom_proxies = app_config.get('custom_proxy_list', [])

    if proxy_mode == 'custom':
        if not custom_proxies:
            logger.warning("Proxy mode is 'custom' but no custom proxies are loaded. No proxy will be used.")
            return None
        selected_proxy = random.choice(custom_proxies)
        # logger.debug(f"Using custom proxy: {selected_proxy}")
        return selected_proxy
    elif proxy_mode == 'swiftshadow':
        if swift_proxy is None or not swift_proxy.proxies:
            logger.warning("Proxy mode is 'swiftshadow' but it's not initialized or has no proxies. No proxy will be used.")
            return None
        proxy_obj = swift_proxy.get()
        if proxy_obj:
            selected_proxy = proxy_obj.as_string()
            # logger.debug(f"Using SwiftShadow proxy: {selected_proxy}")
            return selected_proxy
        else:
            logger.warning("SwiftShadow returned no available proxy. No proxy will be used.")
            return None
    else:
        # Should not happen due to config validation, but handle defensively
        logger.error(f"Invalid proxy mode encountered: {proxy_mode}. No proxy will be used.")
        return None


# --- Initialize router and API keys ---
def initialize_gemini_models_and_keys(api_keys: List[str]) -> Tuple[List[Dict], Dict[str, str]]:
    """Generates model list and API key map for routing."""
    if not api_keys:
        raise ValueError("Cannot initialize models without API keys.")

    # Use the first key to get available models
    try:
        available_models = get_available_gemini_models(api_keys[0])
        logger.info(f"Found {len(available_models)} Gemini models via API")
    except Exception as e:
        logger.warning(f"Failed to retrieve models via API key {api_keys[0][:4]}...: {e}. Using default model list.")
        # Fallback default list if API call fails
        available_models = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro"] # Added 1.0 pro as a common fallback

    model_list = []
    api_key_map = {}
    for i, key in enumerate(api_keys):
        key_id = f"key{i+1}"
        api_key_map[key] = f"{key_id} (***{key[-4:]})"

    for model_name in available_models:
        # Skip models with specific versioning patterns like -001 or -latest if desired
        if re.search(r'-(00\d|latest)$', model_name):
             logger.debug(f"Skipping versioned model: {model_name}")
             continue

        for i, key in enumerate(api_keys):
            deployment_id = f"{model_name}-key{i+1}"
            with request_info_lock:
                request_info[deployment_id] = {
                    "api_key": key,
                    "friendly_name": api_key_map[key],
                    "model": model_name
                }
            # This structure seems more for LiteLLM router, adapting for direct use
            # We primarily need the list of models and the keys for our proxy_completion
            model_deployment_info = {
                "model_name": f"gemini/{model_name}",
                "api_key": key, # Store key association if needed elsewhere
                "deployment_id": deployment_id # Useful for logging/tracking maybe
            }
            # Avoid duplicate model names in the simple list
            if model_deployment_info["model_name"] not in [m["model_name"] for m in model_list]:
                 model_list.append(model_deployment_info)


    logger.info(f"Generated model list with {len(model_list)} entries based on {len(api_keys)} keys.")
    return model_list, api_key_map

def get_available_gemini_models(api_key: str) -> List[str]:
    """Retrieves available Gemini models using the provided API key."""
    genai.configure(api_key=api_key)
    models = genai.list_models()
    formatted_models = []
    seen_models = set()
    for model in models:
        # Filter for models supported for generative content
        if 'generateContent' in model.supported_generation_methods:
            model_base_name = model.name.split('/')[-1]
            # Further filtering to avoid specific version identifiers if needed
            if re.search(r'-(00\d|latest)$', model_base_name):
                 continue
            if model_base_name not in seen_models:
                formatted_models.append(model_base_name)
                seen_models.add(model_base_name)
    return formatted_models


# --- Proxy completion function (Modified to use get_proxy) ---
def proxy_completion(**kwargs):
    global app_config
    api_keys = app_config.get('gemini_api_keys', [])
    if not api_keys:
        raise HTTPException(status_code=500, detail="No API keys configured.")

    # Select a proxy URL based on config
    proxy_url = get_proxy() # Use the new function

    api_key = random.choice(api_keys)
    model_full = kwargs.pop("model")
    # Ensure we handle models like "gemini/gemini-1.5-pro" or just "gemini-1.5-pro"
    model = model_full.split('/')[-1] # Get the base model name

    browser_profile = browser_manager.get_profile_for_key(api_key)

    proxies = None
    if proxy_url:
        # Standard way tls_requests expects proxies
        proxies = {"http": proxy_url, "https": proxy_url}
        logger.info(f"Using proxy: {proxy_url.split('@')[-1]} with browser profile: {browser_profile}") # Hide creds in log
    else:
        logger.info(f"No proxy configured or available. Using direct connection with browser profile: {browser_profile}")

    headers = {
        # Standard headers - consider if User-Agent needs to match profile more closely
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
        "x-goog-api-client": "genai-python/0.7.1", # Example client info
        "Origin": "https://ai.google.dev", # Keep Origin/Referer for potential checks
        "Referer": "https://ai.google.dev/",
        "Connection": "keep-alive",
        "DNT": "1", # Do Not Track
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site", # Might be 'same-origin' if called from specific contexts
    }

    payload = {
        "contents": [],
        "generationConfig": {},
        "safetySettings": [],
        # "toolConfig": {} # Initialize only if needed
    }

    # --- Payload Construction (largely unchanged, minor fixes) ---
    messages = kwargs.pop("messages", [])
    system_instruction = None # Gemini specific handling for system messages

    # Process messages, extracting system instruction if present
    processed_contents = []
    for msg in messages:
        role = msg.get("role", "user").lower()
        content = msg.get("content")

        if not content: continue # Skip empty messages

        # Gemini specific: System instruction needs separate handling
        if role == "system":
            if isinstance(content, str):
                system_instruction = {"role": "user", "parts": [{"text": content}]} # Treat as first user message part
                logger.debug("Extracted system instruction.")
            else:
                 logger.warning("System message has complex content, treating as regular user message.")
                 role = "user" # Fallback to user role

        # Process user/assistant messages
        if role in ["user", "assistant", "model", "tool"]: # Include 'tool' role for tool responses
            gemini_role = "model" if role in ["assistant", "model"] else role # map assistant to model

            if isinstance(content, str):
                 parts = [{"text": content}]
            elif isinstance(content, list): # Handle multi-modal input (text/image)
                parts = []
                image_fetch_tasks = []
                part_placeholders = []

                for item in content:
                    if isinstance(item, dict) and "type" in item:
                        if item["type"] == "text":
                            parts.append({"text": item["text"]})
                        elif item["type"] == "image_url":
                            image_url_data = item.get("image_url", {})
                            url = image_url_data.get("url")
                            if url:
                                if url.startswith("http"):
                                    # Create a placeholder and schedule fetching
                                    placeholder_index = len(parts)
                                    parts.append(None) # Placeholder
                                    part_placeholders.append((placeholder_index, url))
                                    # Don't run asyncio.create_task here, gather later if needed or run sequentially
                                elif url.startswith("data:image"):
                                    # Handle base64 data URI
                                    try:
                                        mime_type, data = url.split(';base64,')
                                        mime_type = mime_type.split(':')[-1]
                                        # Validate mime type if necessary
                                        if mime_type.startswith("image/"):
                                             parts.append({"inlineData": {"mimeType": mime_type, "data": data}})
                                        else:
                                             logger.warning(f"Unsupported image data URI mime type: {mime_type}")
                                             parts.append({"text": f"[Unsupported image data URI: {mime_type}]"})
                                    except Exception as e:
                                        logger.error(f"Error parsing image data URI: {e}")
                                        parts.append({"text": "[Error processing image data URI]"})
                                else:
                                     logger.warning(f"Unsupported image URL format: {url[:30]}...")
                                     parts.append({"text": f"[Unsupported image format: {url[:30]}...]"})
                            else:
                                logger.warning("Image part missing 'url' in 'image_url'.")
                        # Handle direct base64 data if provided differently (adjust if needed)
                        elif item["type"] == "base64_image":
                            img_data = item.get("data")
                            mime_type = item.get("mime_type", "image/jpeg") # Default mime type
                            if img_data:
                                parts.append({"inlineData": {"mimeType": mime_type, "data": img_data}})
                            else:
                                logger.warning("Base64 image part missing 'data'.")

                # Sequentially fetch HTTP images for simplicity in non-async context
                # For async FastAPI, you could gather these, but sequential is easier here
                for index, url in part_placeholders:
                     try:
                         logger.debug(f"Fetching image URL: {url}")
                         # Use tls_requests for consistency
                         img_response = tls_requests.get(
                             url,
                             proxies=proxies, # Use selected proxy for image fetching too
                             tls_identifier=browser_profile,
                             http2=True,
                             timeout=20 # Add timeout for image fetches
                         )
                         img_response.raise_for_status() # Check for HTTP errors
                         # Determine mime type from response header if possible, else default
                         content_type = img_response.headers.get('Content-Type', 'image/jpeg')
                         img_data = base64.b64encode(img_response.content).decode('utf-8')
                         parts[index] = {"inlineData": {"mimeType": content_type, "data": img_data}}
                     except Exception as e:
                         logger.error(f"Error fetching image {url}: {e}")
                         parts[index] = {"text": f"[Image failed to load: {url.split('/')[-1]}]"} # Replace placeholder with error text


            else:
                 logger.warning(f"Unsupported content type for role {role}: {type(content)}")
                 parts = [{"text": "[Unsupported content format]"}]

            # Filter out None placeholders if image fetching failed badly
            final_parts = [p for p in parts if p is not None]
            if final_parts:
                 processed_contents.append({"role": gemini_role, "parts": final_parts})

        # Handle tool calls / function results
        elif role == "tool":
            tool_calls = msg.get("tool_calls")
            if tool_calls and isinstance(tool_calls, list):
                 # Assuming Gemini expects tool results in a specific format
                 # This might need adjustment based on actual Gemini API for tool results
                 # Often, you'd send back a 'function' response part.
                 # Let's assume the content field holds the result string for now
                 # Gemini v1.5 expects function results within parts, role 'function' (or 'tool')
                 # Example structure - NEEDS VERIFICATION with Gemini docs
                 for call in tool_calls:
                     call_id = call.get("id") # Need the ID from the previous assistant turn
                     function_name = call.get("function",{}).get("name")
                     # Assume 'content' holds the JSON string result from the tool execution
                     result_content = str(content) # Ensure it's a string
                     if call_id and function_name:
                         processed_contents.append({
                             "role": "function", # Or maybe "tool"? Check Gemini docs
                             "parts": [{
                                 "functionResponse": {
                                     "name": function_name,
                                     # Response content structure depends on API version
                                     "response": {"content": result_content} # Adjust as needed
                                 }
                             }]
                         })
                     else:
                         logger.warning(f"Skipping tool result due to missing id/name: {call}")
            else:
                 logger.warning(f"Tool role message has unexpected content/tool_calls format: {msg}")


    # Prepend system instruction if it exists
    if system_instruction:
        # Check if first message is already the system instruction text
        if not (processed_contents and processed_contents[0]['role'] == 'user' and processed_contents[0]['parts'] == system_instruction['parts']):
             payload["contents"] = [system_instruction] + processed_contents
             # Gemini specific system instruction field (use if available/preferred)
             # payload["systemInstruction"] = system_instruction
        else:
             payload["contents"] = processed_contents # Already included
    else:
        payload["contents"] = processed_contents


    # Map parameters to generationConfig
    generation_config = payload.setdefault("generationConfig", {}) # Use setdefault
    safety_settings = payload.setdefault("safetySettings", [])

    # Parameter mapping (more robust)
    if "temperature" in kwargs: generation_config["temperature"] = kwargs["temperature"]
    if "topP" in kwargs: generation_config["topP"] = kwargs["topP"]
    if "topK" in kwargs: generation_config["topK"] = kwargs["topK"]
    if "max_tokens" in kwargs: generation_config["maxOutputTokens"] = kwargs["max_tokens"]
    # Allow direct Gemini param name too
    if "maxOutputTokens" in kwargs: generation_config["maxOutputTokens"] = kwargs["maxOutputTokens"]
    if "stop" in kwargs or "stopSequences" in kwargs:
        stop_sequences = kwargs.get("stop") or kwargs.get("stopSequences", [])
        if isinstance(stop_sequences, str): stop_sequences = [stop_sequences]
        if isinstance(stop_sequences, list): generation_config["stopSequences"] = stop_sequences

    # Handle response format (JSON mode)
    if "response_format" in kwargs and isinstance(kwargs["response_format"], dict):
        response_format = kwargs["response_format"]
        if response_format.get("type") == "json_object":
            generation_config["responseMimeType"] = "application/json"
            logger.info("JSON response format requested.")
            # Gemini schema support (if provided)
            # if "response_schema" in response_format:
            #    generation_config["responseSchema"] = response_format["response_schema"]

    # Handle safety settings
    if "safety_settings" in kwargs and isinstance(kwargs["safety_settings"], list):
         # Basic validation of structure
        valid_settings = []
        for setting in kwargs["safety_settings"]:
             if isinstance(setting, dict) and "category" in setting and "threshold" in setting:
                 valid_settings.append(setting)
             else:
                 logger.warning(f"Ignoring invalid safety setting: {setting}")
        if valid_settings:
            payload["safetySettings"] = valid_settings # Overwrite default empty list

    # Handle tools and tool choice
    if "tools" in kwargs and kwargs["tools"] and isinstance(kwargs["tools"], list):
        gemini_tools = []
        has_google_search = False
        for tool in kwargs["tools"]:
            if isinstance(tool, dict) and tool.get("type") == "function" and "function" in tool:
                func_spec = tool["function"]
                # Basic validation of function spec
                if "name" in func_spec and "description" in func_spec and "parameters" in func_spec:
                    gemini_tools.append({
                        "functionDeclarations": [{
                            "name": func_spec["name"],
                            "description": func_spec["description"],
                            "parameters": func_spec["parameters"] # Assumes OpenAI schema compatible
                        }]
                    })
                else:
                    logger.warning(f"Ignoring invalid function tool specification: {tool}")
            elif isinstance(tool, dict) and tool.get("type") == "google_search_retrieval":
                 # Gemini has built-in grounding, activated differently
                 logger.warning("google_search_retrieval tool type is specified but might require specific Gemini grounding configuration, not just a tool declaration.")
                 # Add Google Search tool explicitly if needed for some models/versions
                 # gemini_tools.append({"googleSearchRetrieval": {}}) # Example structure - CHECK DOCS
                 has_google_search = True

        if gemini_tools:
            payload["tools"] = gemini_tools
            logger.info(f"Included {len(gemini_tools)} function declarations in the request.")

        # Handle tool choice (forcing a specific function)
        if "tool_choice" in kwargs:
            tool_choice = kwargs["tool_choice"]
            # Allow string "auto" (default), "none", or object for specific function
            if isinstance(tool_choice, str):
                 if tool_choice == "none":
                     payload.setdefault("toolConfig", {})["functionCallingConfig"] = {"mode": "NONE"}
                 elif tool_choice == "any" or tool_choice == "auto": # Gemini uses ANY or AUTO
                      payload.setdefault("toolConfig", {})["functionCallingConfig"] = {"mode": "AUTO"} # Default, maybe ANY if forcing
                 else: # Treat as function name if just a string
                     payload.setdefault("toolConfig", {})["functionCallingConfig"] = {
                         "mode": "ANY", # Force calling *a* function
                         "allowedFunctionNames": [tool_choice]
                     }
            elif isinstance(tool_choice, dict) and tool_choice.get("type") == "function":
                func_choice = tool_choice.get("function")
                if func_choice and "name" in func_choice:
                     payload.setdefault("toolConfig", {})["functionCallingConfig"] = {
                         "mode": "ANY", # Force calling *a* function
                         "allowedFunctionNames": [func_choice["name"]]
                     }
                     logger.info(f"Tool choice configured to force function: {func_choice['name']}")


    # Handle thinking/reasoning effort (Experimental/Not Standard)
    if "reasoning_effort" in kwargs or "thinking" in kwargs:
        logger.warning("Thinking/reasoning parameters are experimental or not standard Gemini API features; ignoring.")

    # Image Generation Specifics (Modalities check is more relevant for input)
    # If the *model name* indicates image generation, set response MIME type
    # Example model name: gemini-pro-vision, imagen-3 ... adjust as needed
    if "imagen" in model or "image" in model or model.endswith("-vision"): # Heuristic check
         # Find the part containing the prompt text
         prompt_text = ""
         for item in payload.get("contents", [])[0].get("parts",[]): # Assume prompt in first message
             if "text" in item:
                 prompt_text = item["text"]
                 break
         if prompt_text and "generateImage" not in payload : # Check if specific image payload needed
              # This payload structure might be entirely different for Imagen models
              # The current structure is for generateContent (text/multimodal)
              # Image generation often uses a different endpoint or payload structure.
              # For now, we log a warning. Needs specific logic for image models.
              logger.warning(f"Model '{model}' seems to be for image generation. The current payload structure is for text/multimodal. Image generation might fail or require a different API call/payload.")
              # Example: payload = {"prompt": {"text": prompt_text}, "model": model_full}
              # If using generateContent with specific response type:
              # generation_config["responseMimeType"] = "image/png" # or jpeg etc.
              # logger.info("Image generation requested via response MIME type.")


    # Clean up empty sections
    if not payload.get("safetySettings"): del payload["safetySettings"]
    if not payload.get("generationConfig"): del payload["generationConfig"]
    if "toolConfig" in payload and not payload["toolConfig"].get("functionCallingConfig"):
        del payload["toolConfig"]
    if "tools" in payload and not payload["tools"]:
         del payload["tools"]

    # API Endpoint URL construction
    # Use v1beta generally as it often has newer features
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    # Handle specific models that might use v1 (e.g., older stable models)
    # if model in ["gemini-1.0-pro", ...]: api_url = f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent"

    logger.debug(f"Sending request to: {api_url}")
    # logger.debug(f"Request payload: {json.dumps(payload, indent=2)}") # Careful logging PII

    start_time = time.time()
    response_obj = None
    try:
        raw_response = tls_requests.post(
            api_url,
            json=payload,
            headers=headers,
            proxies=proxies,
            timeout=120, # Increased timeout for potentially long generations
            tls_identifier=browser_profile,
            http2=True,
            pseudo_header_order=[":method", ":authority", ":scheme", ":path", "accept", "accept-encoding", "accept-language", "content-type", "origin", "referer", "sec-fetch-dest", "sec-fetch-mode", "sec-fetch-site", "user-agent", "x-goog-api-client", "x-goog-api-key"] # Common order
        )

        # Log status code and headers for debugging if needed
        logger.debug(f"Response Status Code: {raw_response.status_code}")
        # logger.debug(f"Response Headers: {raw_response.headers}")

        raw_response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        data = raw_response.json()
        # logger.debug(f"Response JSON data: {json.dumps(data, indent=2)}")

        # --- Process Response ---
        content = ""
        finish_reason = "stop" # Default
        tool_calls = None # Initialize tool_calls list

        # Check for response structure variations
        if "candidates" in data and data["candidates"]:
            candidate = data["candidates"][0] # Usually take the first candidate

            # --- Extract Content ---
            if "content" in candidate and "parts" in candidate["content"]:
                response_parts = candidate["content"].get("parts", [])
                for part in response_parts:
                    if "text" in part:
                        content += part["text"]
                    elif "inlineData" in part:
                        # Assuming image data if inlineData is present
                        content = part["inlineData"]["data"] # Return base64 data directly
                        logger.info(f"Received inline data (image?) with MIME type: {part['inlineData'].get('mimeType')}")
                        # Should probably set a flag indicating image data vs text
                    elif "functionCall" in part:
                        # Handle function call requests from the model
                        if tool_calls is None: tool_calls = []
                        func_call = part["functionCall"]
                        # Map to OpenAI-like tool_calls structure
                        tool_calls.append({
                            "id": f"call_{random.randint(1000, 9999)}_{len(tool_calls)}", # Generate an ID
                            "type": "function",
                            "function": {
                                "name": func_call.get("name", ""),
                                # Gemini args are often directly objects, dump to JSON string
                                "arguments": json.dumps(func_call.get("args", {}))
                            }
                        })
                        # If function call exists, finish reason is often TOOL_USE
                        finish_reason = "tool_calls" # Map Gemini's reason if available, else assume

            # --- Determine Finish Reason ---
            gemini_finish_reason = candidate.get("finishReason", "STOP").upper()
            # Map Gemini reasons to OpenAI-like reasons
            reason_map = {
                "STOP": "stop",
                "MAX_TOKENS": "length",
                "SAFETY": "content_filter",
                "RECITATION": "content_filter", # Often related to safety/copyright
                "TOOL_CODE": "tool_calls", # If finish reason indicates tool use explicitly
                "FUNCTION_CALL": "tool_calls", # Alternative naming
                "OTHER": "stop", # Default fallback
                "UNKNOWN": "stop", # Default fallback
                "UNSPECIFIED": "stop" # Default fallback
            }
            finish_reason = reason_map.get(gemini_finish_reason, "stop")
            # If we detected tool calls in parts, override finish reason
            if tool_calls is not None and finish_reason != "tool_calls":
                logger.debug(f"Overriding finish reason to 'tool_calls' based on detected functionCall part (Original: {gemini_finish_reason})")
                finish_reason = "tool_calls"


        elif "promptFeedback" in data:
             # Handle cases where the request was blocked before generation
             block_reason = data["promptFeedback"].get("blockReason")
             logger.warning(f"Request blocked due to prompt feedback: {block_reason}")
             # You might want to raise an specific error or return a custom message
             raise HTTPException(status_code=400, detail=f"Request blocked by safety filters: {block_reason}")

        # --- Calculate Usage ---
        usage_metadata = data.get("usageMetadata", {})
        prompt_tokens = usage_metadata.get("promptTokenCount", 0)
        completion_tokens = usage_metadata.get("candidatesTokenCount", 0) # Tokens in the response
        total_tokens = usage_metadata.get("totalTokenCount", 0)
         # Sometimes completion tokens are per-candidate, sum if needed
        if not completion_tokens and "candidates" in data:
             completion_tokens = sum(c.get("tokenCount", 0) for c in data["candidates"])
             if not total_tokens: total_tokens = prompt_tokens + completion_tokens


        response_obj = CustomCompletion(
            id=f"gemini-{int(time.time())}-{random.randint(100, 999)}", # More unique ID
            object="chat.completion",
            created=int(time.time()),
            model=f"gemini/{model}", # Return the specific model used
            choices=[{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content if not tool_calls else None, # Content is None if tool_calls present
                    "tool_calls": tool_calls # Include tool_calls if generated
                },
                "finish_reason": finish_reason
            }],
            usage={
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens
            }
        )

    except tls_requests.exceptions.RequestException as e:
        logger.error(f"TLS Request failed: {e}")
        # Log request details (optional, be careful with sensitive data)
        # logger.debug(f"Failed Request Payload: {json.dumps(payload, indent=2)}")
        raise HTTPException(status_code=502, detail=f"Proxy or Network Error: {str(e)}")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON response: {e}")
        logger.debug(f"Raw Response Text: {raw_response.text[:500]}") # Log part of the raw text
        raise HTTPException(status_code=500, detail="Invalid JSON response from API")
    except Exception as e:
        # Catch other potential errors (e.g., key errors in response processing)
        logger.exception(f"An unexpected error occurred during proxy completion: {e}") # Use exception for stack trace
        # logger.debug(f"Request Payload causing error: {json.dumps(payload, indent=2)}")
        # logger.debug(f"Raw Response causing error (if available): {raw_response.text[:500] if 'raw_response' in locals() else 'N/A'}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

    end_time = time.time()
    proxy_info = f"proxy: {proxy_url.split('@')[-1]}" if proxy_url else "direct connection" # Hide creds
    logger.info(f"Request completed ({response_obj.model}). Time: {end_time - start_time:.2f}s. Finish: '{response_obj.choices[0].finish_reason}'. Usage: P{response_obj.usage.prompt_tokens} C{response_obj.usage.completion_tokens}. Via: {proxy_info}.")

    return response_obj

# --- FastAPI startup and shutdown events ---
@app.on_event("startup")
async def startup_event():
    global app_config, swift_proxy
    try:
        app_config = load_config(CONFIG_FILE_PATH)
        app.state.gemini_api_keys = app_config['gemini_api_keys']

        # Initialize models based on loaded keys
        app.state.model_list, app.state.api_key_map = initialize_gemini_models_and_keys(app.state.gemini_api_keys)
        logger.info(f"Initialized with {len(app.state.model_list)} model configurations.")

        # Conditionally initialize and update SwiftShadow
        if app_config['proxy_mode'] == 'swiftshadow':
            await initialize_swiftshadow()
            if swift_proxy: # Ensure initialization was successful
                app.state.proxy_update_task = asyncio.create_task(update_swiftshadow_periodically())
                logger.info("Started periodic SwiftShadow proxy updates.")
            else:
                 logger.error("SwiftShadow failed to initialize. Proxy functionality will be limited.")
        else:
            logger.info("Running in 'custom' proxy mode. SwiftShadow updates are disabled.")
            app.state.proxy_update_task = None # Ensure no task is stored

    except (FileNotFoundError, ValueError) as e:
        logger.critical(f"CRITICAL ERROR during startup: {e}. Application might not function correctly.")
        # Optionally, raise the error to prevent FastAPI from starting fully
        # raise RuntimeError(f"Startup failed due to configuration error: {e}") from e
        # Or exit:
        import sys
        sys.exit(f"Startup failed: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down API server...")
    if hasattr(app.state, "proxy_update_task") and app.state.proxy_update_task:
        logger.info("Cancelling proxy update task...")
        app.state.proxy_update_task.cancel()
        try:
            await app.state.proxy_update_task
        except asyncio.CancelledError:
            logger.info("Proxy update task cancelled successfully.")
        except Exception as e:
             logger.error(f"Error during proxy update task cancellation: {e}")
    logger.info("Shutdown complete.")

# --- FastAPI endpoints ---
@app.post("/v1/chat/completions") # Match OpenAI endpoint style
@app.post("/completion") # Keep original endpoint for compatibility
async def completion(request: CompletionRequest):
    # Add mapping from OpenAI params if necessary, Pydantic model handles most
    # Note: stream is not implemented here
    if hasattr(request, 'stream') and request.stream:
        raise HTTPException(status_code=400, detail="Streaming responses are not supported.")

    try:
        response = proxy_completion(
            # Pass relevant parameters from request.
            # model_dump ensures we pass values even if default
            **request.model_dump(exclude_unset=False) # Pass all defined fields, including defaults
        )

        # Format response to match OpenAI structure
        return {
            "id": response.id,
            "object": response.object,
            "created": response.created,
            "model": response.model, # Use the model returned by the custom class
            "choices": [{
                "index": choice.index,
                "message": {
                    "role": choice.message.role,
                    # Conditionally include content or tool_calls
                    **({"content": choice.message.content} if choice.message.content is not None else {}),
                    **({"tool_calls": choice.message.tool_calls} if choice.message.tool_calls else {}),
                },
                "logprobs": None, # Not supported by Gemini API directly
                "finish_reason": choice.finish_reason
            } for choice in response.choices],
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            },
            # "system_fingerprint": None # Not provided by Gemini
        }
    except HTTPException as e:
         # Re-raise FastAPI HTTP exceptions
         raise e
    except Exception as e:
         logger.exception("Error during completion request processing.") # Log full trace
         raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")


# Image generation endpoint needs refinement - assumes proxy_completion can handle it
@app.post("/v1/images/generations") # Match OpenAI endpoint style
@app.post("/image-generation") # Keep original endpoint
async def image_generation(request: ImageGenerationRequest):
    # This endpoint currently assumes the `proxy_completion` function
    # can handle image generation models/payloads correctly.
    # This might require significant changes in `proxy_completion`
    # or a dedicated function/API call for image models (like Imagen).

    logger.warning("Image generation endpoint is experimental and may not work correctly with all models or payload structures.")

    try:
        # Construct arguments for proxy_completion based on ImageGenerationRequest
        # The current proxy_completion expects 'messages' format primarily.
        # We need to adapt or create a dedicated path.
        # Simplistic adaptation for now:
        image_gen_args = {
             "model": request.model, # e.g., "gemini/gemini-2.0-flash-exp-image-generation"
             "messages": [{"role": "user", "content": request.prompt}], # Basic prompt mapping
             # Image models might not use these text-gen params:
             # "temperature": 0.7, # Defaults might differ for images
             # "max_tokens": None, # Usually not applicable
        }

        # Add modalities if the proxy_completion function uses it
        # image_gen_args["modalities"] = request.modalities

        response = proxy_completion(**image_gen_args)

        # Process the response assuming it contains image data
        # The CustomCompletion class stores data in choices[0].message.content
        if response.choices and response.choices[0].message.content:
            image_data_base64 = response.choices[0].message.content
            # Check if it looks like base64 data
            if isinstance(image_data_base64, str) and len(image_data_base64) > 100:
                # OpenAI image generation returns a list of objects, each with b64_json
                return {
                    "created": response.created,
                    "data": [
                        {
                            "b64_json": image_data_base64,
                            # "url": None, # URL not typically returned directly this way
                            # "revised_prompt": None # Not supported
                         }
                    ]
                }
            else:
                 logger.error(f"Image generation response content was not valid base64 data: {str(response.choices[0].message.content)[:100]}")
                 raise HTTPException(status_code=500, detail="Image generation succeeded but returned invalid data format.")
        else:
             logger.error("Image generation response did not contain expected content.")
             raise HTTPException(status_code=500, detail="Image generation failed or returned no data.")

    except HTTPException as e:
         raise e
    except Exception as e:
         logger.exception("Error during image generation request.")
         raise HTTPException(status_code=500, detail=f"An internal error occurred during image generation: {str(e)}")


@app.get("/health")
async def health_check():
    proxy_mode = app_config.get('proxy_mode', 'unknown')
    proxy_count = 0
    status = "healthy"
    details = {}

    if proxy_mode == 'swiftshadow':
        if swift_proxy:
            proxy_count = len(swift_proxy.proxies)
            details['swiftshadow_proxies'] = proxy_count
        else:
            status = "degraded"
            details['swiftshadow_status'] = 'not initialized'
    elif proxy_mode == 'custom':
        proxy_count = len(app_config.get('custom_proxy_list', []))
        details['custom_proxies'] = proxy_count
        if proxy_count == 0:
            status = "degraded"
            details['warning'] = 'Custom proxy mode selected but no proxies loaded.'

    details['gemini_keys_loaded'] = len(app_config.get('gemini_api_keys', []))
    if not app_config.get('gemini_api_keys'):
        status = "unhealthy"
        details['error'] = 'No Gemini API keys loaded.'


    return {"status": status, "proxy_mode": proxy_mode, **details}

@app.get("/v1/models") # OpenAI compatible models endpoint
async def get_models():
     # Return the list of models prepared during initialization
     models_data = []
     if hasattr(app.state, 'model_list'):
         for model_info in app.state.model_list:
             model_id = model_info.get("model_name") # e.g., "gemini/gemini-1.5-pro"
             if model_id:
                 models_data.append({
                     "id": model_id,
                     "object": "model",
                     "created": int(time.time()), # Placeholder timestamp
                     "owned_by": "google",
                     # Add more metadata if available/needed
                 })
     else:
         # Fallback or error if models not loaded
         logger.warning("Model list not found in app state for /v1/models endpoint.")
         # Return a minimal default list or error?
         # Example minimal:
         return {
             "object": "list",
             "data": [
                 {"id": "gemini/gemini-1.5-pro", "object": "model", "created": int(time.time()), "owned_by": "google"},
                 {"id": "gemini/gemini-1.5-flash", "object": "model", "created": int(time.time()), "owned_by": "google"}
             ]
         }


     return {"object": "list", "data": models_data}


# --- Main execution ---
if __name__ == "__main__":
    # Basic check for config file before starting server
    try:
        # Try loading config early to catch immediate errors
        _ = load_config(CONFIG_FILE_PATH)
        logger.info("Configuration loaded successfully for pre-check.")
    except Exception as e:
        logger.critical(f"Failed to load configuration '{CONFIG_FILE_PATH}' before starting server: {e}")
        import sys
        sys.exit(1) # Exit if config is fundamentally broken

    # Get host/port from environment variables or defaults
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))

    logger.info(f"Starting Uvicorn server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)