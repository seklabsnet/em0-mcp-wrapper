"""MCP Server — exposes mem0 tools to Claude Code.

Usage:
  em0-mcp                           # pyproject.toml scripts entry point
  python -m em0_mcp_wrapper.server  # direct execution
"""

import json
import logging
import sys

from mcp.server.fastmcp import FastMCP

from . import client, config

# ─── Logging (stderr — stdout is reserved for MCP protocol) ───
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("em0-mcp")

# ─── Config validation ───
config.validate()

# ─── MCP Server ───
mcp = FastMCP(
    "em0-knowledge-layer",
    instructions=(
        "em0 Knowledge Layer — persistent team memory across sessions. "
        "Stores decisions, trade-offs, architecture choices, and lessons. "
        "Search at session start for context. "
        "Store important decisions with add_memory."
    ),
)


def _dump(data: dict) -> str:
    """JSON serialize — all tools return this."""
    return json.dumps(data, ensure_ascii=False, indent=2)


# ─── Tool 1: Add Memory ───
@mcp.tool()
async def add_memory(
    content: str,
    user_id: str = "",
    domain: str = "",
    memory_type: str = "",
) -> str:
    """Store knowledge in em0 persistent memory.

    Use when a decision is made, a bug root cause is found,
    a trade-off is discussed, or a business rule is shared.

    Args:
        content: The knowledge to remember (e.g. "We chose Prisma over TypeORM because...")
        domain: Feature area — home-feed, auth, poi-system, payments, social, journey, matching, notifications, settings, general, backend, frontend, devops, infra
        memory_type: Type — decision, architecture, business-rule, trade-off, bug-lesson, user-insight, preference, convention
        user_id: User/project scope (empty = default from config)
    """
    uid = user_id or config.DEFAULT_USER_ID
    logger.info("add_memory: user=%s domain=%s", uid, domain)
    result = await client.add_memory(
        content=content,
        user_id=uid,
        metadata={"domain": domain, "type": memory_type},
    )
    return _dump(result)


# ─── Tool 2: Search Memory ───
@mcp.tool()
async def search_memory(
    query: str,
    user_id: str = "",
    limit: int = 5,
) -> str:
    """Search em0 memory with semantic search.

    No exact match needed — searches by meaning.
    "which ORM?" will find "Prisma was chosen".

    IMPORTANT: Always call this before starting work on a feature
    to check for existing decisions.

    Args:
        query: Natural language search query
        user_id: User/project scope (empty = default from config)
        limit: Max results (default: 5)
    """
    uid = user_id or config.DEFAULT_USER_ID
    logger.info("search_memory: query='%s' user=%s", query, uid)
    result = await client.search_memory(query=query, user_id=uid, limit=limit)
    return _dump(result)


# ─── Tool 3: List Memories ───
@mcp.tool()
async def list_memories(user_id: str = "") -> str:
    """List all stored memories.

    Args:
        user_id: User/project scope (empty = default from config)
    """
    uid = user_id or config.DEFAULT_USER_ID
    logger.info("list_memories: user=%s", uid)
    result = await client.list_memories(user_id=uid)
    return _dump(result)


# ─── Tool 4: Delete Memory ───
@mcp.tool()
async def delete_memory(memory_id: str) -> str:
    """Delete a specific memory by ID.

    Args:
        memory_id: UUID of the memory to delete (get from search or list)
    """
    logger.info("delete_memory: id=%s", memory_id)
    result = await client.delete_memory(memory_id=memory_id)
    return _dump(result)


# ─── Entrypoint ───
def main():
    logger.info("em0 MCP wrapper starting → %s", config.MEM0_API_URL)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
