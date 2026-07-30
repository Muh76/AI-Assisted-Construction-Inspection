import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

DEFAULT_DATABASE_URL = (
    "postgresql+psycopg2://postgres:postgres@localhost:5432/compliance"
)
DEFAULT_JWT_ALGORITHM = "HS256"
DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 60
DEFAULT_OPENAI_VISION_MODEL = "gpt-4o-mini"


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def get_jwt_secret_key() -> str:
    secret_key = os.getenv("JWT_SECRET_KEY")
    if not secret_key:
        raise RuntimeError("JWT_SECRET_KEY environment variable is not set")
    return secret_key


def get_jwt_algorithm() -> str:
    return os.getenv("JWT_ALGORITHM", DEFAULT_JWT_ALGORITHM)


def get_access_token_expire_minutes() -> int:
    raw_value = os.getenv(
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        str(DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return int(raw_value)


def get_repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent


def get_data_raw_dir() -> Path:
    return get_repo_root() / "data" / "raw"


def get_data_regulations_dir() -> Path:
    return get_repo_root() / "data" / "regulations"


def get_openai_api_key() -> str | None:
    return os.getenv("OPENAI_API_KEY")


def get_openai_vision_model() -> str:
    return os.getenv("OPENAI_VISION_MODEL", DEFAULT_OPENAI_VISION_MODEL)
