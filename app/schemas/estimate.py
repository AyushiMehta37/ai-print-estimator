from datetime import datetime
from typing import Dict, Any
from pydantic import BaseModel


class EstimateCreate(BaseModel):
    pricing: Dict[str, Any]
    total_price: float


class EstimateRead(BaseModel):
    id: int
    order_id: int
    pricing: Dict[str, Any]
    total_price: float
    version: int
    created_at: datetime

    model_config = {"from_attributes": True}
