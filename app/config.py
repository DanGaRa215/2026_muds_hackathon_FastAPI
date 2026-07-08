import os

from dotenv import load_dotenv

load_dotenv()


def get_app_shared_secret() -> str:
    secret = os.environ.get("APP_SHARED_SECRET")
    if not secret:
        raise RuntimeError("APP_SHARED_SECRET environment variable is required")
    return secret


def get_anthropic_api_key() -> str | None:
    return os.environ.get("ANTHROPIC_API_KEY")


def get_anthropic_model() -> str:
    return os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")


def configure_langsmith() -> None:
    """Enable LangSmith tracing only when explicitly configured."""
    tracing = os.environ.get("LANGSMITH_TRACING", "false").lower() in {
        "1",
        "true",
        "yes",
    }
    if not tracing:
        os.environ["LANGSMITH_TRACING"] = "false"
        return

    if not os.environ.get("LANGSMITH_API_KEY"):
        os.environ["LANGSMITH_TRACING"] = "false"
        return

    os.environ.setdefault("LANGSMITH_PROJECT", "furniture-diagnosis")
