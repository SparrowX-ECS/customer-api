import os
from datetime import datetime, timezone
from typing import Annotated, Any, Generator

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import EmailStr
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Field, Session, SQLModel, create_engine, select


DATABASE_URL = os.getenv("CUSTOMER_API_DATABASE_URL", "sqlite:///./customer.db")


class CustomerFields(SQLModel):
    name: str = Field(min_length=1, max_length=100, description="Customer's full name")
    email: EmailStr = Field(description="Customer's email address")
    phone: str | None = Field(default=None, max_length=30, description="Optional phone number")
    company: str | None = Field(default=None, max_length=150, description="Optional company name")


class Customer(CustomerFields, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(max_length=254, unique=True, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CustomerCreate(CustomerFields):
    """Fields accepted when creating a customer."""


class CustomerUpdate(SQLModel):
    """All fields are optional for a partial update through PUT."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    email: str | None = Field(default=None, min_length=3, max_length=254)
    phone: str | None = Field(default=None, max_length=30)
    company: str | None = Field(default=None, max_length=150)


class CustomerRead(CustomerFields):
    id: int
    created_at: datetime
    updated_at: datetime


http_requests_total = Counter(
    "customer_api_http_requests_total",
    "Total HTTP requests handled by the Customer API",
    ("method", "path", "status"),
)
http_request_duration_seconds = Histogram(
    "customer_api_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ("method", "path"),
)
customers_created_total = Counter(
    "customer_api_customers_created_total",
    "Total number of customers created",
)


class MetricsMiddleware:
    def __init__(self, application: Any):
        self.application = application

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.application(scope, receive, send)
            return
        start = datetime.now(timezone.utc)
        status_code = 500

        async def record_response(message: dict[str, Any]) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        await self.application(scope, receive, record_response)
        duration = (datetime.now(timezone.utc) - start).total_seconds()
        path = scope.get("path", "unknown")
        http_requests_total.labels(scope["method"], path, str(status_code)).inc()
        http_request_duration_seconds.labels(scope["method"], path).observe(duration)


def create_app(database_url: str = DATABASE_URL, enable_metrics: bool = True) -> FastAPI:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, connect_args=connect_args)

    application = FastAPI(
        title="SparrowX Labs Customer API",
        description="Manages customer accounts for the Customer Experience team.",
        version="1.0.0",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:8080,http://localhost:3000").split(","),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    SQLModel.metadata.create_all(engine)
    application.state.engine = engine

    if enable_metrics:
        application.add_middleware(MetricsMiddleware)

    def get_session(request: Request) -> Generator[Session, None, None]:
        with Session(request.app.state.engine) as session:
            yield session

    SessionDependency = Annotated[Session, Depends(get_session)]

    @application.get("/health", tags=["system"], summary="Health check")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/metrics", tags=["system"], summary="Prometheus metrics", include_in_schema=False)
    def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @application.post(
        "/customers",
        response_model=CustomerRead,
        status_code=status.HTTP_201_CREATED,
        tags=["customers"],
        summary="Create a customer",
        responses={409: {"description": "A customer with this email already exists"}},
    )
    def create_customer(payload: CustomerCreate, session: SessionDependency) -> Customer:
        customer = Customer.model_validate(payload)
        session.add(customer)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(status_code=409, detail="A customer with this email already exists")
        session.refresh(customer)
        customers_created_total.inc()
        return customer

    @application.get(
        "/customers",
        response_model=list[CustomerRead],
        tags=["customers"],
        summary="List or search customers",
    )
    def list_customers(
        session: SessionDependency,
        search: str | None = Query(default=None, min_length=1, max_length=100, description="Search name, email, or company"),
        offset: int = Query(default=0, ge=0, description="Number of customers to skip"),
        limit: int = Query(default=100, ge=1, le=100, description="Maximum number of customers to return"),
    ) -> list[Customer]:
        statement = select(Customer)
        if search:
            pattern = f"%{search}%"
            statement = statement.where(
                Customer.name.ilike(pattern) | Customer.email.ilike(pattern) | Customer.company.ilike(pattern)
            )
        return list(session.exec(statement.order_by(Customer.id).offset(offset).limit(limit)))

    @application.get(
        "/customers/{customer_id}",
        response_model=CustomerRead,
        tags=["customers"],
        summary="Retrieve a customer",
        responses={404: {"description": "Customer not found"}},
    )
    def get_customer(customer_id: int, session: SessionDependency) -> Customer:
        customer = session.get(Customer, customer_id)
        if customer is None:
            raise HTTPException(status_code=404, detail="Customer not found")
        return customer

    @application.put(
        "/customers/{customer_id}",
        response_model=CustomerRead,
        tags=["customers"],
        summary="Update a customer",
        responses={404: {"description": "Customer not found"}, 409: {"description": "Email already exists"}},
    )
    def update_customer(customer_id: int, payload: CustomerUpdate, session: SessionDependency) -> Customer:
        customer = session.get(Customer, customer_id)
        if customer is None:
            raise HTTPException(status_code=404, detail="Customer not found")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(customer, field, value)
        customer.updated_at = datetime.now(timezone.utc)
        try:
            session.add(customer)
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(status_code=409, detail="A customer with this email already exists")
        session.refresh(customer)
        return customer

    @application.delete(
        "/customers/{customer_id}",
        response_model=None,
        status_code=status.HTTP_204_NO_CONTENT,
        tags=["customers"],
        summary="Delete a customer",
        responses={404: {"description": "Customer not found"}},
    )
    def delete_customer(customer_id: int, session: SessionDependency) -> None:
        customer = session.get(Customer, customer_id)
        if customer is None:
            raise HTTPException(status_code=404, detail="Customer not found")
        session.delete(customer)
        session.commit()

    return application


app = create_app()
