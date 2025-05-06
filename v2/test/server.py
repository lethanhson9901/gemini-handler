import asyncio
import logging
import random
from typing import Any, Dict, List, Optional

import httpx
import yaml
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import APIKeyHeader
from swiftshadow.classes import ProxyInterface

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("gemini-proxy")

# Load configuration
def load_config(config_path: str = "config.yaml") -> Dict:
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        raise RuntimeError(f"Configuration error: {e}")

config = load_config()

# API Authentication
API_KEY_NAME = "Authorization"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Get server key from config
SERVER_KEY = config.get("server_settings", {}).get("key", "")
if not SERVER_KEY:
    raise RuntimeError("Server API key not configured")

# Get proxy settings
USE_PROXIES = config.get("server_settings", {}).get("use_proxies", True)

# API Key Management
class KeyManager:
    def __init__(self, keys: List[str]):
        if not keys:
            raise ValueError("No API keys provided")
        self.keys = keys
        self.current_index = 0
        self.fail_count = {k: 0 for k in keys}
        logger.info(f"Initialized KeyManager with {len(keys)} keys")

    def get_next_key(self) -> str:
        key = self.keys[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.keys)
        return key
    
    def mark_key_failed(self, key: str):
        """Mark a key as failed to potentially skip it in the future"""
        if key in self.fail_count:
            self.fail_count[key] += 1
            logger.warning(f"Key marked as failed ({self.fail_count[key]} times): {key[:10]}...")
    
    def reset_failures(self):
        """Reset all failure counters"""
        self.fail_count = {k: 0 for k in self.keys}

# Initialize key manager
gemini_keys = config.get("gemini", {}).get("api_keys", [])
if not gemini_keys:
    raise RuntimeError("No Gemini API keys configured")

key_manager = KeyManager(gemini_keys)

# Initialize proxy manager if enabled
swift = None
if USE_PROXIES:
    swift = ProxyInterface(autoUpdate=False, autoRotate=True, maxProxies=50)
    logger.info("Proxy support enabled")
else:
    logger.info("Proxy support disabled")

# Create FastAPI app
app = FastAPI(title="Gemini API Proxy", description="Proxy server for Google Gemini API with key rotation and proxy support")

# Authentication dependency
async def verify_api_key(api_key: str = Depends(api_key_header)):
    if not api_key or api_key != f"Bearer {SERVER_KEY}":
        logger.warning("Invalid API key attempt")
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return api_key

# Background task to update proxies
async def background_task():
    """Update proxies every minute"""
    if not USE_PROXIES or not swift:
        return
        
    while True:
        logger.info("Updating proxies...")
        try:
            await swift.async_update()
            # Get the proxy count properly
            proxy_count = len(swift.proxies) if hasattr(swift, 'proxies') else 0
            logger.info(f"Proxy pool updated, available proxies: {proxy_count}")
        except Exception as e:
            logger.error(f"Failed to update proxies: {e}")
        await asyncio.sleep(60)

@app.on_event("startup")
async def startup_event():
    """Start the background task when the app starts"""
    if USE_PROXIES:
        asyncio.create_task(background_task())
        logger.info("Background proxy update task started")

# Helper function to get client with proxy
def get_client_with_proxy():
    if not USE_PROXIES or not swift:
        return httpx.AsyncClient(timeout=60.0)
    
    try:
        proxy = swift.get()
        if not proxy:
            logger.warning("No proxy available, using direct connection")
            return httpx.AsyncClient(timeout=60.0)
        
        proxy_url = proxy.as_string()
        logger.debug(f"Using proxy: {proxy_url}")
        return httpx.AsyncClient(proxies={"all://": proxy_url}, timeout=60.0)
    except Exception as e:
        logger.error(f"Error getting proxy: {e}")
        return httpx.AsyncClient(timeout=60.0)

# Log request and response
async def log_request_response(request_id: str, model_id: str, api_key: str, response):
    """Log request and response details"""
    status = response.status_code if hasattr(response, "status_code") else "N/A"
    logger.info(f"Request {request_id}: model={model_id}, key={api_key[:10]}..., status={status}")

# Gemini endpoints
@app.post("/v1beta/models/{model_id}:generateContent")
async def generate_content(
    model_id: str, 
    request: Request,
    background_tasks: BackgroundTasks,
    _: str = Depends(verify_api_key)
):
    # Get the next API key
    api_key = key_manager.get_next_key()
    request_id = str(random.randint(10000, 99999))
    logger.info(f"Request {request_id}: Using model: {model_id}")
    
    # Get the request body
    body = await request.json()
    
    # Prepare the Gemini API URL with the selected key
    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={api_key}"
    
    # Get a client with a proxy
    async with get_client_with_proxy() as client:
        try:
            # Forward the request to Google's API
            response = await client.post(
                gemini_url,
                json=body,
                headers={"Content-Type": "application/json"}
            )
            
            # Log the request/response
            background_tasks.add_task(log_request_response, request_id, model_id, api_key, response)
            
            # Check if there was an error with the API key
            if response.status_code == 400:
                # Try to parse the error
                error_data = response.json()
                error_message = error_data.get('error', {}).get('message', '')
                if 'API key not valid' in error_message:
                    key_manager.mark_key_failed(api_key)
            
            # Return the response
            return JSONResponse(
                content=response.json(),
                status_code=response.status_code
            )
        except Exception as e:
            logger.error(f"Request {request_id}: Error forwarding request: {e}")
            raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

