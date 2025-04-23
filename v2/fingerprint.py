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
from typing import Any, Dict, List, Optional

import google.generativeai as genai
import litellm
import tls_requests
import yaml
from litellm import Router
from swiftshadow.classes import ProxyInterface

# Set up minimal logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("api_usage.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("gemini_api")

# Global dict to store API key information for each request
request_info = {}
request_info_lock = threading.Lock()

# Initialize SwiftShadow proxy interface
swift = ProxyInterface(autoUpdate=False, autoRotate=True)

# Initialize the proxy list
async def initialize_proxies():
    """Initialize the proxy list at startup"""
    logger.info("Initializing proxy list...")
    await swift.async_update()
    logger.info(f"Loaded {len(swift.proxies)} proxies")

# Run the initialization
loop = asyncio.get_event_loop()
loop.run_until_complete(initialize_proxies())

# Background task to update proxies periodically
async def update_proxies_periodically():
    """Update proxies every 5 minutes"""
    while True:
        logger.info("Updating proxy list...")
        await swift.async_update()
        logger.info(f"Updated proxy list, now have {len(swift.proxies)} proxies")
        await asyncio.sleep(300)  # 5 minutes

# Start the background task for proxy updates
proxy_update_task = asyncio.ensure_future(update_proxies_periodically())

# Browser profile manager
class BrowserProfileManager:
    """Manages browser profiles for TLS fingerprinting"""
    
    def __init__(self):
        self.profiles = [
            "chrome_103", "chrome_104", "chrome_105", "chrome_106", "chrome_107", "chrome_108",
            "chrome_109", "chrome_110", "chrome_111", "chrome_112", "firefox_102", "firefox_104",
            "safari_15_3", "safari_15_6_1", "safari_16_0", "opera_89", "opera_90"
        ]
        self.api_key_profiles = {}
        self.profile_lock = threading.Lock()
    
    def get_profile_for_key(self, api_key):
        """Get a consistent browser profile for a specific API key"""
        with self.profile_lock:
            if api_key not in self.api_key_profiles:
                # Hash the API key to get a consistent index
                hash_value = hash(api_key) % len(self.profiles)
                self.api_key_profiles[api_key] = self.profiles[hash_value]
            
            return self.api_key_profiles[api_key]

# Initialize the browser profile manager
browser_manager = BrowserProfileManager()

# Create a custom completion response class
class CustomCompletion:
    """Custom class to mimic LiteLLM completion response"""
    
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

def get_available_gemini_models(api_key: str) -> List[str]:
    """Get all available Gemini models using the Google API."""
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
    """Generate a model list for LiteLLM Router from a config file containing Gemini API keys."""
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
    print(f"Found {len(available_models)} Gemini models")
    
    model_list = []
    
    # Create API key mapping with friendly names
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
    print("Model list length: ", len(model_list))

    return model_list, api_key_map, api_keys  # Return the API keys too

# Disable detailed logging for litellm
os.environ['LITELLM_LOG'] = 'ERROR'

