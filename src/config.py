"""Environment variable loading and validation."""
import os

REQUIRED_ENV_VARS = ["ANTHROPIC_API_KEY", "VOYAGE_API_KEY", "NEON_DATABASE_URL"]


def check_env() -> None:
    missing = [v for v in REQUIRED_ENV_VARS if not os.environ.get(v)]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}. "
            "Copy .env.example to .env and fill them in."
        )
