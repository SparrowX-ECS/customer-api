from datetime import datetime

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlmodel import Session

from app import CustomerCreate, CustomerUpdate, create_app


def endpoint(application, path, method):
    return next(route.endpoint for route in application.routes if getattr(route, "path", None) == path and method in route.methods)


def setup_app(tmp_path):
    application = create_app(f"sqlite:///{tmp_path / 'test.db'}", enable_metrics=False)
    return application, Session(application.state.engine)


def test_health_and_metrics(tmp_path):
    application, session = setup_app(tmp_path)
    session.close()
    assert endpoint(application, "/health", "GET")() == {"status": "ok"}
    metrics = endpoint(application, "/metrics", "GET")()
    assert metrics.status_code == 200


def test_customer_crud_and_search(tmp_path):
    application, session = setup_app(tmp_path)
    create = endpoint(application, "/customers", "POST")
    list_customers = endpoint(application, "/customers", "GET")
    get_customer = endpoint(application, "/customers/{customer_id}", "GET")
    update = endpoint(application, "/customers/{customer_id}", "PUT")
    delete = endpoint(application, "/customers/{customer_id}", "DELETE")

    customer = create(CustomerCreate(name="Ada Lovelace", email="ada@example.com", company="Analytical Engines"), session)
    assert customer.id == 1
    assert list_customers(session, "analytical", 0, 100)[0].id == customer.id
    assert get_customer(customer.id, session).email == "ada@example.com"
    updated = update(customer.id, CustomerUpdate(name="Ada Byron Lovelace"), session)
    assert updated.name == "Ada Byron Lovelace"
    assert delete(customer.id, session) is None
    with pytest.raises(HTTPException) as missing:
        get_customer(customer.id, session)
    assert missing.value.status_code == 404
    session.close()


def test_validation_duplicates_and_missing_customers(tmp_path):
    application, session = setup_app(tmp_path)
    create = endpoint(application, "/customers", "POST")
    with pytest.raises(ValidationError):
        CustomerCreate(name="", email="not-an-email")
    create(CustomerCreate(name="First", email="same@example.com"), session)
    with pytest.raises(HTTPException) as duplicate:
        create(CustomerCreate(name="Second", email="same@example.com"), session)
    assert duplicate.value.status_code == 409
    session.close()


def test_openapi_documents_contract(tmp_path):
    application, session = setup_app(tmp_path)
    spec = application.openapi()
    session.close()
    assert "/customers" in spec["paths"]
    assert "/customers/{customer_id}" in spec["paths"]
    assert "post" in spec["paths"]["/customers"]
    assert "delete" in spec["paths"]["/customers/{customer_id}"]
