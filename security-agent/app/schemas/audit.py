"""Safe audit-log response schema."""
from datetime import datetime
from pydantic import BaseModel
class AuditLogResponse(BaseModel):
    id: int; user_id: int | None; action: str; resource: str | None; ip_address: str | None; user_agent: str | None; status: str; details: str | None; created_at: datetime
