from jose import jwt

from app.auth.dependencies import get_current_user
from app.auth.security import verify_password
from app.config import get_jwt_algorithm, get_jwt_secret_key
from app.models import User


def _register_user(client, email: str, password: str) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert response.status_code == 201


def test_register_user(client, db_session):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "inspector@example.com",
            "password": "secure-password-123",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "inspector@example.com"
    assert "id" in body
    assert "created_at" in body
    assert "password" not in body
    assert "hashed_password" not in body

    user = db_session.get(User, body["id"])
    assert user is not None
    assert user.email == "inspector@example.com"
    assert verify_password("secure-password-123", user.hashed_password)
    assert not verify_password("wrong-password", user.hashed_password)


def test_register_user_duplicate_email(client):
    payload = {
        "email": "duplicate@example.com",
        "password": "secure-password-123",
    }

    first = client.post("/api/v1/auth/register", json=payload)
    second = client.post("/api/v1/auth/register", json=payload)

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["detail"] == "Email already registered"


def test_login_success(client, db_session):
    email = "login@example.com"
    password = "secure-password-123"
    _register_user(client, email, password)

    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]

    payload = jwt.decode(
        body["access_token"],
        get_jwt_secret_key(),
        algorithms=[get_jwt_algorithm()],
    )
    user = db_session.get(User, int(payload["sub"]))
    assert user is not None
    assert user.email == email


def test_login_wrong_password_returns_401(client):
    email = "wrong-password@example.com"
    _register_user(client, email, "correct-password")

    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "incorrect-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


def test_get_current_user_decodes_valid_token(client, db_session):
    email = "current-user@example.com"
    password = "secure-password-123"
    _register_user(client, email, password)

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    token = login_response.json()["access_token"]

    user = get_current_user(
        credentials=type("Credentials", (), {"credentials": token})(),
        db=db_session,
    )

    assert user.email == email
