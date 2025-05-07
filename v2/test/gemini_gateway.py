import asyncio
import itertools
import logging
import os
import random
from typing import Any, Dict, List, Optional, Set, Tuple

import httpx
import yaml
from fastapi import Depends, FastAPI, HTTPException, Request, Security
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security.api_key import APIKeyHeader, APIKeyQuery
from swiftshadow.classes import Proxy, ProxyInterface

# --- Configuration Loading ---
CONFIG_FILE = "config.yaml"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(f"{CONFIG_FILE} not found.")
    with open(CONFIG_FILE, "r") as f:
        config_data = yaml.safe_load(f)
    
    config_data.setdefault("server_settings", {})
    config_data.setdefault("gemini", {})
    config_data.setdefault("proxy_settings", {})
    config_data.setdefault("retry_settings", {})
    config_data.setdefault("health_check_settings", {})

    if not config_data["gemini"].get("api_keys"):
        raise ValueError("No Gemini API keys in config.yaml")
    if not config_data["health_check_settings"].get("health_check_api_key"):
        raise ValueError("Missing 'health_check_api_key' in health_check_settings")


    config_data["retry_settings"].setdefault("max_request_retries", 2) 
    config_data["retry_settings"].setdefault("fallback_to_direct_on_failure", True)
    config_data["retry_settings"].setdefault("retry_delay_seconds", 1)
    
    config_data["health_check_settings"].setdefault("enabled", True)
    config_data["health_check_settings"].setdefault("health_check_model_endpoint", "v1beta/models/gemini-1.5-flash-latest")
    config_data["health_check_settings"].setdefault("timeout_seconds", 15) # Increased slightly
    config_data["health_check_settings"].setdefault("max_concurrent_checks", 10)
    config_data["health_check_settings"].setdefault("min_whitelist_size", 5) 
    config_data["health_check_settings"].setdefault("proxy_recheck_interval_seconds", 300)

    return config_data

config = load_config()

SERVER_KEY = config["server_settings"]["server_key"]
GEMINI_API_KEYS = config["gemini"]["api_keys"]
GEMINI_BASE_URL = config["gemini"]["base_url"].rstrip('/')

PROXY_UPDATE_INTERVAL = config["proxy_settings"]["auto_update_interval_seconds"]
PROXY_MAX_COUNT_SWIFTSHADOW = config["proxy_settings"]["max_proxies"]

MAX_REQUEST_RETRIES = config["retry_settings"]["max_request_retries"]
FALLBACK_TO_DIRECT = config["retry_settings"]["fallback_to_direct_on_failure"]
RETRY_DELAY_SECONDS = config["retry_settings"]["retry_delay_seconds"]

HC_ENABLED = config["health_check_settings"]["enabled"]
HC_MODEL_ENDPOINT = config["health_check_settings"]["health_check_model_endpoint"]
HC_API_KEY = config["health_check_settings"]["health_check_api_key"]
HC_TIMEOUT = config["health_check_settings"]["timeout_seconds"]
HC_MAX_CONCURRENT = config["health_check_settings"]["max_concurrent_checks"] # Corrected variable name
HC_MIN_WHITELIST_SIZE = config["health_check_settings"]["min_whitelist_size"] # Corrected variable name
HC_PROXY_RECHECK_INTERVAL = config["health_check_settings"]["proxy_recheck_interval_seconds"]


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Gemini API Gateway (Advanced Proxy Health Check)",
    description="Gateway with specific API call for proxy health checks, whitelisting, and retry.",
    version="1.3.1" 
)

WHITELISTED_PROXIES: List[Proxy] = [] 
WHITELIST_LOCK = asyncio.Lock()       
RECENTLY_FAILED_PROXIES: Set[str] = set() 

API_KEY_NAME = "key" 
api_key_query = APIKeyQuery(name=API_KEY_NAME, auto_error=False)
api_key_header = APIKeyHeader(name="X-Server-Key", auto_error=False) 
async def get_api_key(key_query: str = Security(api_key_query), key_header: str = Security(api_key_header)):
    if key_query == SERVER_KEY: return key_query
    if key_header == SERVER_KEY: return key_header
    raise HTTPException(status_code=401, detail="Invalid or missing API Key")
