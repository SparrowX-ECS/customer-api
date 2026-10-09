import os

import httpx


BASE_URL = os.environ.get("BASE_URL", "").rstrip("/")


def client() -> httpx.Client:
    if not BASE_URL:
        raise RuntimeError("BASE_URL must point to the deployed customer-api service")
    return httpx.Client(base_url=BASE_URL, timeout=15.0, follow_redirects=True)


def test_health_endpoint() -> None:
    with client() as api:
        response = api.get("/api/customers/health")

    assert response.status_code == 200, response.text
    assert response.json() == {"status": "ok"}


def test_list_customers_is_readable() -> None:
    with client() as api:
        response = api.get("/api/customers/")

    assert response.status_code == 200, response.text
    assert isinstance(response.json(), list)


def test_openapi_contains_customer_routes() -> None:
    with client() as api:
        response = api.get("/openapi.json")

    assert response.status_code == 200, response.text
    paths = response.json()["paths"]
    assert "/api/customers/" in paths
    assert "/api/customers/{customer_id}" in paths


def test_metrics_endpoint_is_readable() -> None:
    with client() as api:
        response = api.get("/metrics")

    assert response.status_code == 200, response.text
    assert "text/plain" in response.headers.get("content-type", "")
