#!/usr/bin/env bash
# em0 Knowledge Layer — Onboarding Script
#
# Takım arkadaşların bunu bir kere çalıştırır:
#   ./scripts/setup-em0.sh
#
# Ne yapar:
#   1. em0-mcp Python package'ını kurar
#   2. em0 MCP server'ı Claude Code'a register eder (global — tüm projelerde çalışır)
#   3. Global CLAUDE.md'ye em0 instruction ekler
#
# Gereksinimler:
#   - Claude Code CLI kurulu olmalı (claude komutu çalışmalı)
#   - Python 3.10+ ve pip/uv kurulu olmalı
#   - API key Erkut'tan alınmalı

set -euo pipefail

# ─── Colors ───
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo -e "${BLUE}  em0 Knowledge Layer — Setup${NC}"
echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo ""

# ─── Step 0: Check prerequisites ───
echo -e "${YELLOW}[1/4] Checking prerequisites...${NC}"

if ! command -v claude &> /dev/null; then
    echo -e "${RED}✗ Claude Code CLI not found. Install: npm install -g @anthropic-ai/claude-code${NC}"
    exit 1
fi
echo -e "  ${GREEN}✓${NC} Claude Code CLI"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 not found${NC}"
    exit 1
fi
echo -e "  ${GREEN}✓${NC} Python $(python3 --version | cut -d' ' -f2)"

# ─── Step 1: Install em0-mcp package ───
echo ""
echo -e "${YELLOW}[2/4] Installing em0-mcp package...${NC}"

# Try uv first, fallback to pip
if command -v uv &> /dev/null; then
    uv pip install --quiet "em0-mcp-wrapper @ git+https://github.com/seklabsnet/em0-mcp-wrapper.git" 2>/dev/null \
        && echo -e "  ${GREEN}✓${NC} Installed via uv" \
        || { pip install --quiet "em0-mcp-wrapper @ git+https://github.com/seklabsnet/em0-mcp-wrapper.git" && echo -e "  ${GREEN}✓${NC} Installed via pip"; }
else
    pip install --quiet "em0-mcp-wrapper @ git+https://github.com/seklabsnet/em0-mcp-wrapper.git" 2>/dev/null \
        && echo -e "  ${GREEN}✓${NC} Installed via pip" \
        || { echo -e "${RED}✗ Failed to install em0-mcp-wrapper${NC}"; exit 1; }
fi

# Verify em0-mcp command exists
if ! command -v em0-mcp &> /dev/null; then
    echo -e "${YELLOW}  ⚠ em0-mcp command not in PATH. Trying python -m em0_mcp_wrapper.server...${NC}"
fi

# ─── Step 2: Register MCP server ───
echo ""
echo -e "${YELLOW}[3/4] Registering em0 MCP server...${NC}"

# Check if already registered
if claude mcp list 2>/dev/null | grep -q "em0"; then
    echo -e "  ${GREEN}✓${NC} em0 already registered"
    echo ""
    echo -e "  Current config:"
    claude mcp get em0 2>/dev/null | grep -E "URL|KEY|Status" | sed 's/^/    /'
    echo ""
    read -p "  Re-register with new API key? (y/N): " REREGISTER
    if [[ "$REREGISTER" != "y" && "$REREGISTER" != "Y" ]]; then
        echo -e "  ${GREEN}✓${NC} Keeping existing config"
        SKIP_REGISTER=true
    fi
fi

if [[ "${SKIP_REGISTER:-}" != "true" ]]; then
    # API URL (hardcoded — same for everyone)
    MEM0_URL="https://mem0-server.happygrass-15b6b68c.westeurope.azurecontainerapps.io"

    # API Key (from user)
    echo ""
    read -sp "  em0 API Key (Erkut'tan al): " API_KEY
    echo ""

    if [[ -z "$API_KEY" ]]; then
        echo -e "${RED}✗ API key boş olamaz${NC}"
        exit 1
    fi

    # Remove old registration if exists
    claude mcp remove em0 -s user 2>/dev/null || true

    # Register
    claude mcp add em0 \
        -s user \
        -e "MEM0_API_URL=$MEM0_URL" \
        -e "MEM0_API_KEY=$API_KEY" \
        -- em0-mcp

    echo -e "  ${GREEN}✓${NC} em0 MCP server registered (global — tüm projelerde çalışır)"
fi

# ─── Step 3: Update global CLAUDE.md ───
echo ""
echo -e "${YELLOW}[4/4] Updating global CLAUDE.md...${NC}"

CLAUDE_MD="$HOME/.claude/CLAUDE.md"
EM0_MARKER="## em0 Knowledge Layer"

if [[ -f "$CLAUDE_MD" ]] && grep -q "$EM0_MARKER" "$CLAUDE_MD"; then
    echo -e "  ${GREEN}✓${NC} em0 instructions already in CLAUDE.md"
else
    mkdir -p "$HOME/.claude"
    cat >> "$CLAUDE_MD" << 'HEREDOC'

## em0 Knowledge Layer

Bu environment'ta em0 persistent memory sistemi aktif. em0, projeler arası bilgi grafiği ve semantic hafıza sağlar.

### Session Başında
- `search_memory` ile mevcut projenin son kararlarını ve mimarisini kontrol et
- user_id otomatik algılanır (git repo adından)

### Çalışırken
- Önemli kararlar alındığında `add_memory` ile kaydet (domain ve type belirt)
- Bug root cause bulunduğunda `add_memory` ile `immutable=true` olarak kaydet
- Bilmediğin bir konuda `search_all_projects` ile tüm projelerde ara

### Metadata Standartları
- **domain:** auth, backend, frontend, infra, ui, devops, general
- **type:** decision, architecture, business-rule, trade-off, bug-lesson, convention
- **source:** conversation, code-review, implementation, incident

HEREDOC
    echo -e "  ${GREEN}✓${NC} em0 instructions added to $CLAUDE_MD"
fi

# ─── Done ───
echo ""
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✓ em0 setup complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo ""
echo "  Şimdi herhangi bir projede Claude Code aç — em0 otomatik çalışacak."
echo "  user_id git repo adından otomatik algılanır."
echo ""
echo "  Test et:"
echo "    claude 'em0 da hangi projeler var?'"
echo ""