gemini_key_rotator = itertools.cycle(GEMINI_API_KEYS)
def get_next_gemini_key(): return next(gemini_key_rotator)

swift_proxy_interface = ProxyInterface(
    autoUpdate=False, 
    autoRotate=False, 
    maxProxies=PROXY_MAX_COUNT_SWIFTSHADOW 
)

async def check_proxy_health(proxy: Proxy, semaphore: asyncio.Semaphore) -> Optional[Proxy]:
    async with semaphore: 
        proxy_str = proxy.as_string()
        proxy_dict = {"http://": proxy_str, "https://": proxy_str}
        proxy_id = f"{proxy.ip}:{proxy.port}"

        if proxy_id in RECENTLY_FAILED_PROXIES:
            logger.debug(f"Health Check: Skipping recently failed proxy {proxy_id}")
            return None

        health_check_url = f"{GEMINI_BASE_URL}/{HC_MODEL_ENDPOINT.lstrip('/')}?key={HC_API_KEY}"
        headers = {'Content-Type': 'application/json'}

        logger.debug(f"Health Check: Testing proxy {proxy_id} with GET {health_check_url}")
        try:
            async with httpx.AsyncClient(proxies=proxy_dict, timeout=HC_TIMEOUT, follow_redirects=False) as client:
                response = await client.get(health_check_url, headers=headers) 
                
                if response.status_code == 200:
                    logger.info(f"Health Check: Proxy {proxy_id} is HEALTHY (Status: {response.status_code} from {health_check_url})")
                    return proxy
                else:
                    logger.warning(f"Health Check: Proxy {proxy_id} is UNHEALTHY (Status: {response.status_code} from {health_check_url}, Response: {response.text[:100]})")
                    RECENTLY_FAILED_PROXIES.add(proxy_id)
                    return None
        except (httpx.TimeoutException, httpx.ProxyError, httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout, httpx.RemoteProtocolError) as e:
            logger.warning(f"Health Check: Proxy {proxy_id} FAILED ({type(e).__name__} during GET {health_check_url})")
            RECENTLY_FAILED_PROXIES.add(proxy_id)
            return None
        except Exception as e:
            logger.error(f"Health Check: Proxy {proxy_id} UNEXPECTED error ({type(e).__name__}: {e}) during GET {health_check_url}", exc_info=False)
            RECENTLY_FAILED_PROXIES.add(proxy_id)
            return None

