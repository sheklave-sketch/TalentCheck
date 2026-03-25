"""Async HTTP client for bot -> API communication.
Uses a persistent connection pool for performance."""
import logging
import httpx
from .config import API_BASE_URL, BOT_SECRET

logger = logging.getLogger(__name__)

_HEADERS = {"X-Bot-Secret": BOT_SECRET}
_TIMEOUT = 20.0

# Persistent client — reuses TCP connections instead of creating one per request
_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            base_url=API_BASE_URL,
            timeout=_TIMEOUT,
            headers=_HEADERS,
            limits=httpx.Limits(
                max_connections=50,
                max_keepalive_connections=20,
                keepalive_expiry=30,
            ),
        )
    return _client


async def api_get(path: str, params: dict | None = None) -> dict:
    """GET request to the telegram API endpoints. Returns parsed JSON."""
    c = _get_client()
    r = await c.get(f"/api/telegram{path}", params=params)
    r.raise_for_status()
    return r.json()


async def api_post(path: str, data: dict | None = None) -> dict:
    """POST request to the telegram API endpoints. Returns parsed JSON or error dict."""
    c = _get_client()
    r = await c.post(f"/api/telegram{path}", json=data or {})
    if r.status_code >= 400:
        try:
            detail = r.json().get("detail", r.text)
        except Exception:
            detail = r.text
        return {"error": True, "status": r.status_code, "detail": detail}
    return r.json()


async def api_get_raw(path: str, params: dict | None = None) -> dict:
    """GET request that returns raw response for binary data (certificates)."""
    c = _get_client()
    r = await c.get(f"/api/telegram{path}", params=params)
    if r.status_code >= 400:
        try:
            detail = r.json().get("detail", r.text)
        except Exception:
            detail = r.text
        return {"error": True, "status": r.status_code, "detail": detail}
    return r.json()
