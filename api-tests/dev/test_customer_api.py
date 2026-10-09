import os
import uuid

import httpx


BASE_URL = os.environ.get("BASE_URL", "").rstrip("/")


def client() -> httpx.Client:
    if not BASE_URL:
        raise RuntimeError("BASE_URL must point to the deployed customer-api service")
    return httpx.Client(base_url=BASE_URL, timeout=15.0, follow_redirects=True)


def test_customer_crud_lifecycle() -> None:
    email = f"deployment-{uuid.uuid4().hex}@example.com"
    payload = {
        "name": "Deployment Validation Customer",
        "email": email,
        "company": "SparrowX",
    }

    with client() as api:
        created = api.post("/api/customers/", json=payload)
        assert created.status_code == 201, created.text
        customer = created.json()
        customer_id = customer["id"]

        fetched = api.get(f"/api/customers/{customer_id}")
        assert fetched.status_code == 200, fetched.text
        assert fetched.json()["email"] == email

        searched = api.get("/api/customers/", params={"search": email})
        assert searched.status_code == 200, searched.text
        assert any(item["id"] == customer_id for item in searched.json())

        updated = api.put(
            f"/api/customers/{customer_id}",
            json={"name": "Updated Deployment Customer"},
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["name"] == "Updated Deployment Customer"

        deleted = api.delete(f"/api/customers/{customer_id}")
        assert deleted.status_code == 204, deleted.text

        missing = api.get(f"/api/customers/{customer_id}")
        assert missing.status_code == 404, missing.text


def test_customer_api_rejects_duplicate_email() -> None:
    email = f"duplicate-{uuid.uuid4().hex}@example.com"
    payload = {"name": "Duplicate Test Customer", "email": email}

    with client() as api:
        first = api.post("/api/customers/", json=payload)
        assert first.status_code == 201, first.text
        customer_id = first.json()["id"]

        try:
            duplicate = api.post("/api/customers/", json=payload)
            assert duplicate.status_code == 409, duplicate.text
        finally:
            api.delete(f"/api/customers/{customer_id}")


def test_routed_openapi_contains_customer_routes() -> None:
    with client() as api:
        response = api.get("/api/customers/openapi.json")

    assert response.status_code == 200, response.text
    paths = response.json()["paths"]
    assert "/api/customers/" in paths
    assert "/api/customers/{customer_id}" in paths
