from datetime import datetime, timezone
from typing import Generator

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from src.models import Customer
from src.schemas import CustomerCreate, CustomerRead, CustomerUpdate


router = APIRouter(prefix="/api/customer")


def get_session(request: Request) -> Generator[Session, None, None]:
    with Session(request.app.state.engine) as session:
        yield session


@router.post("/", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
def create_customer(payload: CustomerCreate, session: Session = Depends(get_session)) -> Customer:
    customer = Customer.model_validate(payload)
    session.add(customer)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="A customer with this email already exists")
    session.refresh(customer)
    return customer


@router.get("/", response_model=list[CustomerRead])
def list_customers(
    session: Session = Depends(get_session),
    search: str | None = Query(default=None, min_length=1, max_length=100),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
) -> list[Customer]:
    statement = select(Customer)
    if search:
        pattern = f"%{search}%"
        statement = statement.where(
            Customer.name.ilike(pattern)
            | Customer.email.ilike(pattern)
            | Customer.company.ilike(pattern)
        )
    return list(session.exec(statement.order_by(Customer.id).offset(offset).limit(limit)))


@router.get("/{customer_id}", response_model=CustomerRead)
def get_customer(customer_id: int, session: Session = Depends(get_session)) -> Customer:
    customer = session.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.put("/{customer_id}", response_model=CustomerRead)
def update_customer(customer_id: int, payload: CustomerUpdate, session: Session = Depends(get_session)) -> Customer:
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


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(customer_id: int, session: Session = Depends(get_session)) -> None:
    customer = session.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    session.delete(customer)
    session.commit()
