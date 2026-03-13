"""Tests for the mem0 API client (mocked HTTP)."""

import pytest
import respx
import httpx

from em0_mcp_wrapper import config
from em0_mcp_wrapper import client

# Set config for tests
config.MEM0_API_URL = "https://test-mem0.example.com"
config.MEM0_API_KEY = "test-key"
config.REQUEST_TIMEOUT = 5

# Speed up retry tests
client.MAX_RETRIES = 2
client.RETRY_DELAY = 0


@respx.mock
@pytest.mark.asyncio
async def test_add_memory():
    respx.post("https://test-mem0.example.com/v1/memories/").mock(
        return_value=httpx.Response(200, json={"results": [{"id": "abc", "event": "ADD"}]})
    )
    result = await client.add_memory("test content", "user1", {"domain": "auth"})
    assert "results" in result
    assert result["results"][0]["id"] == "abc"


@respx.mock
@pytest.mark.asyncio
async def test_search_memory():
    respx.post("https://test-mem0.example.com/v1/memories/search/").mock(
        return_value=httpx.Response(200, json={"results": [{"memory": "found it", "score": 0.9}]})
    )
    result = await client.search_memory("test query", "user1", limit=5)
    assert "results" in result
    assert result["results"][0]["score"] == 0.9


@respx.mock
@pytest.mark.asyncio
async def test_list_memories():
    respx.get("https://test-mem0.example.com/v1/memories/").mock(
        return_value=httpx.Response(200, json={"results": []})
    )
    result = await client.list_memories("user1")
    assert result == {"results": []}


@respx.mock
@pytest.mark.asyncio
async def test_delete_memory():
    respx.delete("https://test-mem0.example.com/v1/memories/abc123/").mock(
        return_value=httpx.Response(200, json={"status": "deleted"})
    )
    result = await client.delete_memory("abc123")
    assert result["status"] == "deleted"


@respx.mock
@pytest.mark.asyncio
async def test_timeout_retries_then_fails():
    respx.post("https://test-mem0.example.com/v1/memories/search/").mock(
        side_effect=httpx.TimeoutException("timeout")
    )
    result = await client.search_memory("test", "user1")
    assert "error" in result
    assert "timed out" in result["error"]
    assert "hint" in result


@respx.mock
@pytest.mark.asyncio
async def test_timeout_retry_succeeds():
    route = respx.post("https://test-mem0.example.com/v1/memories/search/")
    route.side_effect = [
        httpx.TimeoutException("cold start"),
        httpx.Response(200, json={"results": [{"memory": "found", "score": 0.8}]}),
    ]
    result = await client.search_memory("test", "user1")
    assert "results" in result
    assert result["results"][0]["score"] == 0.8


@respx.mock
@pytest.mark.asyncio
async def test_connect_error_retries():
    respx.post("https://test-mem0.example.com/v1/memories/search/").mock(
        side_effect=httpx.ConnectError("refused")
    )
    result = await client.search_memory("test", "user1")
    assert "error" in result
    assert "Cannot connect" in result["error"]


@respx.mock
@pytest.mark.asyncio
async def test_http_error():
    respx.post("https://test-mem0.example.com/v1/memories/search/").mock(
        return_value=httpx.Response(401, text="Unauthorized")
    )
    result = await client.search_memory("test", "user1")
    assert "error" in result
    assert "401" in result["error"]
