# em0-mcp-wrapper

MCP server that bridges [Claude Code](https://claude.ai/claude-code) to a self-hosted [mem0](https://github.com/mem0ai/mem0) instance.

## What it does

Provides 4 MCP tools to Claude Code:

| Tool | Purpose |
|------|---------|
| `add_memory` | Store knowledge (decisions, trade-offs, lessons) |
| `search_memory` | Semantic search across stored knowledge |
| `list_memories` | List all memories for a user/project |
| `delete_memory` | Delete a specific memory by ID |

## Installation

```bash
pip install git+https://github.com/seklabsnet/em0-mcp-wrapper.git
```

## Register with Claude Code

```bash
claude mcp add --scope user --transport stdio em0 \
  --env MEM0_API_URL=https://your-mem0-server.example.com \
  --env MEM0_API_KEY=$MEM0_API_KEY \
  --env MEM0_USER_ID=your-team \
  -- em0-mcp
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MEM0_API_URL` | Yes | — | mem0 server URL |
| `MEM0_API_KEY` | Yes | — | API key for authentication |
| `MEM0_USER_ID` | No | `centauri` | Default user/project scope |
| `MEM0_TIMEOUT` | No | `30` | Request timeout (seconds) |

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