async def proxy_harvester_task():
    health_check_semaphore = asyncio.Semaphore(HC_MAX_CONCURRENT)
    last_whitelist_recheck_time = asyncio.get_event_loop().time() # Initialize correctly

    while True:
        try:
            logger.info("Harvester: Updating proxy list from swiftshadow...")
            await swift_proxy_interface.async_update()
            raw_proxies_from_swift = list(swift_proxy_interface.proxies) 
            logger.info(f"Harvester: Swiftshadow provided {len(raw_proxies_from_swift)} proxies.")

            current_whitelist_ids = set()
            async with WHITELIST_LOCK: # Protect read of WHITELISTED_PROXIES
                current_whitelist_ids = {f"{p.ip}:{p.port}" for p in WHITELISTED_PROXIES}
            
            new_proxies_to_check = [
                p for p in raw_proxies_from_swift 
                if f"{p.ip}:{p.port}" not in current_whitelist_ids and f"{p.ip}:{p.port}" not in RECENTLY_FAILED_PROXIES
            ]

            if new_proxies_to_check:
                logger.info(f"Harvester: Found {len(new_proxies_to_check)} new unique proxies to health check.")
                tasks = [check_proxy_health(p, health_check_semaphore) for p in new_proxies_to_check]
                results = await asyncio.gather(*tasks, return_exceptions=True) # Handle individual task errors
                
                newly_whitelisted_proxies = []
                for i, res in enumerate(results):
                    if isinstance(res, Proxy):
                        newly_whitelisted_proxies.append(res)
                    elif isinstance(res, Exception):
                        logger.error(f"Harvester: Error in health check task for proxy {new_proxies_to_check[i].ip}:{new_proxies_to_check[i].port} - {res}")
                        RECENTLY_FAILED_PROXIES.add(f"{new_proxies_to_check[i].ip}:{new_proxies_to_check[i].port}")


                if newly_whitelisted_proxies:
                    async with WHITELIST_LOCK:
                        for p_new in newly_whitelisted_proxies:
                            if not any(wp.ip == p_new.ip and wp.port == p_new.port for wp in WHITELISTED_PROXIES):
                                WHITELISTED_PROXIES.append(p_new)
                        logger.info(f"Harvester: Added {len(newly_whitelisted_proxies)} proxies to whitelist. Whitelist size: {len(WHITELISTED_PROXIES)}")
            
            current_time = asyncio.get_event_loop().time()
            if HC_PROXY_RECHECK_INTERVAL > 0 and (current_time - last_whitelist_recheck_time > HC_PROXY_RECHECK_INTERVAL):
                logger.info("Harvester: Re-checking existing whitelisted proxies...")
                proxies_to_recheck = []
                async with WHITELIST_LOCK: # Protect read
                    proxies_to_recheck = list(WHITELISTED_PROXIES) 
                
                if proxies_to_recheck:
                    recheck_tasks = [check_proxy_health(p, health_check_semaphore) for p in proxies_to_recheck]
                    recheck_results = await asyncio.gather(*recheck_tasks, return_exceptions=True)
                    
                    updated_whitelist = []
                    for res in recheck_results:
                        if isinstance(res, Proxy):
                            updated_whitelist.append(res)
                        # Failed re-checks are implicitly dropped and already added to RECENTLY_FAILED_PROXIES by check_proxy_health

                    async with WHITELIST_LOCK:
                        WHITELISTED_PROXIES[:] = updated_whitelist 
                    logger.info(f"Harvester: Whitelist re-check complete. Whitelist size: {len(WHITELISTED_PROXIES)}")
                last_whitelist_recheck_time = current_time

            if len(RECENTLY_FAILED_PROXIES) > PROXY_MAX_COUNT_SWIFTSHADOW * 2 : 
                logger.info(f"Harvester: Clearing {len(RECENTLY_FAILED_PROXIES)} recently failed proxies set.")
                RECENTLY_FAILED_PROXIES.clear()

        except Exception as e:
            logger.error(f"Harvester: Error in task: {e}", exc_info=True)
        
        await asyncio.sleep(PROXY_UPDATE_INTERVAL)


@app.on_event("startup")
async def startup_event():
    logger.info("Application startup...")
    if HC_ENABLED:
        logger.info("Proxy health checking is ENABLED.")
        asyncio.create_task(proxy_harvester_task())
        logger.info("Proxy harvester and validator task started.")
    else:
        logger.info("Proxy health checking is DISABLED.")


async def get_whitelisted_proxy() -> Tuple[Optional[Proxy], str, Optional[Dict[str,str]]]:
    proxy_log_info = "None (no whitelisted proxies)"
    proxy_dict_for_httpx: Optional[Dict[str, str]] = None
    selected_proxy: Optional[Proxy] = None

    async with WHITELIST_LOCK:
        if WHITELISTED_PROXIES:
            selected_proxy = random.choice(WHITELISTED_PROXIES) 
            proxy_str = selected_proxy.as_string()
            proxy_dict_for_httpx = {"http://": proxy_str, "https://": proxy_str}
            proxy_log_info = f"{selected_proxy.ip}:{selected_proxy.port} ({selected_proxy.protocol})"
        else: 
            if not HC_ENABLED and swift_proxy_interface.proxies: 
                 temp_swift_proxy = swift_proxy_interface.get() # Use swift's rotation
                 if temp_swift_proxy: # swift_proxy_interface.get() can return None
                    selected_proxy = temp_swift_proxy
                    proxy_str = selected_proxy.as_string()
                    proxy_dict_for_httpx = {"http://": proxy_str, "https://": proxy_str}
                    proxy_log_info = f"{selected_proxy.ip}:{selected_proxy.port} (Swiftshadow direct)"

    if selected_proxy:
        logger.debug(f"Providing proxy: {proxy_log_info}")
    return selected_proxy, proxy_log_info, proxy_dict_for_httpx

