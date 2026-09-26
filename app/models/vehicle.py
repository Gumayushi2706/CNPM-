"""
Mô hình Phương tiện điện (Vehicles) trong Hệ thống E-Mobility Hub ĐHQG-HCM
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class VehicleType(str, Enum):
    E_BIKE = "E_BIKE"               # Xe đạp điện trợ lực
    E_SCOOTER = "E_SCOOTER"         # Xe máy điện chia sẻ
    PERSONAL_EV = "PERSONAL_EV"     # Xe điện cá nhân của sinh viên


class VehicleStatus(str, Enum):
    AVAILABLE = "AVAILABLE"         # Sẵn sàng cho thuê
    IN_USE = "IN_USE"               # Đang được sinh viên sử dụng
    CHARGING = "CHARGING"           # Đang cắm sạc tại Hub
    WAITING_CHARGE = "WAITING_CHARGE" # Chờ đến lượt sạc
    RESERVED = "RESERVED"           # Đã được đặt trước
    MAINTENANCE = "MAINTENANCE"     # Đang bảo trì định kỳ
    FAULTY = "FAULTY"               # Bị hỏng / sự cố kỹ thuật


class Vehicle(BaseModel):
    id: str
    plate_number: str
    vehicle_type: VehicleType
    model_name: str
    battery_soc: float = Field(default=100.0, ge=0.0, le=100.0, description="Mức pin SoC (%)")
    battery_capacity_kwh: float = Field(default=2.5, description="Dung lượng pin (kWh)")
    current_hub_id: Optional[str] = None
    current_slot_id: Optional[str] = None
    current_port_id: Optional[str] = None
    status: VehicleStatus = VehicleStatus.AVAILABLE
    total_trips: int = 0
    total_km: float = 0.0
    owner_id: Optional[str] = None  # None nếu là xe công cộng, có user_id nếu là xe cá nhân
    created_at: str = ""

    def is_usable(self, min_soc: float = 20.0) -> bool:
        """Kiểm tra xe có thể cho thuê ngay hay không"""
        return self.status == VehicleStatus.AVAILABLE and self.battery_soc >= min_soc

    def estimated_range_km(self) -> float:
        """Ước tính quãng đường còn đi được theo % pin"""
        # E-Bike: 100% pin ~ 50km; E-Scooter: 100% pin ~ 80km
        efficiency = 0.5 if self.vehicle_type == VehicleType.E_BIKE else 0.8
        return round(self.battery_soc * efficiency, 1)

    def to_dict(self):
        return self.model_dump()
