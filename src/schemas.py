from datetime import datetime

from pydantic import EmailStr
from sqlmodel import Field, SQLModel


class CustomerCreate(SQLModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=30)
    company: str | None = Field(default=None, max_length=150)


class CustomerUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    company: str | None = Field(default=None, max_length=150)


class CustomerRead(SQLModel):
    id: int
    name: str
    email: EmailStr
    phone: str | None
    company: str | None
    created_at: datetime
    updated_at: datetime
