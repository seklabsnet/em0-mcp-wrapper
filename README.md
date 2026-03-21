# em0-mcp-wrapper

MCP server that bridges [Claude Code](https://claude.ai/claude-code) to a self-hosted [mem0](https://github.com/mem0ai/mem0) instance with **knowledge graph** support.

Built on [FastMCP 3.x](https://github.com/jlowin/fastmcp). Backed by PostgreSQL + pgvector + Neo4j.

## What it does

Provides 12 MCP tools to Claude Code:

**Memory Tools:**

| Tool | Purpose |
|------|---------|
| `add_memory` | Store knowledge with metadata, immutable flag, and source tracking |
| `search_memory` | Semantic search with optional domain/type filters |
| `get_memory` | Get a single memory by ID with full details |
| `update_memory` | Update an existing memory's content |
| `list_memories` | List all memories for a user/project |
| `delete_memory` | Delete a specific memory by ID |
| `memory_history` | View edit history of a memory |
| `memory_stats` | Cross-project stats (total projects, memories per project) |

**Graph Memory Tools** (requires Neo4j on mem0 server):

| Tool | Purpose |
|------|---------|
| `get_entities` | List all entities (nodes) in the knowledge graph |
| `get_relations` | List all relationships between entities |
| `search_graph` | Search via relationship traversal ("what depends on X?") |
| `delete_entity` | Delete an entity and all its relations |

## Quick Start

```bash
# Install (macOS with Homebrew Python)
brew install pipx
pipx install git+https://github.com/seklabsnet/em0-mcp-wrapper.git

# Or with pip (conda, venv, or --break-system-packages)
pip install git+https://github.com/seklabsnet/em0-mcp-wrapper.git

# Setup (registers MCP server with Claude Code)
em0-setup
```

That's it. Restart Claude Code and the tools are available in **all your projects**.

## Updating

```bash
# pipx (recommended)
pipx uninstall em0-mcp-wrapper
pipx install git+https://github.com/seklabsnet/em0-mcp-wrapper.git

# pip
pip install --upgrade --force-reinstall git+https://github.com/seklabsnet/em0-mcp-wrapper.git
```

> **Note:** `pipx upgrade` may serve a cached version. Use uninstall + install to ensure you get the latest.

After updating, restart Claude Code to pick up the new version.

## Usage Guide

### Starting a Session

Always check existing knowledge first:

```
"what do we know about the auth module?"
→ Claude automatically calls search_memory
```

### Saving Knowledge

When a decision is made, a bug is found, or a trade-off is discussed:

```
"save this: we chose PostgreSQL because ACID compliance is required for payments"
→ Claude calls add_memory
→ Stored in pgvector (searchable) AND Neo4j (graph relationships)
→ Neo4j extracts: erkut ──decided──→ postgresql ──required_for──→ payments
```

For critical, irreversible decisions use immutable:

```
"save as immutable: our API versioning strategy is URL-based (/v1/, /v2/)"
→ Cannot be updated or merged after saving
```

### Searching

**Semantic search** — finds by meaning, not exact words:

```
"what ORM did we pick?"
→ Finds "Prisma was chosen over TypeORM because..."
```

**Filtered search** — narrow by domain or type:

```
"show me only backend decisions"
→ search_memory(filter_domain="backend", filter_type="decision")
```

**Graph search** — find relationships and dependencies:

```
"what depends on PostgreSQL?"
→ search_graph returns:
  postgresql ──used_for──→ centauri_project
  payment_service ──requires──→ postgresql
  auth_service ──uses──→ postgresql
```

### Metadata System

Each memory can have metadata for filtering:

| Field | Values | Example |
|-------|--------|---------|
| **domain** | auth, backend, frontend, infra, payments, devops, ... | `"backend"` |
| **type** | decision, architecture, business-rule, trade-off, bug-lesson, convention | `"decision"` |
| **source** | conversation, code-review, implementation, incident, documentation | `"code-review"` |

### Knowledge Graph

When you add a memory, Neo4j automatically extracts entities and relationships:

```
add_memory("Erkut decided to use PostgreSQL for ACID compliance")
```

Creates this graph:
```
erkut ──decided_to_use──→ postgresql
postgresql ──used_for──→ centauri_project
centauri_project ──requires──→ acid_compliance
```

Explore the graph:
```
get_entities()    → all people, systems, concepts in the graph
get_relations()   → all connections between entities
search_graph()    → traverse relationships for a specific query
```

### Tool Reference

**Daily use (frequent):**

| Tool | When | Example |
|------|------|---------|
| `search_memory` | Check what we know | "database decisions?" |
| `add_memory` | Save new knowledge | "save: Redis for caching" |

**Regular use:**

| Tool | When | Example |
|------|------|---------|
| `search_graph` | Find dependencies | "what depends on X?" |
| `get_entities` | See all graph nodes | "what's in our knowledge graph?" |
| `get_relations` | See all connections | "who decided what?" |
| `list_memories` | List everything | "all memories for centauri" |
| `get_memory` | Full detail of one memory | by ID from search results |
| `memory_history` | How a decision evolved | "history of this decision" |

**Rare use:**

| Tool | When |
|------|------|
| `update_memory` | Decision changed |
| `delete_memory` | Remove wrong/outdated entry |
| `delete_entity` | Remove a node from graph |
| `memory_stats` | Cross-project overview |

### Tips

1. **Search at session start** — ask "what do you know about this project?"
2. **Save the "why"** — "we chose X" is ok, "we chose X because Y" is gold
3. **Use immutable for contracts** — API schemas, DB schemas, public interfaces
4. **Query the graph before refactoring** — "what depends on X?" prevents surprises

## Multi-Project Support

Project ID is **auto-detected** from your git repo name — no config needed:

```
~/centauri/       → user_id: "centauri"
~/my-saas-app/    → user_id: "my-saas-app"
~/freelance/acme/ → user_id: "acme"
```

Each project gets its own isolated memory space. Same server, same DB — separated by project ID.

**Priority order:**
1. `MEM0_USER_ID` env var (if set, always wins)
2. Git remote repo name (parsed from `origin` URL)
3. Current directory name (fallback)

## Where to find your API key

`em0-setup` will ask for `MEM0_API_KEY` on first run. Here's where to find it:

| Method | Command |
|--------|---------|
| From an existing machine | `claude mcp get em0` (look for `MEM0_API_KEY=...`) |
| From Azure | `az containerapp show --name mem0-server --resource-group rg-mem0-prod --query "properties.template.containers[0].env[?name=='MEM0_API_KEY'].value" -o tsv` |
| From team | Ask whoever deployed the mem0 server |

## Setup Options

```bash
em0-setup                              # interactive (prompts for API key)
em0-setup --api-key sk-xxx             # pass key directly
em0-setup --user-id custom-id          # override auto-detection
em0-setup --api-url https://custom.url # custom server URL
```

## Manual Registration

If you prefer to register manually instead of using `em0-setup`:

```bash
claude mcp add --scope user --transport stdio em0 \
  --env MEM0_API_URL=https://your-mem0-server.example.com \
  --env MEM0_API_KEY=$MEM0_API_KEY \
  -- em0-mcp
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MEM0_API_URL` | Yes | — | mem0 server URL |
| `MEM0_API_KEY` | Yes | — | API key for authentication |
| `MEM0_USER_ID` | No | auto-detect | Override project ID (git repo name → dir name) |
| `MEM0_TIMEOUT` | No | `90` | Request timeout (seconds) |
| `MEM0_MAX_LENGTH` | No | `50000` | Max memory content length (chars) |

## Architecture

```
Claude Code
  ↓ MCP (stdio)
em0-mcp-wrapper (this repo)
  ↓ HTTP
mem0 server (Azure Container Apps)
  ↓              ↓
PostgreSQL     Neo4j
(pgvector)     (knowledge graph)
```

## Development

```bash
git clone https://github.com/seklabsnet/em0-mcp-wrapper.git
cd em0-mcp-wrapper
pip install -e ".[dev]"
pytest -v
ruff check src/ tests/
```

## License

MIT
