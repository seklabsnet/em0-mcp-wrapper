"""Tests for MCP server tool registration."""

from em0_mcp_wrapper import config

# Set config before importing server
config.MEM0_API_URL = "https://test-mem0.example.com"
config.MEM0_API_KEY = "test-key"


def test_version():
    from em0_mcp_wrapper import __version__
    assert __version__ == "0.1.0"


def test_config_validate_passes():
    """With URL and key set, validate should not raise."""
    config.MEM0_API_URL = "https://test.example.com"
    config.MEM0_API_KEY = "key"
    # Should not raise
    config.validate()
