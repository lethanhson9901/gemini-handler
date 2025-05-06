"""
LiteLLM + SwiftShadow proxy‑rotating Gemini server
Now exposes the proxy IP for every request.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import google.generativeai as genai
import httpx
import uvicorn
import yaml
from fastapi import Body, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from litellm import Router
from litellm.exceptions import (
    BadRequestError,
    JSONSchemaValidationError,
    RateLimitError,
)
from pydantic import BaseModel
from swiftshadow.classes import ProxyInterface  # ★

# ------------------------------------------------------------------
logging.basicConfig(level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("gemini_proxy")
CONFIG_FILE = "config.yaml"

# ---------- SwiftShadow ----------
proxy_manager = ProxyInterface(protocol="http", autoRotate=True, autoUpdate=True)

# ---------- FastAPI -------------
app = FastAPI(
    title="LiteLLM Gemini Proxy (show proxy IP)",
    version="1.2.0",
    description="OpenAI‑compatible endpoints for Google Gemini – with rotating proxies"
)
app.add_middleware(CORSMiddleware,
                   allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"], allow_credentials=True)

# ---------- Schemas -------------
class ModelData(BaseModel):
    id: str
    object: str = "model"
    created: int = 1_686_935_002
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

router: Optional[Router] = None   # set on startup
# ---------- Helpers -------------
def load_api_keys(path: str) -> List[str]:
    with open(path, "r") as f:
        return yaml.safe_load(f).get("gemini", {}).get("api_keys", [])

def supported_models(key: str) -> List[str]:
    genai.configure(api_key=key)
    return [m.name for m in genai.list_models()
            if "gemini" in m.name and "generateContent" in m.supported_generation_methods]

def build_model_list(keys: List[str]) -> List[Dict[str, Any]]:
    ml = []
    for k in keys:
        for full in supported_models(k):
            short = full.split("/")[-1]
            ml.append({"model_name": short,
                       "litellm_params": {"model": f"gemini/{short}", "api_key": k}})
    return ml

# ---------- Proxy wrapper --------
async def call_with_proxy(fn, *args, **kwargs):
    """Run a litellm coroutine through a fresh proxy & return (result, proxy_url)."""
    proxy_url = proxy_manager.get().as_string()                   # ★ rotate
    async with httpx.AsyncClient(proxy=proxy_url) as client:      # ★ HTTPX ≥0.28
        import litellm
        litellm.aclient_session = client
        try:
            result = await fn(*args, **kwargs)
            return result, proxy_url
        finally:
            litellm.aclient_session = None

# ---------- Startup --------------
async def init_router():
    global router
    keys = load_api_keys(CONFIG_FILE)
    router = Router(model_list=build_model_list(keys),
                    routing_strategy="simple-shuffle")
    logger.info("Router ready with %d models.", len(router.model_list))

async def refresh_proxies():
    while True:
        try: await proxy_manager.async_update()
        except Exception as e: logger.warning("Proxy refresh error: %s", e)
        await asyncio.sleep(600)

@app.on_event("startup")
async def startup():
    await init_router()
    await proxy_manager.async_update()
    asyncio.create_task(refresh_proxies())

# ---------- End‑points -----------
@app.get("/v1/models", response_model=ModelsResponse)
async def list_models():
    seen, data = set(), []
    for m in router.model_list:
        if m["model_name"] not in seen:
            seen.add(m["model_name"])
            data.append(ModelData(id=m["model_name"]))
    return {"object": "list", "data": data}

@app.post("/v1/chat/completions")
async def chat(req: CompletionRequest, resp: Response):
    params = {
        "model": req.model,
        "messages": [m.dict() for m in req.messages],
        "temperature": req.temperature, "top_p": req.top_p, "stream": req.stream
    }
    for fld in ("max_tokens", "reasoning_effort", "thinking",
                "response_format", "tools", "safety_settings", "topK"):
        if getattr(req, fld) is not None:
            params[fld] = getattr(req, fld)

    try:
        result, proxy_url = await call_with_proxy(router.acompletion, **params)
        resp.headers["X-Proxy-IP"] = proxy_url                     # ★ header out
        # ---- flatten objects ↓
        choices = [{"index": c.index,
                    "finish_reason": c.finish_reason,
                    "message": {"role": c.message.role,
                                "content": c.message.content}}
                   for c in result.choices]
        usage = (result.usage if isinstance(result.usage, dict) else
                 {"prompt_tokens": result.usage.prompt_tokens,
                  "completion_tokens": result.usage.completion_tokens,
                  "total_tokens": result.usage.total_tokens})
        return {"id": result.id, "object": "chat.completion",
                "created": result.created, "model": result.model,
                "choices": choices, "usage": usage,
                "proxy": proxy_url}                                # ★ body out
    except (BadRequestError, JSONSchemaValidationError) as e:
        raise HTTPException(400, str(e))
    except RateLimitError as e:
        raise HTTPException(429, str(e))
    except Exception as e:
        logger.error("Completion error: %s", e)
        raise HTTPException(500, str(e))

@app.post("/setup")
async def setup(keys: List[str] = Body(...)):
    yaml.dump({"gemini": {"api_keys": keys}}, open(CONFIG_FILE, "w"))
    await init_router()
    return {"msg": "config updated"}

@app.get("/")
async def root(): return JSONResponse({"msg": "OK – see /docs"})

if __name__ == "__main__":
    uvicorn.run("proxy_server:app", host="0.0.0.0", port=8000, reload=True)
