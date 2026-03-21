# em0-mcp-wrapper

MCP server that bridges [Claude Code](https://claude.ai/claude-code) to a self-hosted [mem0](https://github.com/mem0ai/mem0) instance.

Built on [FastMCP 3.x](https://github.com/jlowin/fastmcp).

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

## Features

### Immutable Memories
Mark critical decisions as immutable so they can't be updated or merged:
```
add_memory("We chose PostgreSQL for ACID compliance", immutable=True)
```

### Metadata Filters
Search with domain and type filters:
```
search_memory("database choice", filter_domain="backend", filter_type="decision")
```

### Memory History
Track how decisions evolved over time:
```
memory_history("memory-uuid-here")
```

### Graph Memory (Knowledge Graph)
When Neo4j is configured on the mem0 server, memories automatically build a knowledge graph:
```
add_memory("Erkut decided to use PostgreSQL for ACID compliance")
→ Creates: Erkut ──decided──→ PostgreSQL ──reason──→ ACID Compliance
```

Search with relationship traversal:
```
search_graph("what depends on PostgreSQL?")
→ Auth Service ──uses──→ PostgreSQL
  Payment Service ──uses──→ PostgreSQL
```

List all entities and relations:
```
get_entities()   → [PostgreSQL, Erkut, Auth Service, ...]
get_relations()  → [Erkut ──decided──→ PostgreSQL, ...]
```

### Input Validation
Content is validated for length (max 50K chars) and emptiness before sending to the server.

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
