"""
Mô hình Quản lý Sự cố (Incident Management) trong Hệ thống E-Mobility Hub
"""

from enum import Enum
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class IncidentSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IncidentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INVESTIGATING = "INVESTIGATING"
    RESOLVED = "RESOLVED"


class IncidentEntityType(str, Enum):
    CHARGING_PORT = "CHARGING_PORT"
    VEHICLE = "VEHICLE"
    PARKING_SLOT = "PARKING_SLOT"
    HUB_GRID = "HUB_GRID"


class Incident(BaseModel):
    id: str
    hub_id: str
    entity_type: IncidentEntityType
    entity_id: str
    severity: IncidentSeverity = IncidentSeverity.MEDIUM
    description: str
    action_taken: str = ""
    reported_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    resolved_at: Optional[str] = None
    status: IncidentStatus = IncidentStatus.ACTIVE
