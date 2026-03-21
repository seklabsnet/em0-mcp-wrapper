"""Tests for the mem0 API client (mocked HTTP)."""

import json

import httpx
import pytest
import respx

from em0_mcp_wrapper import client, config

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
async def test_add_memory_immutable():
    route = respx.post("https://test-mem0.example.com/v1/memories/")
    route.mock(
        return_value=httpx.Response(200, json={"results": [{"id": "imm1", "event": "ADD"}]})
    )
    result = await client.add_memory(
        "critical decision", "user1", {"domain": "arch"}, immutable=True
    )
    assert "results" in result
    body = json.loads(route.calls[0].request.content)
    assert body["immutable"] is True


@respx.mock
@pytest.mark.asyncio
async def test_search_memory():
    respx.post("https://test-mem0.example.com/v1/memories/search/").mock(
        return_value=httpx.Response(
            200, json={"results": [{"memory": "found it", "score": 0.9}]}
        )
    )
    result = await client.search_memory("test query", "user1", limit=5)
    assert "results" in result
    assert result["results"][0]["score"] == 0.9


@respx.mock
@pytest.mark.asyncio
async def test_search_memory_with_filters():
    route = respx.post("https://test-mem0.example.com/v1/memories/search/")
    route.mock(return_value=httpx.Response(200, json={"results": []}))
    filters = {"metadata.domain": "auth"}
    await client.search_memory("test", "user1", filters=filters)
    body = json.loads(route.calls[0].request.content)
    assert body["filters"] == filters


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
async def test_get_memory():
    respx.get("https://test-mem0.example.com/v1/memories/abc123/").mock(
        return_value=httpx.Response(200, json={"id": "abc123", "memory": "test data"})
    )
    result = await client.get_memory("abc123")
    assert result["id"] == "abc123"


@respx.mock
@pytest.mark.asyncio
async def test_update_memory():
    respx.put("https://test-mem0.example.com/v1/memories/abc123/").mock(
        return_value=httpx.Response(200, json={"id": "abc123", "event": "UPDATE"})
    )
    result = await client.update_memory("abc123", "updated content")
    assert result["event"] == "UPDATE"


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
async def test_memory_history():
    respx.get("https://test-mem0.example.com/v1/memories/abc123/history/").mock(
        return_value=httpx.Response(200, json=[
            {
                "old_memory": "v1",
                "new_memory": "v2",
                "event": "UPDATE",
                "created_at": "2026-03-01",
            }
        ])
    )
    result = await client.memory_history("abc123")
    assert isinstance(result, list)
    assert result[0]["event"] == "UPDATE"


@respx.mock
@pytest.mark.asyncio
async def test_get_entities():
    respx.get("https://test-mem0.example.com/v1/entities/").mock(
        return_value=httpx.Response(200, json={
            "results": [
                {"name": "PostgreSQL", "type": "database"},
                {"name": "Erkut", "type": "person"},
            ]
        })
    )
    result = await client.get_entities("user1")
    assert len(result["results"]) == 2


@respx.mock
@pytest.mark.asyncio
async def test_get_relations():
    respx.get("https://test-mem0.example.com/v1/relations/").mock(
        return_value=httpx.Response(200, json={
            "results": [
                {
                    "source": "Erkut",
                    "relationship": "decided",
                    "target": "PostgreSQL",
                }
            ]
        })
    )
    result = await client.get_relations("user1")
    assert len(result["results"]) == 1
    assert result["results"][0]["relationship"] == "decided"


@respx.mock
@pytest.mark.asyncio
async def test_search_graph():
    route = respx.post("https://test-mem0.example.com/v1/memories/search/")
    route.mock(return_value=httpx.Response(200, json={
        "results": [{"memory": "chose PostgreSQL", "score": 0.9}],
        "relations": [
            {
                "source": "Erkut",
                "relationship": "decided",
                "target": "PostgreSQL",
                "score": 0.85,
            }
        ],
    }))
    result = await client.search_graph("database decisions", "user1")
    assert "relations" in result
    assert len(result["relations"]) == 1
    body = json.loads(route.calls[0].request.content)
    assert body["api_version"] == "v2"


@respx.mock
@pytest.mark.asyncio
async def test_delete_entity():
    respx.delete("https://test-mem0.example.com/v1/entities/PostgreSQL/").mock(
        return_value=httpx.Response(200, json={"status": "deleted"})
    )
    result = await client.delete_entity("user1", "PostgreSQL")
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
