import uuid


def _unique_email():
    return f"user-{uuid.uuid4().hex[:8]}@example.com"


def test_register_success(client):
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": _unique_email(),
            "password": "password123",
            "full_name": "Ada Lovelace",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["full_name"] == "Ada Lovelace"
    assert "hashed_password" not in body


def test_register_duplicate_email(client):
    email = _unique_email()
    payload = {"email": email, "password": "password123", "full_name": "Dup"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    assert client.post("/api/v1/auth/register", json=payload).status_code == 409


def test_register_short_password(client):
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": _unique_email(), "password": "short", "full_name": "Short"},
    )
    assert resp.status_code == 422


def test_login_wrong_password(client):
    email = _unique_email()
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": "Wrong"},
    )
    resp = client.post(
        "/api/v1/auth/login", data={"username": email, "password": "notthepassword"}
    )
    assert resp.status_code == 401


def test_me_requires_auth(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_me_with_auth(client, auth_headers):
    resp = client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Test User"


def test_refresh_token(client):
    email = _unique_email()
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": "Refresh"},
    )
    login = client.post(
        "/api/v1/auth/login", data={"username": email, "password": "password123"}
    )
    refresh_token = login.json()["refresh_token"]
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert resp.json()["access_token"]
