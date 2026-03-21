"""MCP Server — exposes mem0 tools to Claude Code.

Usage:
  em0-mcp                           # pyproject.toml scripts entry point
  python -m em0_mcp_wrapper.server  # direct execution
"""

import json
import logging
import sys

from fastmcp import FastMCP

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


def _validate_content(content: str) -> str | None:
    """Validate memory content. Returns error message or None if valid."""
    if not content or not content.strip():
        return "Content cannot be empty."
    if len(content) > config.MAX_MEMORY_LENGTH:
        return f"Content too long ({len(content)} chars). Max: {config.MAX_MEMORY_LENGTH}."
    return None


# ─── Tool 1: Add Memory ───
@mcp.tool()
async def add_memory(
    content: str,
    user_id: str = "",
    domain: str = "",
    memory_type: str = "",
    source: str = "",
    immutable: bool = False,
) -> str:
    """Store knowledge in em0 persistent memory.

    Use when a decision is made, a bug root cause is found,
    a trade-off is discussed, or a business rule is shared.

    Args:
        content: The knowledge to remember
        domain: Feature area (e.g. auth, backend, frontend, infra)
        memory_type: decision, architecture, business-rule, trade-off,
            bug-lesson, user-insight, preference, convention
        source: conversation, code-review, implementation,
            story-planning, incident, documentation
        user_id: User/project scope (empty = default from config)
        immutable: If true, memory cannot be updated or merged
    """
    error = _validate_content(content)
    if error:
        return _dump({"error": error})

    uid = user_id or config.DEFAULT_USER_ID
    logger.info("add_memory: user=%s domain=%s immutable=%s", uid, domain, immutable)
    result = await client.add_memory(
        content=content,
        user_id=uid,
        metadata={"domain": domain, "type": memory_type, "source": source},
        immutable=immutable,
    )
    # Interpret empty results — mem0 returns [] when content is deduplicated
    if "results" in result and len(result["results"]) == 0:
        result["message"] = "Already known — mem0 deduplicated this (similar memory exists)."
    return _dump(result)


