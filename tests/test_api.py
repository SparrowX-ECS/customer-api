from datetime import datetime

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlmodel import SQLModel, Session

from src.main import create_app
from src.schemas import CustomerCreate, CustomerUpdate


def endpoint(application, path, method):
    return next(route.endpoint for route in application.routes if getattr(route, "path", None) == path and method in route.methods)


def setup_app():
    application = create_app(enable_metrics=False)
    SQLModel.metadata.drop_all(application.state.engine)
    SQLModel.metadata.create_all(application.state.engine)
    return application, Session(application.state.engine)


def test_health_and_metrics():
    application, session = setup_app()
    session.close()
    assert endpoint(application, "/health", "GET")() == {"status": "ok"}
    metrics = endpoint(application, "/metrics", "GET")()
    assert metrics.status_code == 200


def test_customer_crud_and_search():
    application, session = setup_app()
    create = endpoint(application, "/api/customer/", "POST")
    list_customers = endpoint(application, "/api/customer/", "GET")
    get_customer = endpoint(application, "/api/customer/{customer_id}", "GET")
    update = endpoint(application, "/api/customer/{customer_id}", "PUT")
    delete = endpoint(application, "/api/customer/{customer_id}", "DELETE")

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


def test_validation_duplicates_and_missing_customers():
    application, session = setup_app()
    create = endpoint(application, "/api/customer/", "POST")
    with pytest.raises(ValidationError):
        CustomerCreate(name="", email="not-an-email")
    create(CustomerCreate(name="First", email="same@example.com"), session)
    with pytest.raises(HTTPException) as duplicate:
        create(CustomerCreate(name="Second", email="same@example.com"), session)
    assert duplicate.value.status_code == 409
    session.close()


def test_openapi_documents_contract():
    application, session = setup_app()
    spec = application.openapi()
    session.close()
    assert "/api/customer/" in spec["paths"]
    assert "/api/customer/{customer_id}" in spec["paths"]
    assert "post" in spec["paths"]["/api/customer/"]
    assert "delete" in spec["paths"]["/api/customer/{customer_id}"]