class TrackedRouter(Router):
    """Custom Router that tracks and logs which API key and model is being used, with proxy support"""
    
    def __init__(self, *args, api_key_map=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_key_map = api_key_map or {}
        self.deployment_callback = self._track_deployment_callback
    
    def _track_deployment_callback(self, kwargs, response_obj):
        """Custom callback to track which deployment was used"""
        try:
            deployment_id = kwargs.get("litellm_params", {}).get("metadata", {}).get("deployment_id")
            
            if deployment_id:
                thread_id = threading.get_ident()
                with request_info_lock:
                    if thread_id not in request_info:
                        request_info[thread_id] = {}
                    request_info[thread_id]["deployment_id"] = deployment_id
        except Exception as e:
            print(f"Error tracking deployment: {e}")
    
    def completion(self, model, messages, *args, **kwargs):
        thread_id = threading.get_ident()
        with request_info_lock:
            request_info[thread_id] = {"last_model": model}
        
        # Add metadata to track which deployment is used
        if "metadata" not in kwargs:
            kwargs["metadata"] = {}
        
        # Get a proxy from SwiftShadow
        proxy = swift.get()
        proxy_url = proxy.as_string() if proxy else None
        
        if proxy_url:
            # Configure proxy for this request
            if "additional_args" not in kwargs:
                kwargs["additional_args"] = {}
            kwargs["additional_args"]["proxy"] = proxy_url
            print(f"Using proxy: {proxy_url}")
        else:
            print("No proxy available, using direct connection")
        
        # Call the parent method to make the actual request
        start_time = time.time()
        response = super().completion(model=model, messages=messages, *args, **kwargs)
        end_time = time.time()
        
        # Extract deployment info for logging
        used_deployment_id = None
        
        # Try to get from thread-local storage
        with request_info_lock:
            thread_data = request_info.get(thread_id, {})
            used_deployment_id = thread_data.get("deployment_id")
        
        # Get API key info
        api_key_info = "unknown"
        if used_deployment_id and used_deployment_id in request_info:
            api_key_info = request_info[used_deployment_id].get("friendly_name", "unknown")
        
        # Log the API key information and proxy used
        print(f"Request completed using: {api_key_info}, Proxy: {proxy_url}, Time: {end_time - start_time:.2f}s")
        
        return response

# Initialize the router and get API keys
print("Initializing router...")
model_list, api_key_map, api_keys = auto_generate_model_list("../config.yaml")
router = TrackedRouter(model_list=model_list, api_key_map=api_key_map)

# Function to make a completion with proxy and TLS fingerprinting
def proxy_completion(*args, **kwargs):
    """Make a completion request through a proxy with TLS fingerprinting"""
    # Get a proxy from SwiftShadow
    proxy = swift.get()
    proxy_url = proxy.as_string() if proxy else None
    
    # Store original args for fallback
    original_args = args
    original_kwargs = kwargs.copy()
    
    # Make sure we have an API key
    if "api_key" not in kwargs:
        # Use a random API key from our list
        kwargs["api_key"] = random.choice(api_keys)
    
    api_key = kwargs.pop("api_key")
    model_full = kwargs.pop("model")
    model = model_full.replace("gemini/", "")
    
    # Get browser profile for this API key
    browser_profile = browser_manager.get_profile_for_key(api_key)
    
    # Prepare proxy configuration for TLS-Requests
    proxies = None
    if proxy_url:
        if proxy_url.startswith('socks5://'):
            proxies = {"https": proxy_url, "http": proxy_url}
        else:
            # For HTTP/HTTPS proxies
            proxies = {"https": proxy_url, "http": proxy_url}
        print(f"Using proxy: {proxy_url} with browser profile: {browser_profile}")
    else:
        print(f"No proxy available, using direct connection with browser profile: {browser_profile}")
    
    # Add realistic browser headers
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
    
    # Prepare the request payload
    payload = {
        "contents": [],
        "generationConfig": {}
    }
    
    # Convert messages to Gemini format
    messages = kwargs.pop("messages", [])
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        
        # Handle different content types (text or complex with images)
        if isinstance(content, str):
            # Simple text content
            gemini_role = "user" if role == "user" else "model"
            payload["contents"].append({
                "role": gemini_role,
                "parts": [{"text": content}]
            })
        elif isinstance(content, list):
            # Complex content with possible images
            gemini_role = "user" if role == "user" else "model"
            parts = []
            
            for item in content:
                if item["type"] == "text":
                    parts.append({"text": item["text"]})
                elif item["type"] == "image_url":
                    # Handle image URLs by converting to base64 if needed
                    image_url = item["image_url"]["url"]
                    if image_url.startswith("http"):
                        try:
                            # Fetch the image using TLS-Requests with browser fingerprinting
                            img_response = tls_requests.get(
                                image_url, 
                                proxies=proxies, 
                                tls_identifier=browser_profile,
                                http2=True
                            )
                            if img_response.status_code == 200:
                                img_data = base64.b64encode(img_response.content).decode('utf-8')
                                parts.append({
                                    "inline_data": {
                                        "mime_type": "image/jpeg",
                                        "data": img_data
                                    }
                                })
                        except Exception as e:
                            print(f"Error fetching image: {e}")
                            # Fall back to direct URL if fetching fails
                            parts.append({
                                "inline_data": {
                                    "mime_type": "image/jpeg",
                                    "data": image_url
                                }
                            })
                    else:
                        # Already a base64 string
                        parts.append({
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": image_url
                            }
                        })
            
            payload["contents"].append({
                "role": gemini_role,
                "parts": parts
            })
    
    # Add other parameters to generationConfig
    for key, value in kwargs.items():
        if key == "temperature":
            payload["generationConfig"]["temperature"] = value
        elif key == "topP":
            payload["generationConfig"]["topP"] = value
        elif key == "topK":
            payload["generationConfig"]["topK"] = value
        elif key == "max_tokens" or key == "maxOutputTokens":
            payload["generationConfig"]["maxOutputTokens"] = value
        elif key == "safety_settings":
            payload["safetySettings"] = value
        elif key == "tools":
            if "googleSearch" in str(value):
                payload["tools"] = [{"googleSearchRetrieval": {}}]
            else:
                payload["tools"] = value
        elif key == "tool_choice":
            payload["toolConfig"] = {"toolChoice": value}
        elif key == "reasoning_effort" or key == "thinking":
            if key == "reasoning_effort":
                if value == "high":
                    budget_tokens = 2048
                elif value == "medium":
                    budget_tokens = 1024
                else:
                    budget_tokens = 512
            else:
                budget_tokens = value.get("budget_tokens", 1024)
            
            payload["generationConfig"]["thinking"] = {
                "type": "enabled",
                "budget_tokens": budget_tokens
            }
    
    # Handle response format JSON mode
    if "response_format" in kwargs:
        response_format = kwargs["response_format"]
        if response_format.get("type") == "json_object":
            payload["generationConfig"]["responseMimeType"] = "application/json"
            
            # Add schema if provided
            if "response_schema" in response_format:
                payload["generationConfig"]["responseSchema"] = response_format["response_schema"]
    
    # Prepare the API URL
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    
    # Make the request with TLS fingerprinting
    start_time = time.time()
    try:
        # Use tls_requests.post with the browser profile
        response = tls_requests.post(
            api_url,
            json=payload,
            headers=headers,
            proxies=proxies,
            timeout=60,
            tls_identifier=browser_profile,  # This is the key parameter for TLS fingerprinting
            http2=True  # Enable HTTP/2 for better fingerprinting
        )
        response.raise_for_status()
        data = response.json()
        
        # Parse the response
        content = ""
        finish_reason = "stop"
        
        if "candidates" in data and len(data["candidates"]) > 0:
            candidate = data["candidates"][0]
            
            if "content" in candidate and "parts" in candidate["content"]:
                # Extract text content
                for part in candidate["content"]["parts"]:
                    if "text" in part:
                        content += part["text"]
            
            # Handle finish reason
            if "finishReason" in candidate:
                finish_reason = candidate["finishReason"].lower()
        
        # Handle tool calls if present
        tool_calls = None
        if "candidates" in data and len(data["candidates"]) > 0:
            candidate = data["candidates"][0]
            if "content" in candidate and "parts" in candidate["content"]:
                for part in candidate["content"]["parts"]:
                    if "functionCall" in part:
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
        
        # Convert the Gemini response to a custom response object
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
        print(f"Error making request with TLS fingerprinting: {e}")
        print("Falling back to standard LiteLLM...")
        # Fall back to LiteLLM if our direct implementation fails
        # Need to restore the original parameters for the fallback
        response_obj = litellm.completion(model=original_kwargs.get("model"), messages=original_kwargs.get("messages", []), api_key=api_key, **{k: v for k, v in original_kwargs.items() if k not in ["model", "messages", "api_key"]})
    
    end_time = time.time()
    print(f"Request completed using TLS fingerprinting and proxy: {proxy_url}, Time: {end_time - start_time:.2f}s")
    
    return response_obj

