"""API and security tests for the Flask server (TC21-TC30)."""
import pytest
from app.server import create_app


@pytest.fixture
def client():
    return create_app().test_client()


def post(c, action, body):
    return c.post(f"/api/{action}", json=body)


def test_TC21_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.get_json()["status"] == "ok"


def test_TC22_home_page_served(client):
    r = client.get("/")
    assert r.status_code == 200 and b"SkillUp" in r.data


def test_TC23_security_headers_present(client):
    h = client.get("/").headers
    for name in ["X-Content-Type-Options", "X-Frame-Options", "Content-Security-Policy", "Referrer-Policy"]:
        assert name in h
    assert h["X-Frame-Options"] == "DENY" and h["X-Content-Type-Options"] == "nosniff"


def test_TC24_register_over_api(client):
    r = post(client, "register", {"name": "Neel", "email": "n@x.com", "role": "learner"}).get_json()
    assert r["ok"] and r["result"] == 3


def test_TC25_duplicate_email_rejected_over_api(client):
    body = {"name": "A", "email": "a@x.com", "role": "learner"}
    post(client, "register", body)
    assert post(client, "register", body).get_json()["ok"] is False


def test_TC26_overlong_input_rejected(client):
    r = post(client, "register", {"name": "A" * 500, "email": "a@x.com", "role": "learner"}).get_json()
    assert r["ok"] is False and "too long" in r["error"]


def test_TC27_malformed_json_returns_400(client):
    r = client.post("/api/register", data="not json", content_type="application/json")
    assert r.status_code == 400


def test_TC28_unknown_action_returns_404(client):
    assert post(client, "drop_database", {}).status_code == 404


def test_TC29_oversized_request_rejected(client):
    r = client.post("/api/register", data="x" * (70 * 1024), content_type="application/json")
    assert r.status_code == 413


def test_TC30_markup_is_stored_as_text_not_executed(client):
    """Server keeps the raw text; the UI escapes it (see app/static/index.html esc())."""
    payload = "<img src=x onerror=alert(1)>"
    post(client, "register", {"name": payload, "email": "x@x.com", "role": "learner"})
    st = client.get("/api/state").get_json()
    assert any(u["name"] == payload for u in st["users"])
    assert b"esc(" in client.get("/").data