@app.post("/v1beta/models/{model_id}:streamGenerateContent")
async def stream_generate_content(
    model_id: str, 
    request: Request,
    _: str = Depends(verify_api_key)
):
    # Get the next API key
    api_key = key_manager.get_next_key()
    request_id = str(random.randint(10000, 99999))
    logger.info(f"Request {request_id}: Using model for streaming: {model_id}")
    
    # Get the request body
    body = await request.json()
    
    # Prepare the Gemini API URL with the selected key
    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:streamGenerateContent?alt=sse&key={api_key}"
    
    # Define the streaming response function
    async def stream_response():
        async with get_client_with_proxy() as client:
            try:
                # Forward the request to Google's API
                async with client.stream(
                    "POST",
                    gemini_url,
                    json=body,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    # Check for API key errors
                    if response.status_code == 400:
                        try:
                            error_text = await response.aread()
                            error_data = response.json()
                            error_message = error_data.get('error', {}).get('message', '')
                            if 'API key not valid' in error_message:
                                key_manager.mark_key_failed(api_key)
                        except:
                            pass
                    
                    # Stream the response
                    async for chunk in response.aiter_bytes():
                        yield chunk
            except Exception as e:
                logger.error(f"Request {request_id}: Error in streaming: {e}")
                yield f"data: {{'error': '{str(e)}'}}\n\n".encode()
    
    # Return a streaming response
    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream"
    )

@app.post("/v1beta/models/{model_id}:embedContent")
async def embed_content(
    model_id: str, 
    request: Request,
    background_tasks: BackgroundTasks,
    _: str = Depends(verify_api_key)
):
    # Get the next API key
    api_key = key_manager.get_next_key()
    request_id = str(random.randint(10000, 99999))
    logger.info(f"Request {request_id}: Using model for embedding: {model_id}")
    
    # Get the request body
    body = await request.json()
    
    # Prepare the Gemini API URL with the selected key
    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:embedContent?key={api_key}"
    
    # Get a client with a proxy
    async with get_client_with_proxy() as client:
        try:
            # Forward the request to Google's API
            response = await client.post(
                gemini_url,
                json=body,
                headers={"Content-Type": "application/json"}
            )
            
            # Log the request/response
            background_tasks.add_task(log_request_response, request_id, model_id, api_key, response)
            
            # Check if there was an error with the API key
            if response.status_code == 400:
                error_data = response.json()
                error_message = error_data.get('error', {}).get('message', '')
                if 'API key not valid' in error_message:
                    key_manager.mark_key_failed(api_key)
            
            # Return the response
            return JSONResponse(
                content=response.json(),
                status_code=response.status_code
            )
        except Exception as e:
            logger.error(f"Request {request_id}: Error forwarding embed request: {e}")
            raise HTTPException(status_code=500, detail=f"Error processing embed request: {str(e)}")

@app.post("/v1beta/models/{model_id}:batchEmbedContents")
async def batch_embed_contents(
    model_id: str, 
    request: Request,
    background_tasks: BackgroundTasks,
    _: str = Depends(verify_api_key)
):
    # Get the next API key
    api_key = key_manager.get_next_key()
    request_id = str(random.randint(10000, 99999))
    logger.info(f"Request {request_id}: Using model for batch embedding: {model_id}")
    
    # Get the request body
    body = await request.json()
    
    # Prepare the Gemini API URL with the selected key
    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:batchEmbedContents?key={api_key}"
    
    # Get a client with a proxy
    async with get_client_with_proxy() as client:
        try:
            # Forward the request to Google's API
            response = await client.post(
                gemini_url,
                json=body,
                headers={"Content-Type": "application/json"}
            )
            
            # Log the request/response
            background_tasks.add_task(log_request_response, request_id, model_id, api_key, response)
            
            # Check if there was an error with the API key
            if response.status_code == 400:
                error_data = response.json()
                error_message = error_data.get('error', {}).get('message', '')
                if 'API key not valid' in error_message:
                    key_manager.mark_key_failed(api_key)
            
            # Return the response
            return JSONResponse(
                content=response.json(),
                status_code=response.status_code
            )
        except Exception as e:
            logger.error(f"Request {request_id}: Error forwarding batch embed request: {e}")
            raise HTTPException(status_code=500, detail=f"Error processing batch embed request: {str(e)}")

