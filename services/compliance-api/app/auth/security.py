from datetime import UTC, datetime, timedelta

from jose import jwt
from passlib.context import CryptContext

from app.config import (
    get_access_token_expire_minutes,
    get_jwt_algorithm,
    get_jwt_secret_key,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str | int) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=get_access_token_expire_minutes())
    payload = {
        "sub": str(subject),
        "exp": expire,
    }
    return jwt.encode(
        payload,
        get_jwt_secret_key(),
        algorithm=get_jwt_algorithm(),
    )