# Example usage functions demonstrating different Gemini features

def example_basic_completion():
    """Basic text completion example"""
    print("\n--- Basic Completion Example ---")
    try:
        response = proxy_completion(
            model="gemini/gemini-2.0-flash",
            messages=[{"role": "user", "content": "Write a short poem about AI"}],
            temperature=0.7
        )
        print(f"Response: {response.choices[0].message.content}")
    except Exception as e:
        print(f"Error: {e}")

def example_json_mode():
    """JSON mode example"""
    print("\n--- JSON Mode Example ---")
    try:
        messages = [
            {
                "role": "user",
                "content": "List 3 popular cookie recipes with their ingredients."
            }
        ]
        
        response = proxy_completion(
            model="gemini/gemini-1.5-pro", 
            messages=messages, 
            response_format={"type": "json_object"}
        )
        
        print(f"Response (JSON): {json.loads(response.choices[0].message.content)}")
    except Exception as e:
        print(f"Error: {e}")

def example_json_schema():
    """JSON schema example"""
    print("\n--- JSON Schema Example ---")
    try:
        messages = [
            {
                "role": "user",
                "content": "List 3 popular cookie recipes."
            }
        ]
        
        response_schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "recipe_name": {
                        "type": "string",
                    },
                    "difficulty": {
                        "type": "string",
                        "enum": ["easy", "medium", "hard"]
                    }
                },
                "required": ["recipe_name", "difficulty"],
            },
        }
        
        response = proxy_completion(
            model="gemini/gemini-1.5-pro", 
            messages=messages, 
            response_format={
                "type": "json_object", 
                "response_schema": response_schema
            }
        )
        
        print(f"Response (with schema): {json.loads(response.choices[0].message.content)}")
    except Exception as e:
        print(f"Error: {e}")

