import os

from dotenv import load_dotenv

load_dotenv()

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def get_app_shared_secret() -> str:
    secret = os.environ.get("APP_SHARED_SECRET")
    if not secret:
        raise RuntimeError("APP_SHARED_SECRET environment variable is required")
    return secret


def get_openrouter_api_key() -> str | None:
    return os.environ.get("OPENROUTER_API_KEY")


def get_openrouter_model() -> str:
    return os.environ.get("OPENROUTER_MODEL", "qwen/qwen3-vl-32b-instruct")


def get_openrouter_base_url() -> str:
    return os.environ.get("OPENROUTER_BASE_URL", OPENROUTER_BASE_URL)


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