@app.post("/v1beta/models/{model_id}:countTokens")
async def count_tokens(
    model_id: str, 
    request: Request,
    background_tasks: BackgroundTasks,
    _: str = Depends(verify_api_key)
):
    # Get the next API key
    api_key = key_manager.get_next_key()
    request_id = str(random.randint(10000, 99999))
    logger.info(f"Request {request_id}: Using model for token counting: {model_id}")
    
    # Get the request body
    body = await request.json()
    
    # Prepare the Gemini API URL with the selected key
    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:countTokens?key={api_key}"
    
    # Get a client with a proxy
    async with get_client_with_proxy() as client:
        try:
            # Forward the request to Google's API
            response = await client.post(
                gemini_url,
                json=body,
                headers={"Content-Type": "application/json"}
            )
            
            # Log the request/response
            background_tasks.add_task(log_request_response, request_id, model_id, api_key, response)
            
            # Check if there was an error with the API key
            if response.status_code == 400:
                error_data = response.json()
                error_message = error_data.get('error', {}).get('message', '')
                if 'API key not valid' in error_message:
                    key_manager.mark_key_failed(api_key)
            
            # Return the response
            return JSONResponse(
                content=response.json(),
                status_code=response.status_code
            )
        except Exception as e:
            logger.error(f"Request {request_id}: Error forwarding token count request: {e}")
            raise HTTPException(status_code=500, detail=f"Error processing token count request: {str(e)}")

@app.get("/v1beta/models")
async def list_models(
    request: Request,
    background_tasks: BackgroundTasks,
    _: str = Depends(verify_api_key)
):
    # Get the next API key
    api_key = key_manager.get_next_key()
    request_id = str(random.randint(10000, 99999))
    logger.info(f"Request {request_id}: Listing available models")
    
    # Get query parameters
    pageSize = request.query_params.get("pageSize")
    pageToken = request.query_params.get("pageToken")
    
    # Build URL with query parameters
    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    if pageSize:
        gemini_url += f"&pageSize={pageSize}"
    if pageToken:
        gemini_url += f"&pageToken={pageToken}"
    
    # Get a client with a proxy
    async with get_client_with_proxy() as client:
        try:
            # Forward the request to Google's API
            response = await client.get(gemini_url)
            
            # Log the request/response
            background_tasks.add_task(log_request_response, request_id, "list_models", api_key, response)
            
            # Check if there was an error with the API key
            if response.status_code == 400:
                error_data = response.json()
                error_message = error_data.get('error', {}).get('message', '')
                if 'API key not valid' in error_message:
                    key_manager.mark_key_failed(api_key)
            
            # Return the response
            return JSONResponse(
                content=response.json(),
                status_code=response.status_code
            )
        except Exception as e:
            logger.error(f"Request {request_id}: Error listing models: {e}")
            raise HTTPException(status_code=500, detail=f"Error listing models: {str(e)}")

@app.get("/v1beta/models/{model_id}")
async def get_model(
    model_id: str,
    background_tasks: BackgroundTasks,
    _: str = Depends(verify_api_key)
):
    # Get the next API key
    api_key = key_manager.get_next_key()
    request_id = str(random.randint(10000, 99999))
    logger.info(f"Request {request_id}: Getting model details: {model_id}")
    
    # Prepare the Gemini API URL with the selected key
    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}?key={api_key}"
    
    # Get a client with a proxy
    async with get_client_with_proxy() as client:
        try:
            # Forward the request to Google's API
            response = await client.get(gemini_url)
            
            # Log the request/response
            background_tasks.add_task(log_request_response, request_id, model_id, api_key, response)
            
            # Check if there was an error with the API key
            if response.status_code == 400:
                error_data = response.json()
                error_message = error_data.get('error', {}).get('message', '')
                if 'API key not valid' in error_message:
                    key_manager.mark_key_failed(api_key)
            
            # Return the response
            return JSONResponse(
                content=response.json(),
                status_code=response.status_code
            )
        except Exception as e:
            logger.error(f"Request {request_id}: Error getting model details: {e}")
            raise HTTPException(status_code=500, detail=f"Error getting model details: {str(e)}")

# Add a status endpoint to check if the server is running
@app.get("/status")
async def status():
    """Check if the server is running"""
    proxy_count = len(swift.proxies) if USE_PROXIES and swift else "disabled"
    return {
        "status": "ok",
        "proxy_count": proxy_count,
        "api_key_count": len(gemini_keys),
        "key_failures": key_manager.fail_count if key_manager else {}
    }

# Helper function to get client with proxy - corrected version
def get_client_with_proxy():
    if not USE_PROXIES or not swift:
        return httpx.AsyncClient(timeout=60.0)
    
    try:
        proxy = swift.get()
        if not proxy:
            logger.warning("No proxy available, using direct connection")
            return httpx.AsyncClient(timeout=60.0)
        
        proxy_url = proxy.as_string()
        logger.debug(f"Using proxy: {proxy_url}")
        
        # Correct way to set proxies in httpx AsyncClient
        proxies = {"http://": proxy_url, "https://": proxy_url}
        return httpx.AsyncClient(proxies=proxies, timeout=60.0)
    except Exception as e:
        logger.error(f"Error getting proxy: {e}")
        return httpx.AsyncClient(timeout=60.0)

# Reset failed key counters
@app.post("/admin/reset-failures")
async def reset_failures(
    _: str = Depends(verify_api_key)
):
    """Reset failure counters for API keys"""
    key_manager.reset_failures()
    return {"status": "reset_successful"}

# Run the application if executed directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)