def example_tool_calling():
    """Tool calling example"""
    print("\n--- Tool Calling Example ---")
    try:
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_current_weather",
                    "description": "Get the current weather in a given location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "The city and state, e.g. San Francisco, CA",
                            },
                            "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                        },
                        "required": ["location"],
                    },
                },
            }
        ]
        
        messages = [{"role": "user", "content": "What's the weather like in Boston today?"}]
        
        response = proxy_completion(
            model="gemini/gemini-1.5-flash",
            messages=messages,
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "get_current_weather"}}  # Force tool use
        )
        
        if response.choices[0].message.tool_calls:
            tool_call = response.choices[0].message.tool_calls[0]
            print(f"Tool Call Name: {tool_call.function.name}")
            print(f"Tool Call Args: {tool_call.function.arguments}")
        else:
            print(f"No tool calls in response. Content: {response.choices[0].message.content}")
    except Exception as e:
        print(f"Error: {e}")

def example_google_search():
    """Google Search tool example"""
    print("\n--- Google Search Tool Example ---")
    try:
        tools = [{"googleSearch": {}}]
        
        response = proxy_completion(
            model="gemini/gemini-2.0-flash",
            messages=[{"role": "user", "content": "What is the population of Tokyo?"}],
            tools=tools,
        )
        
        print(f"Response with Google Search: {response.choices[0].message.content}")
    except Exception as e:
        print(f"Error: {e}")

def example_reasoning_effort():
    """Reasoning effort example"""
    print("\n--- Reasoning Effort Example ---")
    try:
        response = proxy_completion(
            model="gemini/gemini-2.5-flash-preview-04-17",
            messages=[{"role": "user", "content": "Explain the concept of quantum entanglement"}],
            reasoning_effort="high",  # Translated to thinking with high budget_tokens
        )
        
        print(f"Response with high reasoning effort: {response.choices[0].message.content}")
    except Exception as e:
        print(f"Error: {e}")

def example_thinking_param():
    """Direct thinking parameter example"""
    print("\n--- Thinking Parameter Example ---")
    try:
        response = proxy_completion(
            model="gemini/gemini-2.5-flash-preview-04-17",
            messages=[{"role": "user", "content": "Solve this math problem: If a train travels at 60 mph, how long will it take to travel 240 miles?"}],
            thinking={"type": "enabled", "budget_tokens": 2048},
        )
        
        print(f"Response with thinking parameter: {response.choices[0].message.content}")
    except Exception as e:
        print(f"Error: {e}")

