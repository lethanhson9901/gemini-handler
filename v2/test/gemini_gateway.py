import asyncio
import itertools
import logging
import os
from typing import Any, Dict, Optional

import httpx
import yaml  # PyYAML dependency
from fastapi import Depends, FastAPI, HTTPException, Request, Security
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security.api_key import APIKeyHeader, APIKeyQuery
from swiftshadow.classes import (  # Make sure swiftshadow is installed
    Proxy,
    ProxyInterface,
)

# --- Configuration Loading ---
CONFIG_FILE = "config.yaml"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(
            f"{CONFIG_FILE} not found. Please create it based on the example."
        )
    with open(CONFIG_FILE, "r") as f:
        config_data = yaml.safe_load(f) # Renamed to avoid conflict
    
    required_keys = ["server_settings", "gemini", "proxy_settings"]
    for key in required_keys:
        if key not in config_data:
            raise ValueError(f"Missing '{key}' section in {CONFIG_FILE}")
            
    if not config_data["gemini"].get("api_keys"):
        raise ValueError("No Gemini API keys found in config.yaml under gemini.api_keys")
    return config_data

config = load_config() # config is now a global variable holding the loaded dict

SERVER_KEY = config["server_settings"]["server_key"]
GEMINI_API_KEYS = config["gemini"]["api_keys"]
GEMINI_BASE_URL = config["gemini"]["base_url"].rstrip('/')
PROXY_UPDATE_INTERVAL = config["proxy_settings"]["auto_update_interval_seconds"]
PROXY_MAX_COUNT = config["proxy_settings"]["max_proxies"]

# --- Logging Setup ---
# Set to logging.DEBUG to see more verbose proxy selection logs from get_next_proxy_object
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# --- FastAPI App Initialization ---
app = FastAPI(
    title="Gemini API Gateway",
    description="A gateway to Google Gemini API with API key and proxy rotation.",
    version="1.1.0" # Incremented version
)

# --- API Key Authentication for this Gateway ---
API_KEY_NAME = "key" 
api_key_query = APIKeyQuery(name=API_KEY_NAME, auto_error=False)
api_key_header = APIKeyHeader(name="X-Server-Key", auto_error=False) 

async def get_api_key(
    key_query: str = Security(api_key_query),
    key_header: str = Security(api_key_header),
):
    if key_query == SERVER_KEY:
        return key_query
    if key_header == SERVER_KEY:
        return key_header
    raise HTTPException(
        status_code=401, detail="Invalid or missing API Key for this gateway"
    )

# --- Gemini API Key Rotation ---
gemini_key_rotator = itertools.cycle(GEMINI_API_KEYS)

def get_next_gemini_key():
    key = next(gemini_key_rotator)
    # This debug log will only show if logger level is DEBUG
    logger.debug(f"Selected Gemini API Key ending with: ...{key[-6:]}")
    return key

# --- Proxy Management (swiftshadow) ---
swift_proxy_interface = ProxyInterface(
    autoUpdate=False, 
    autoRotate=True,  # Rotates proxy on each swift.get()
    maxProxies=PROXY_MAX_COUNT
)

async def update_proxies_periodically():
    """Background task to update proxies."""
    while True:
        try:
            logger.info("Attempting to update proxy list from swiftshadow...")
            await swift_proxy_interface.async_update()
            logger.info(f"Proxy list updated. Current count: {len(swift_proxy_interface.proxies)}")
        except Exception as e:
            logger.error(f"Error updating proxies: {e}", exc_info=True)
        await asyncio.sleep(PROXY_UPDATE_INTERVAL)

@app.on_event("startup")
async def startup_event():
    """Initial proxy fetch and start background task."""
    logger.info("Application startup: Initializing proxy interface...")
    try:
        logger.info("Performing initial proxy update...")
        await swift_proxy_interface.async_update()
        logger.info(f"Initial proxy list fetched. Count: {len(swift_proxy_interface.proxies)}")
    except Exception as e:
        logger.error(f"Error during initial proxy update: {e}", exc_info=True)
    
    asyncio.create_task(update_proxies_periodically())
    logger.info("Proxy update background task started.")