async def mark_proxy_as_failed(proxy: Optional[Proxy]):
    if not proxy: return
    proxy_id = f"{proxy.ip}:{proxy.port}"
    logger.warning(f"Marking proxy {proxy_id} as FAILED for current request.")
    RECENTLY_FAILED_PROXIES.add(proxy_id) 
    async with WHITELIST_LOCK:
        WHITELISTED_PROXIES[:] = [p for p in WHITELISTED_PROXIES if not (p.ip == proxy.ip and p.port == proxy.port)]
    logger.info(f"Removed {proxy_id} from whitelist. Whitelist size: {len(WHITELISTED_PROXIES)}")


@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def forward_to_gemini(
    request: Request, full_path: str, server_api_key: str = Depends(get_api_key) 
):
    gemini_api_key = get_next_gemini_key()
    query_params = dict(request.query_params)
    query_params["key"] = gemini_api_key 
    if API_KEY_NAME in query_params and query_params[API_KEY_NAME] == SERVER_KEY:
        del query_params[API_KEY_NAME]
    target_url = f"{GEMINI_BASE_URL}/{full_path.lstrip('/')}"
    headers = { k: v for k, v in request.headers.items() if k.lower() not in ['host', 'x-server-key', 'connection']}
    headers["accept-encoding"] = "identity" 
    request_body = await request.body()
    
    last_exception = None
    total_attempts_allowed = MAX_REQUEST_RETRIES + (1 if FALLBACK_TO_DIRECT else 0)

    for attempt_num in range(1, total_attempts_allowed + 1):
        current_proxy_obj: Optional[Proxy] = None
        proxy_log_info: str = "N/A"
        proxy_dict_for_httpx: Optional[Dict[str, str]] = None
        is_direct_attempt = False

        if attempt_num <= MAX_REQUEST_RETRIES : 
            current_proxy_obj, proxy_log_info, proxy_dict_for_httpx = await get_whitelisted_proxy()
            if not current_proxy_obj:
                logger.warning(f"Attempt {attempt_num} (Proxy): No suitable proxy available from provider.")
                if attempt_num == MAX_REQUEST_RETRIES and not FALLBACK_TO_DIRECT: 
                    last_exception = Exception("No proxies available and no fallback.")
                    break 
                if attempt_num < total_attempts_allowed: # Only sleep if more attempts are possible
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
                continue
        elif FALLBACK_TO_DIRECT and attempt_num == MAX_REQUEST_RETRIES + 1: 
             is_direct_attempt = True
             proxy_log_info = "None (direct fallback)"
             logger.info(f"Attempt {attempt_num}: All proxy attempts exhausted or skipped. Trying direct connection.")
        else: break 

        logger.info(f"Forwarding Attempt {attempt_num}/{total_attempts_allowed}: {request.method} to: {target_url}")
        logger.info(f"Using Gemini Key ending: ...{gemini_api_key[-6:]}")
        logger.info(f"Connection via: {proxy_log_info}")

        try:
            async with httpx.AsyncClient(proxies=proxy_dict_for_httpx, timeout=60.0, follow_redirects=True) as client:
                upstream_response: httpx.Response
                if request.method == "GET": upstream_response = await client.get(target_url, params=query_params, headers=headers)
                elif request.method == "POST": upstream_response = await client.post(target_url, params=query_params, content=request_body, headers=headers)
                elif request.method == "PUT": upstream_response = await client.put(target_url, params=query_params, content=request_body, headers=headers)
                elif request.method == "DELETE": upstream_response = await client.delete(target_url, params=query_params, headers=headers)
                else: raise HTTPException(status_code=405, detail="Method Not Allowed")

                logger.info(f"Attempt {attempt_num} successful: Gemini Status {upstream_response.status_code}")
                
                is_streaming = ("alt=sse" in str(request.url).lower() or "chunked" in upstream_response.headers.get("transfer-encoding", "").lower() or
                                upstream_response.headers.get("content-type", "").lower().startswith("text/event-stream"))
                resp_headers = {k: v for k, v in upstream_response.headers.items() if k.lower() not in ["transfer-encoding", "connection", "content-encoding"]}

                if is_streaming:
                    async def stream_gen():
                        try: 
                            async for chunk in upstream_response.aiter_bytes(): yield chunk
                        finally: await upstream_response.aclose()
                    return StreamingResponse(stream_gen(), status_code=upstream_response.status_code, media_type=upstream_response.headers.get("content-type"), headers=resp_headers)
                else:
                    content = await upstream_response.aread()
                    await upstream_response.aclose()
                    resp_headers["Content-Length"] = str(len(content))
                    if "application/json" in upstream_response.headers.get("content-type", "").lower():
                        try: return JSONResponse(yaml.safe_load(content), status_code=upstream_response.status_code, headers=resp_headers)
                        except Exception as e: logger.warning(f"JSON parse failed, returning raw: {e}")
                    return StreamingResponse(iter([content]), status_code=upstream_response.status_code, media_type=upstream_response.headers.get("content-type"), headers=resp_headers)

        except (httpx.TimeoutException, httpx.ProxyError, httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout, httpx.RemoteProtocolError) as e:
            logger.error(f"Attempt {attempt_num} FAILED for {proxy_log_info}. Error: {type(e).__name__} - {str(e)[:200]}")
            last_exception = e
            if current_proxy_obj and not is_direct_attempt: 
                await mark_proxy_as_failed(current_proxy_obj)
            if attempt_num < total_attempts_allowed:
                 logger.info(f"Will retry in {RETRY_DELAY_SECONDS}s...")
                 await asyncio.sleep(RETRY_DELAY_SECONDS)
            continue 
        except httpx.HTTPStatusError as e: 
            logger.error(f"Attempt {attempt_num} FAILED: Gemini HTTP error {e.response.status_code}. Not retrying. Detail: {e.response.text[:200]}")
            raise HTTPException(status_code=e.response.status_code, detail=f"Gemini API Error: {e.response.text[:500]}")
        except Exception as e: 
            logger.error(f"Attempt {attempt_num} FAILED with unexpected error for {proxy_log_info}: {type(e).__name__}", exc_info=True)
            last_exception = e
            if current_proxy_obj and not is_direct_attempt:
                await mark_proxy_as_failed(current_proxy_obj)
            if attempt_num < total_attempts_allowed:
                 logger.info(f"Will retry in {RETRY_DELAY_SECONDS}s...")
                 await asyncio.sleep(RETRY_DELAY_SECONDS)
            continue

    logger.error(f"All {total_attempts_allowed} attempts failed for request to {full_path}.")
    detail_msg = "All gateway attempts failed."
    if last_exception: detail_msg = f"All gateway attempts failed. Last error: {type(last_exception).__name__} - {str(last_exception)[:200]}"
    status_code = 502 
    if isinstance(last_exception, httpx.TimeoutException): status_code = 504 
    raise HTTPException(status_code=status_code, detail=detail_msg)

