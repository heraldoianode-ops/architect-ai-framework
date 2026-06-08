import uuid
from pydantic import BaseModel, Field
from typing import Optional
from app.models.property import PropertyType, OperationType, PropertyStatus


class PropertyCreate(BaseModel):
    address: str
    neighborhood: str | None = None
    city: str = "Buenos Aires"
    province: str = "CABA"
    property_type: PropertyType
    operation_type: OperationType
    price: float | None = None
    currency: str = "USD"
    expenses: float | None = None
    sqm_total: float | None = None
    sqm_covered: float | None = None
    rooms: int | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    parking: int = 0
    floor: int | None = None
    amenities: list[str] | None = None
    title: str | None = None
    description: str | None = None
    photos: list[str] | None = None
    latitude: float | None = None
    longitude: float | None = None


class PropertyUpdate(BaseModel):
    address: str | None = None
    neighborhood: str | None = None
    price: float | None = None
    status: PropertyStatus | None = None
    title: str | None = None
    description: str | None = None
    photos: list[str] | None = None
    amenities: list[str] | None = None
    sqm_total: float | None = None
    sqm_covered: float | None = None
    rooms: int | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None


class PropertyRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    agent_id: uuid.UUID | None
    address: str
    neighborhood: str | None
    city: str
    property_type: PropertyType
    operation_type: OperationType
    price: float | None
    currency: str
    sqm_total: float | None
    sqm_covered: float | None
    rooms: int | None
    bedrooms: int | None
    bathrooms: int | None
    parking: int
    status: PropertyStatus
    title: str | None
    description: str | None
    photos: list[str] | None
    amenities: list[str] | None
    source: str


class PropertyFilters(BaseModel):
    operation_type: OperationType | None = None
    property_type: PropertyType | None = None
    neighborhood: str | None = None
    city: str | None = None
    price_min: float | None = None
    price_max: float | None = None
    bedrooms: int | None = None
    status: PropertyStatus | None = None
    query: str | None = None  # full-text search
    limit: int = Field(default=20, le=100)
    offset: int = 0