def get_next_proxy_object() -> Optional[Proxy]:
    """
    Gets the next Proxy object from swiftshadow.
    Returns the Proxy object itself or None if no proxies are available or an issue occurs.
    """
    if not swift_proxy_interface.proxies:
        logger.warning("No proxies available in swiftshadow interface.")
        return None
    
    proxy_obj: Optional[Proxy] = swift_proxy_interface.get() 
    
    if proxy_obj:
        # This debug log will only show if logger level is DEBUG
        logger.debug(f"Proxy object obtained: {proxy_obj.ip}:{proxy_obj.port} ({proxy_obj.protocol})")
        return proxy_obj
    else:
        # This might happen if swiftshadow.get() returns None unexpectedly
        logger.warning("swiftshadow.get() returned None despite a non-empty proxy list, or the proxy object was falsey.")
        return None

# --- Main API Endpoint ---
@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def forward_to_gemini(
    request: Request,
    full_path: str,
    server_api_key: str = Depends(get_api_key) 
):
    gemini_api_key = get_next_gemini_key()
    
    query_params = dict(request.query_params)
    query_params["key"] = gemini_api_key 
    
    if API_KEY_NAME in query_params and query_params[API_KEY_NAME] == SERVER_KEY:
        del query_params[API_KEY_NAME]

    target_url = f"{GEMINI_BASE_URL}/{full_path.lstrip('/')}"
    
    headers = {
        key: value for key, value in request.headers.items() 
        if key.lower() not in ['host', 'x-server-key', 'connection']
    }
    headers["accept-encoding"] = "identity" 

    request_body = await request.body()
    
    proxy_obj = get_next_proxy_object()
    proxy_dict_for_httpx: Optional[Dict[str, str]] = None
    proxy_log_info = "None (direct connection)"

    if proxy_obj:
        proxy_dict_for_httpx = {"http://": proxy_obj.as_string(), "https://": proxy_obj.as_string()}
        proxy_log_info = f"{proxy_obj.ip}:{proxy_obj.port} ({proxy_obj.protocol})"

    logger.info(f"Forwarding {request.method} to: {target_url}")
    logger.info(f"Using Gemini Key ending: ...{gemini_api_key[-6:]}")
    logger.info(f"Using Proxy: {proxy_log_info}")

    async with httpx.AsyncClient(proxies=proxy_dict_for_httpx, timeout=60.0, follow_redirects=True) as client:
        try:
            upstream_response: httpx.Response

            if request.method == "GET":
                upstream_response = await client.get(
                    target_url, params=query_params, headers=headers
                )
            elif request.method == "POST":
                 upstream_response = await client.post(
                    target_url, params=query_params, content=request_body, headers=headers
                )
            elif request.method == "PUT":
                 upstream_response = await client.put(
                    target_url, params=query_params, content=request_body, headers=headers
                )
            elif request.method == "DELETE":
                 upstream_response = await client.delete(
                    target_url, params=query_params, headers=headers 
                )
            else:
                logger.warning(f"Unsupported method by gateway: {request.method}")
                raise HTTPException(status_code=405, detail="Method Not Allowed by this gateway")

            logger.info(f"Received response from Gemini ({target_url}): Status {upstream_response.status_code}")

            is_streaming_response = (
                "alt=sse" in str(request.url).lower() or
                "chunked" in upstream_response.headers.get("transfer-encoding", "").lower() or
                upstream_response.headers.get("content-type", "").lower().startswith("text/event-stream")
            )

            response_headers = { 
                k: v for k, v in upstream_response.headers.items()
                if k.lower() not in ["transfer-encoding", "connection", "content-encoding"]
            }

            if is_streaming_response:
                logger.info(f"Streaming response from {target_url}")
                async def stream_generator():
                    try:
                        async for chunk in upstream_response.aiter_bytes():
                            yield chunk
                    finally:
                        await upstream_response.aclose()
                
                return StreamingResponse(
                    stream_generator(),
                    status_code=upstream_response.status_code,
                    media_type=upstream_response.headers.get("content-type"),
                    headers=response_headers
                )
            else:
                response_content = await upstream_response.aread()
                await upstream_response.aclose()
                
                logger.debug(f"Non-streaming response content length: {len(response_content)} bytes")
                response_headers["Content-Length"] = str(len(response_content))

                if "application/json" in upstream_response.headers.get("content-type", "").lower():
                    try:
                        # Using yaml.safe_load for potentially more resilient parsing
                        # If you prefer standard json, use: json_content = json.loads(response_content)
                        # and add `import json` at the top.
                        json_content = yaml.safe_load(response_content) 
                        return JSONResponse(
                            content=json_content,
                            status_code=upstream_response.status_code,
                            headers=response_headers
                        )
                    except yaml.YAMLError as parse_err: # Catch specific PyYAML error
                         logger.warning(f"Failed to parse YAML/JSON response from Gemini, returning raw. Error: {parse_err}")
                    except Exception as generic_parse_err: # Catch other potential errors during parsing
                         logger.warning(f"Generic error parsing response from Gemini, returning raw. Error: {generic_parse_err}")

                return StreamingResponse(
                    iter([response_content]), 
                    status_code=upstream_response.status_code,
                    media_type=upstream_response.headers.get("content-type"),
                    headers=response_headers
                )

        except httpx.TimeoutException as e:
            logger.error(f"Timeout connecting to {target_url} via proxy {proxy_log_info}. Error: {e}")
            raise HTTPException(status_code=504, detail=f"Gateway timeout connecting to Gemini API: {e}")
        except httpx.ProxyError as e:
            logger.error(f"Proxy error for {target_url} with proxy {proxy_log_info}. Error: {e}")
            raise HTTPException(status_code=502, detail=f"Bad gateway: Proxy error - {e}")
        except httpx.RequestError as e: 
            logger.error(f"Request error connecting to {target_url} via proxy {proxy_log_info}: {e}")
            raise HTTPException(status_code=502, detail=f"Bad gateway: Error connecting to Gemini API - {str(e)}")
        except Exception as e:
            logger.error(f"An unexpected error occurred while processing {full_path}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/_gateway/health", tags=["Gateway Management"])