# ─── Tool 2: Search Memory ───
@mcp.tool()
async def search_memory(
    query: str,
    user_id: str = "",
    limit: int = 5,
    filter_domain: str = "",
    filter_type: str = "",
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
        filter_domain: Filter by domain (e.g. "auth", "backend")
        filter_type: Filter by type (e.g. "decision", "architecture")
    """
    uid = user_id or config.DEFAULT_USER_ID
    logger.info("search_memory: query='%s' user=%s", query, uid)

    # Build metadata filters
    filters: dict | None = None
    if filter_domain or filter_type:
        conditions = []
        if filter_domain:
            conditions.append({"metadata.domain": filter_domain})
        if filter_type:
            conditions.append({"metadata.type": filter_type})
        filters = {"AND": conditions} if len(conditions) > 1 else conditions[0]

    result = await client.search_memory(
        query=query, user_id=uid, limit=limit, filters=filters,
    )
    # Format results for readability
    if "results" in result:
        items = result["results"]
        if not items:
            return _dump({"result": f"No memories found for '{query}'."})
        lines = [f"Found {len(items)} memory(ies) for '{query}':\n"]
        for i, m in enumerate(items, 1):
            meta = m.get("metadata", {})
            domain_tag = meta.get("domain", "?")
            type_tag = meta.get("type", "?")
            source = meta.get("source", "?")
            lines.append(
                f"{i}. [{domain_tag}/{type_tag}] {m.get('memory', '')}\n"
                f"   score={m.get('score', '?'):.2f}"
                f" | source={source} | id={m.get('id', '?')}"
            )
        # Show graph relations if present (Neo4j enabled)
        relations = result.get("relations", [])
        if relations:
            lines.append(f"\nGraph Relations ({len(relations)}):")
            for r in relations:
                src = r.get("source", "?")
                rel = r.get("relationship", "?")
                tgt = r.get("target", "?")
                score = r.get("score", 0)
                lines.append(
                    f"  {src} ──{rel}──→ {tgt}"
                    f"  (score={score:.2f})"
                )
        return "\n".join(lines)
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
    # Show graph relations if present (Neo4j enabled)
    if isinstance(result, dict) and "relations" in result:
        relations = result["relations"]
        if relations:
            result["_graph_relations_count"] = len(relations)
    return _dump(result)


# ─── Tool 4: Get Memory ───
@mcp.tool()
async def get_memory(memory_id: str) -> str:
    """Get a single memory by ID with full details.

    Args:
        memory_id: UUID of the memory (get from search or list results)
    """
    logger.info("get_memory: id=%s", memory_id)
    result = await client.get_memory(memory_id=memory_id)
    return _dump(result)


# ─── Tool 5: Update Memory ───
@mcp.tool()
async def update_memory(memory_id: str, content: str) -> str:
    """Update an existing memory's content.

    Use when a decision changes, information becomes outdated,
    or a memory needs correction. Immutable memories cannot be updated.

    Args:
        memory_id: UUID of the memory to update (get from search or list)
        content: The new content to replace the existing memory
    """
    error = _validate_content(content)
    if error:
        return _dump({"error": error})

    logger.info("update_memory: id=%s", memory_id)
    result = await client.update_memory(memory_id=memory_id, content=content)
    return _dump(result)


# ─── Tool 6: Delete Memory ───
@mcp.tool()
async def delete_memory(memory_id: str) -> str:
    """Delete a specific memory by ID.

    Args:
        memory_id: UUID of the memory to delete (get from search or list)
    """
    logger.info("delete_memory: id=%s", memory_id)
    result = await client.delete_memory(memory_id=memory_id)
    return _dump(result)


# ─── Tool 7: Memory History ───
@mcp.tool()
async def memory_history(memory_id: str) -> str:
    """View the edit history of a memory — see how it changed over time.

    Useful for understanding why a decision evolved or was corrected.

    Args:
        memory_id: UUID of the memory (get from search or list)
    """
    logger.info("memory_history: id=%s", memory_id)
    result = await client.memory_history(memory_id=memory_id)
    if "error" in result:
        return _dump(result)
    # Format history entries
    if isinstance(result, list):
        if not result:
            return _dump({"result": "No history found for this memory."})
        lines = [f"History ({len(result)} version(s)):\n"]
        for i, entry in enumerate(result, 1):
            old = entry.get("old_memory", entry.get("previous_value", "—"))
            new = entry.get("new_memory", entry.get("new_value", "—"))
            event = entry.get("event", "UPDATE")
            ts = entry.get("created_at", entry.get("timestamp", "?"))
            lines.append(f"{i}. [{event}] {ts}")
            lines.append(f"   Before: {old}")
            lines.append(f"   After:  {new}")
        return "\n".join(lines)
    return _dump(result)


# ─── Tool 8: Stats ───
@mcp.tool()
async def memory_stats() -> str:
    """Show cross-project statistics — how many projects use mem0, memory count per project.

    Use when the user asks about mem0 usage, how many projects, or overall stats.
    """
    logger.info("memory_stats")
    result = await client.get_stats()
    if "error" in result:
        return _dump(result)
    lines = [f"mem0 Stats (v{result.get('version', '?')}):\n"]
    lines.append(f"Total projects: {result.get('total_projects', 0)}")
    lines.append(f"Total memories: {result.get('total_memories', 0)}\n")
    projects = result.get("projects", {})
    if projects:
        lines.append("Per project:")
        for name, count in projects.items():
            lines.append(f"  {name}: {count} memories")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════
# Graph Memory Tools (requires Neo4j on mem0 server)
# ═══════════════════════════════════════════════════


# ─── Tool 9: Get Entities ───
@mcp.tool()
async def get_entities(user_id: str = "") -> str:
    """List all entities (nodes) in the knowledge graph.

    Shows people, systems, concepts, and other entities
    extracted from stored memories.

    Args:
        user_id: User/project scope (empty = default from config)
    """
    uid = user_id or config.DEFAULT_USER_ID
    logger.info("get_entities: user=%s", uid)
    result = await client.get_entities(user_id=uid)
    if "error" in result:
        return _dump(result)
    # Format entities for readability
    entities = result.get("results", result) if isinstance(result, dict) else result
    if isinstance(entities, list):
        if not entities:
            return _dump({"result": "No entities in graph yet."})
        lines = [f"Knowledge Graph Entities ({len(entities)}):\n"]
        for e in entities:
            name = e.get("name", e.get("entity", "?"))
            etype = e.get("type", e.get("entity_type", "?"))
            lines.append(f"  [{etype}] {name}")
        return "\n".join(lines)
    return _dump(result)


# ─── Tool 10: Get Relations ───
@mcp.tool()
async def get_relations(user_id: str = "") -> str:
    """List all relationships in the knowledge graph.

    Shows how entities are connected — who decided what,
    which service depends on which database, etc.

    Args:
        user_id: User/project scope (empty = default from config)
    """
    uid = user_id or config.DEFAULT_USER_ID
    logger.info("get_relations: user=%s", uid)
    result = await client.get_relations(user_id=uid)
    if "error" in result:
        return _dump(result)
    relations = result.get("results", result) if isinstance(result, dict) else result
    if isinstance(relations, list):
        if not relations:
            return _dump({"result": "No relations in graph yet."})
        lines = [f"Knowledge Graph Relations ({len(relations)}):\n"]
        for r in relations:
            src = r.get("source", r.get("from", "?"))
            rel = r.get("relationship", r.get("relation", "?"))
            tgt = r.get("target", r.get("to", "?"))
            lines.append(f"  {src} ──{rel}──→ {tgt}")
        return "\n".join(lines)
    return _dump(result)


# ─── Tool 11: Search Graph ───
@mcp.tool()
async def search_graph(
    query: str,
    user_id: str = "",
    limit: int = 5,
) -> str:
    """Search using the knowledge graph (relationship traversal).

    Unlike search_memory (vector similarity), this traverses
    entity relationships. Best for questions like:
    - "What depends on PostgreSQL?"
    - "What decisions did Erkut make?"
    - "What's connected to the auth service?"

    Args:
        query: Natural language query
        user_id: User/project scope (empty = default from config)
        limit: Max results (default: 5)
    """
    uid = user_id or config.DEFAULT_USER_ID
    logger.info("search_graph: query='%s' user=%s", query, uid)
    result = await client.search_graph(query=query, user_id=uid, limit=limit)
    if "error" in result:
        return _dump(result)
    lines = []
    # Vector results (still returned alongside)
    items = result.get("results", [])
    if items:
        lines.append(f"Memory Results ({len(items)}):\n")
        for i, m in enumerate(items, 1):
            lines.append(f"  {i}. {m.get('memory', '?')}")
    # Graph relations — the main value
    relations = result.get("relations", [])
    if relations:
        lines.append(f"\nGraph Relations ({len(relations)}):")
        for r in relations:
            src = r.get("source", "?")
            rel = r.get("relationship", "?")
            tgt = r.get("target", "?")
            score = r.get("score", 0)
            lines.append(
                f"  {src} ──{rel}──→ {tgt}"
                f"  (score={score:.2f})"
            )
    if not lines:
        return _dump({"result": f"No graph results for '{query}'."})
    return "\n".join(lines)


# ─── Tool 12: Delete Entity ───
@mcp.tool()
async def delete_entity(
    entity_name: str,
    user_id: str = "",
) -> str:
    """Delete an entity and all its relations from the knowledge graph.

    WARNING: This removes the entity node and all edges connected to it.

    Args:
        entity_name: Name of the entity to delete
        user_id: User/project scope (empty = default from config)
    """
    uid = user_id or config.DEFAULT_USER_ID
    logger.info("delete_entity: entity=%s user=%s", entity_name, uid)
    result = await client.delete_entity(user_id=uid, entity_name=entity_name)
    return _dump(result)


# ─── Entrypoint ───
def main():
    logger.info("em0 MCP wrapper v0.4.0 starting → %s", config.MEM0_API_URL)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
