import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health_and_metrics(client: AsyncClient) -> None:
    health = await client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}

    metrics = await client.get("/metrics")
    assert metrics.status_code == 200


@pytest.mark.anyio
async def test_customer_crud_and_search(client: AsyncClient) -> None:
    email = f"deployment-{uuid.uuid4().hex}@example.com"
    payload = {
        "name": "Ada Lovelace",
        "email": email,
        "company": "Analytical Engines",
    }

    created = await client.post("/api/customers/", json=payload)
    assert created.status_code == 201, created.text
    customer = created.json()
    customer_id = customer["id"]

    try:
        listed = await client.get("/api/customers/", params={"search": "analytical"})
        assert listed.status_code == 200, listed.text
        assert any(item["id"] == customer_id for item in listed.json())

        fetched = await client.get(f"/api/customers/{customer_id}")
        assert fetched.status_code == 200, fetched.text
        assert fetched.json()["email"] == email

        updated = await client.put(
            f"/api/customers/{customer_id}",
            json={"name": "Ada Byron Lovelace"},
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["name"] == "Ada Byron Lovelace"

        deleted = await client.delete(f"/api/customers/{customer_id}")
        assert deleted.status_code == 204, deleted.text
    finally:
        # Cleanup is safe if the delete assertion already succeeded.
        await client.delete(f"/api/customers/{customer_id}")

    missing = await client.get(f"/api/customers/{customer_id}")
    assert missing.status_code == 404, missing.text


@pytest.mark.anyio
async def test_validation_duplicates_and_missing_customers(client: AsyncClient) -> None:
    invalid = await client.post(
        "/api/customers/",
        json={"name": "", "email": "not-an-email"},
    )
    assert invalid.status_code == 422, invalid.text

    email = f"duplicate-{uuid.uuid4().hex}@example.com"
    payload = {"name": "First", "email": email}
    first = await client.post("/api/customers/", json=payload)
    assert first.status_code == 201, first.text
    customer_id = first.json()["id"]

    try:
        duplicate = await client.post(
            "/api/customers/",
            json={"name": "Second", "email": email},
        )
        assert duplicate.status_code == 409, duplicate.text
    finally:
        await client.delete(f"/api/customers/{customer_id}")

    missing = await client.get("/api/customers/999999")
    assert missing.status_code == 404, missing.text


@pytest.mark.anyio
async def test_openapi_documents_contract(client: AsyncClient) -> None:
    response = await client.get("/openapi.json")
    assert response.status_code == 200, response.text

    paths = response.json()["paths"]
    assert "/api/customers/" in paths
    assert "/api/customers/{customer_id}" in paths
    assert "post" in paths["/api/customers/"]
    assert "delete" in paths["/api/customers/{customer_id}"]
