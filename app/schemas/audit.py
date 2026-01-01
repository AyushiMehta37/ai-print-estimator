from datetime import datetime
from pydantic import BaseModel


class AuditCreate(BaseModel):
    action: str
    actor: str
    notes: str | None = None


class AuditRead(BaseModel):
    id: int
    order_id: int
    action: str
    actor: str
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
