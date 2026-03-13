"""HTTP client for the mem0 REST API. All error handling lives here."""

import logging

import httpx

from . import config

logger = logging.getLogger("em0-mcp")


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {config.MEM0_API_KEY}",
        "Content-Type": "application/json",
    }


async def request(method: str, path: str, **kwargs) -> dict:
    """Send a request to mem0 API. Returns error dict on failure."""
    url = f"{config.MEM0_API_URL}{path}"
    try:
        async with httpx.AsyncClient(timeout=config.REQUEST_TIMEOUT) as client:
            resp = await client.request(method, url, headers=_headers(), **kwargs)
            resp.raise_for_status()
            return resp.json()
    except httpx.TimeoutException:
        logger.error("Timeout: %s %s", method, url)
        return {"error": "Request timed out", "url": url}
    except httpx.HTTPStatusError as e:
        logger.error("HTTP %d: %s %s", e.response.status_code, method, url)
        return {"error": f"HTTP {e.response.status_code}", "detail": e.response.text}
    except httpx.ConnectError:
        logger.error("Connection error: %s", url)
        return {"error": "Cannot connect to mem0 server", "url": url}


async def add_memory(content: str, user_id: str, metadata: dict) -> dict:
    payload = {
        "messages": [{"role": "user", "content": content}],
        "user_id": user_id,
        "metadata": {k: v for k, v in metadata.items() if v},
    }
    return await request("POST", "/v1/memories/", json=payload)


async def search_memory(query: str, user_id: str, limit: int = 5) -> dict:
    payload = {"query": query, "user_id": user_id, "limit": limit}
    return await request("POST", "/v1/memories/search/", json=payload)


async def list_memories(user_id: str) -> dict:
    return await request("GET", "/v1/memories/", params={"user_id": user_id})


async def delete_memory(memory_id: str) -> dict:
    return await request("DELETE", f"/v1/memories/{memory_id}/")
