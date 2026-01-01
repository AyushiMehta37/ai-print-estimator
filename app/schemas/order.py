from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class OrderCreate(BaseModel):
    input_type: str = Field(..., examples=["text", "email", "pdf", "image"])
    raw_input: str


class OrderRead(BaseModel):
    id: int
    input_type: str
    raw_input: str

    extracted_specs: Optional[Dict[str, Any]] = None
    validation_flags: Optional[Dict[str, Any]] = None

    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
