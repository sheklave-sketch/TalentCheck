"""Async HTTP client for bot → API communication."""
import httpx
from .config import API_BASE_URL, BOT_SECRET

_HEADERS = {"X-Bot-Secret": BOT_SECRET}
_TIMEOUT = 15.0


async def api_get(path: str, params: dict | None = None) -> dict:
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=_TIMEOUT) as c:
        r = await c.get(f"/api/telegram{path}", headers=_HEADERS, params=params)
        r.raise_for_status()
        return r.json()


async def api_post(path: str, data: dict | None = None) -> dict:
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=_TIMEOUT) as c:
        r = await c.post(f"/api/telegram{path}", headers=_HEADERS, json=data or {})
        if r.status_code >= 400:
            try:
                detail = r.json().get("detail", r.text)
            except Exception:
                detail = r.text
            return {"error": True, "status": r.status_code, "detail": detail}
        return r.json()