@app.get("/_gateway/health", tags=["Gateway Management"])
async def health_check_endpoint(): 
    async with WHITELIST_LOCK: whitelist_count = len(WHITELISTED_PROXIES)
    return {
        "status": "healthy", "gemini_keys_available": len(GEMINI_API_KEYS),
        "health_checks_enabled": HC_ENABLED, "whitelisted_proxies_count": whitelist_count,
        "recently_failed_proxies_tracked": len(RECENTLY_FAILED_PROXIES),
        "min_whitelist_target": HC_MIN_WHITELIST_SIZE
    }

if __name__ == "__main__":
    import uvicorn
    server_host = config["server_settings"]["host"]
    server_port = int(config["server_settings"]["port"]) 
    logger.info(f"Starting Gemini API Gateway on {server_host}:{server_port}")
    logger.info(f"Log level: {logging.getLevelName(logger.getEffectiveLevel())}")
    logger.info(f"Max request retries: {MAX_REQUEST_RETRIES}, Fallback to direct: {FALLBACK_TO_DIRECT}")
    logger.info(f"Proxy health checks: {'ENABLED' if HC_ENABLED else 'DISABLED'}")
    if HC_ENABLED:
        logger.info(f"Health check model: {HC_MODEL_ENDPOINT}, HC API Key: ...{HC_API_KEY[-6:] if HC_API_KEY else 'N/A'}, Concurrency: {HC_MAX_CONCURRENT}")
    
    uvicorn.run("gemini_gateway:app", host=server_host, port=server_port, reload=True)