def example_safety_settings():
    """Safety settings example"""
    print("\n--- Safety Settings Example ---")
    try:
        response = proxy_completion(
            model="gemini/gemini-2.0-flash", 
            messages=[{"role": "user", "content": "Write a fictional story about a bank heist"}],
            safety_settings=[
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_ONLY_HIGH",
                },
            ]
        )
        
        print(f"Response with custom safety settings: {response.choices[0].message.content}")
    except Exception as e:
        print(f"Error: {e}")

def example_context_caching():
    """Simpler alternative to context caching example"""
    print("\n--- Context Handling Example ---")
    try:
        # Instead of using the caching API, we'll just demonstrate handling large context
        large_context = "Here is a complex technical document about quantum computing" * 50
        
        for i in range(2):
            print(f"\nLarge context request #{i+1}")
            resp = proxy_completion(
                model="gemini/gemini-1.5-pro",
                messages=[
                    # System Message with large context
                    {
                        "role": "system",
                        "content": large_context
                    },
                    # User message
                    {
                        "role": "user",
                        "content": "Summarize the key points in this document about quantum computing"
                    }
                ]
            )
            
            print(f"Response: {resp.choices[0].message.content[:100]}...")
            print(f"Usage: {resp.usage.total_tokens} tokens")
    except Exception as e:
        print(f"Error: {e}")

def example_image_input():
    """Image input example (vision) with updated model"""
    print("\n--- Image Input Example ---")
    try:
        # Use a sample image URL
        image_url = 'https://storage.googleapis.com/github-repo/img/gemini/intro/landmark3.jpg'
        
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Describe this image in detail"
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": image_url}
                    }
                ]
            }
        ]
        
        # Use a newer model that supports vision
        response = proxy_completion(
            model="gemini/gemini-1.5-flash",  # Updated from gemini-pro-vision
            messages=messages,
        )
        
        print(f"Image description: {response.choices[0].message.content}")
    except Exception as e:
        print(f"Error: {e}")

def example_additional_params():
    """Example with additional GenerationConfig params"""
    print("\n--- Additional GenerationConfig Params Example ---")
    try:
        response = proxy_completion(
            model="gemini/gemini-1.5-pro", 
            messages=[{"role": "user", "content": "Generate a creative story"}],
            topK=10,  # Additional parameter passed directly to GenerationConfig
            topP=0.8
        )
        
        print(f"Response with custom generation params: {response.choices[0].message.content[:100]}...")
    except Exception as e:
        print(f"Error: {e}")

def example_image_generation():
    """Image generation example"""
    print("\n--- Image Generation Example ---")
    try:
        response = proxy_completion(
            model="gemini/gemini-2.0-flash-exp-image-generation",
            messages=[{"role": "user", "content": "Generate an image of a mountain landscape at sunset"}],
            modalities=["image", "text"],
        )
        
        # The response contains a base64 encoded image
        image_data = response.choices[0].message.content
        print(f"Image generated successfully. Base64 data starts with: {image_data[:50]}...")
        
        # You could save this to a file
        if image_data and image_data.startswith("data:image"):
            # Extract the base64 part
            base64_data = image_data.split(",")[1]
            
            # Save to file (optional)
            with open("generated_image.png", "wb") as f:
                f.write(base64.b64decode(base64_data))
                print("Image saved to generated_image.png")
    except Exception as e:
        print(f"Error: {e}")

# Run examples
def run_examples():
    """Run all examples to demonstrate Gemini features with proxy rotation and TLS fingerprinting"""
    print("\n=== RUNNING GEMINI API EXAMPLES WITH PROXY ROTATION AND TLS FINGERPRINTING ===\n")
    
    examples = [
        example_basic_completion,
        example_json_mode,
        example_json_schema,
        example_tool_calling,
        example_google_search,
        example_reasoning_effort,
        example_thinking_param,
        example_safety_settings,
        example_context_caching,
        example_image_input,
        example_additional_params,
        example_image_generation
    ]
    
    for example in examples:
        try:
            example()
            time.sleep(1)  # Small delay between examples
        except Exception as e:
            print(f"Example {example.__name__} failed: {e}")

if __name__ == "__main__":
    try:
        run_examples()
    finally:
        # Clean up the background task when done
        try:
            proxy_update_task.cancel()
            loop.run_until_complete(proxy_update_task)
        except:
            pass
