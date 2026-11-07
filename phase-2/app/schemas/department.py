"""Department schemas."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict


class DepartmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    department_id: str
    department_name: str
    cost_center: str
    description: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
