from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


class CustomerFields(SQLModel):
    name: str = Field(min_length=1, max_length=100, description="Customer's full name")
    email: str = Field(max_length=254, unique=True, index=True)
    phone: str | None = Field(default=None, max_length=30)
    company: str | None = Field(default=None, max_length=150)


class Customer(CustomerFields, table=True):
    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
