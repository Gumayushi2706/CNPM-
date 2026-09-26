"""
Mô hình Đặt chỗ (Booking), Chuyến đi (Trip) và Phiên sạc (ChargingSession)
"""

from enum import Enum
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class BookingType(str, Enum):
    VEHICLE_RENTAL = "VEHICLE_RENTAL"             # Đặt xe công cộng (E-bike, E-scooter)
    PARKING_RESERVATION = "PARKING_RESERVATION"   # Đặt trước chỗ đỗ xe cá nhân
    CHARGING_RESERVATION = "CHARGING_RESERVATION" # Đặt trước lịch sạc


class BookingStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class Booking(BaseModel):
    id: str
    user_id: str
    user_name: str
    booking_type: BookingType
    hub_id: str
    destination_hub_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    slot_id: Optional[str] = None
    port_id: Optional[str] = None
    status: BookingStatus = BookingStatus.CONFIRMED
    start_time: str = Field(default_factory=lambda: datetime.now().isoformat())
    end_time: Optional[str] = None
    estimated_cost: float = 0.0
    actual_cost: float = 0.0
    note: str = ""


class Trip(BaseModel):
    id: str
    booking_id: str
    user_id: str
    vehicle_id: str
    origin_hub_id: str
    destination_hub_id: Optional[str] = None
    start_time: str = Field(default_factory=lambda: datetime.now().isoformat())
    end_time: Optional[str] = None
    duration_minutes: float = 0.0
    distance_km: float = 0.0
    start_soc: float = 100.0
    end_soc: float = 100.0
    fare: float = 0.0
    status: str = "IN_PROGRESS"  # IN_PROGRESS, COMPLETED


class ChargingSession(BaseModel):
    id: str
    hub_id: str
    port_id: str
    vehicle_id: str
    user_id: str
    start_soc: float
    target_soc: float = 100.0
    current_soc: float
    power_kw: float
    start_time: str = Field(default_factory=lambda: datetime.now().isoformat())
    estimated_end_time: Optional[str] = None
    actual_end_time: Optional[str] = None
    energy_consumed_kwh: float = 0.0
    total_fee: float = 0.0
    priority_score: float = 0.0
    status: str = "CHARGING"  # QUEUED, CHARGING, COMPLETED, SUSPENDED
