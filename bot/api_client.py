"""Async HTTP client for bot -> API communication."""
import logging
import httpx
from .config import API_BASE_URL, BOT_SECRET

logger = logging.getLogger(__name__)

_HEADERS = {"X-Bot-Secret": BOT_SECRET}
_TIMEOUT = 20.0


async def api_get(path: str, params: dict | None = None) -> dict:
    """GET request to the telegram API endpoints. Returns parsed JSON."""
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=_TIMEOUT) as c:
        r = await c.get(f"/api/telegram{path}", headers=_HEADERS, params=params)
        r.raise_for_status()
        return r.json()


async def api_post(path: str, data: dict | None = None) -> dict:
    """POST request to the telegram API endpoints. Returns parsed JSON or error dict."""
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=_TIMEOUT) as c:
        r = await c.post(f"/api/telegram{path}", headers=_HEADERS, json=data or {})
        if r.status_code >= 400:
            try:
                detail = r.json().get("detail", r.text)
            except Exception:
                detail = r.text
            return {"error": True, "status": r.status_code, "detail": detail}
        return r.json()


async def api_get_raw(path: str, params: dict | None = None) -> dict:
    """GET request that returns raw response for binary data (certificates)."""
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=_TIMEOUT) as c:
        r = await c.get(f"/api/telegram{path}", headers=_HEADERS, params=params)
        if r.status_code >= 400:
            try:
                detail = r.json().get("detail", r.text)
            except Exception:
                detail = r.text
            return {"error": True, "status": r.status_code, "detail": detail}
        return r.json()
