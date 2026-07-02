import pytest
from httpx import ASGITransport, AsyncClient

from app.core.db import init_db
from app.main import app


@pytest.fixture
async def client():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_register_login_and_auth_gate(client):
    email = "user1@example.com"
    register = await client.post("/auth/register",
                                 json={"email": email, "password": "secret123"})
    assert register.status_code == 200
    token = register.json()["access_token"]

    duplicate = await client.post("/auth/register",
                                  json={"email": email, "password": "secret123"})
    assert duplicate.status_code == 409

    login = await client.post("/auth/login", json={"email": email, "password": "secret123"})
    assert login.status_code == 200

    bad_login = await client.post("/auth/login", json={"email": email, "password": "wrong-pass"})
    assert bad_login.status_code == 401

    unauthorized = await client.get("/dashboard")
    assert unauthorized.status_code == 401

    dashboard = await client.get("/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert dashboard.status_code == 200
    assert dashboard.json()["latest"] is None


@pytest.mark.asyncio
async def test_create_run_and_fetch(client, monkeypatch):
    async def fake_execute_run(run_id: int) -> None:
        return None

    monkeypatch.setattr("app.routers.runs.execute_run", fake_execute_run)

    register = await client.post("/auth/register",
                                 json={"email": "user2@example.com", "password": "secret123"})
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    created = await client.post(
        "/runs",
        data={"target_role": "ai_engineer",
              "links": '["https://github.com/janedoe"]'},
        headers=headers,
    )
    assert created.status_code == 200, created.text
    run_id = created.json()["id"]

    fetched = await client.get(f"/runs/{run_id}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["target_role"] == "ai_engineer"

    suggestions = await client.get(f"/runs/{run_id}/suggestions", headers=headers)
    assert suggestions.status_code == 200
    assert suggestions.json() == []

    # Another user must not see someone else's run.
    other = await client.post("/auth/register",
                              json={"email": "user3@example.com", "password": "secret123"})
    other_headers = {"Authorization": f"Bearer {other.json()['access_token']}"}
    stranger = await client.get(f"/runs/{run_id}", headers=other_headers)
    assert stranger.status_code == 404