async def health_check():
    """Health check for the gateway itself."""
    proxy_preview_str = "N/A (no proxies in pool)"
    if swift_proxy_interface and swift_proxy_interface.proxies:
        # Peek at the next proxy without consuming it for the health check
        # swiftshadow's .get() with autoRotate=True moves the proxy.
        # To truly peek, we'd look at self.proxies[0] if it's a list/deque.
        # For simplicity and given autoRotate, just getting one is okay for a preview.
        temp_proxy = swift_proxy_interface.get() # This will rotate
        if temp_proxy:
            proxy_preview_str = f"{temp_proxy.ip}:{temp_proxy.port} ({temp_proxy.protocol})"
            # Note: This proxy is now at the end of the rotation due to .get()

    return {
        "status": "healthy",
        "gemini_keys_available": len(GEMINI_API_KEYS),
        "proxies_in_pool": len(swift_proxy_interface.proxies) if swift_proxy_interface else 0,
        "next_proxy_preview_after_rotation": proxy_preview_str
    }

# --- Main Execution ---
if __name__ == "__main__":
    import uvicorn
    server_host = config["server_settings"]["host"]
    server_port = int(config["server_settings"]["port"]) 
    logger.info(f"Starting Gemini API Gateway on {server_host}:{server_port}")
    logger.info(f"Log level set to: {logging.getLevelName(logger.getEffectiveLevel())}")
    uvicorn.run("gemini_gateway:app", host=server_host, port=server_port, reload=True) # Added reload for dev