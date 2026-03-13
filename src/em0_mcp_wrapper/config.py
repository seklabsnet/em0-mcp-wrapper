"""Configuration — reads from environment variables, validates at startup."""

import os
import sys

MEM0_API_URL: str = os.environ.get("MEM0_API_URL", "").rstrip("/")
MEM0_API_KEY: str = os.environ.get("MEM0_API_KEY", "")
DEFAULT_USER_ID: str = os.environ.get("MEM0_USER_ID", "centauri")
REQUEST_TIMEOUT: int = int(os.environ.get("MEM0_TIMEOUT", "30"))


def validate() -> None:
    """Check required config, exit with clear error if missing."""
    errors = []
    if not MEM0_API_URL:
        errors.append("MEM0_API_URL")
    if not MEM0_API_KEY:
        errors.append("MEM0_API_KEY")
    if errors:
        print(
            f"ERROR: Missing required environment variables: {', '.join(errors)}\n"
            f"See: .env.example",
            file=sys.stderr,
        )
        sys.exit(1)
