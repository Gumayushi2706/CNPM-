"""
Mô hình Mobility Hub, Vị trí đỗ (Parking Slot) và Cổng sạc (Charging Port)
"""

from enum import Enum
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class PortStatus(str, Enum):
    AVAILABLE = "AVAILABLE"       # Cổng sạc rảnh, sẵn sàng sạc
    CHARGING = "CHARGING"         # Đang cấp điện sạc xe
    RESERVED = "RESERVED"         # Đã được đặt lịch trước
    FAULTY = "FAULTY"             # Cổng sạc báo lỗi kỹ thuật
    MAINTENANCE = "MAINTENANCE"   # Tạm ngưng để bảo trì


class SlotStatus(str, Enum):
    AVAILABLE = "AVAILABLE"       # Vị trí đỗ còn trống
    OCCUPIED = "OCCUPIED"         # Đã có xe đang đỗ
    RESERVED = "RESERVED"         # Đã được đặt chỗ trước


class SlotType(str, Enum):
    SHARED_VEHICLE = "SHARED_VEHICLE"       # Chỗ đỗ dành cho xe công cộng (E-bike, E-scooter)
    PERSONAL_VEHICLE = "PERSONAL_VEHICLE"   # Chỗ đỗ dành cho xe điện cá nhân của sinh viên


class ChargingPort(BaseModel):
    id: str
    hub_id: str
    port_number: int
    port_type: str = "STANDARD_3_3KW"  # STANDARD_3_3KW, FAST_7_4KW, SUPER_11KW
    power_kw: float = 3.3
    status: PortStatus = PortStatus.AVAILABLE
    current_vehicle_id: Optional[str] = None
    total_kwh_delivered: float = 0.0
    active_session_id: Optional[str] = None

    def is_available(self) -> bool:
        return self.status == PortStatus.AVAILABLE and self.current_vehicle_id is None


class ParkingSlot(BaseModel):
    id: str
    hub_id: str
    slot_number: int
    slot_type: SlotType = SlotType.SHARED_VEHICLE
    status: SlotStatus = SlotStatus.AVAILABLE
    occupied_vehicle_id: Optional[str] = None
    has_charging_access: bool = True

    def is_available(self) -> bool:
        return self.status == SlotStatus.AVAILABLE and self.occupied_vehicle_id is None


class Hub(BaseModel):
    id: str
    code: str
    name: str
    category: str
    latitude: float
    longitude: float
    description: str
    capacity_slots: int
    capacity_chargers: int
    grid_power_limit_kw: float = 80.0
    slots: List[ParkingSlot] = Field(default_factory=list)
    ports: List[ChargingPort] = Field(default_factory=list)
    vehicle_ids: List[str] = Field(default_factory=list)

    # Các phương thức tính toán chỉ số thời gian thực
    def get_available_vehicles_count(self, vehicles_map: Dict[str, Any]) -> int:
        return sum(
            1 for v_id in self.vehicle_ids
            if v_id in vehicles_map and vehicles_map[v_id].status == "AVAILABLE"
        )

    def get_available_ebikes_count(self, vehicles_map: Dict[str, Any]) -> int:
        return sum(
            1 for v_id in self.vehicle_ids
            if v_id in vehicles_map and vehicles_map[v_id].status == "AVAILABLE" and vehicles_map[v_id].vehicle_type == "E_BIKE"
        )

    def get_available_escooters_count(self, vehicles_map: Dict[str, Any]) -> int:
        return sum(
            1 for v_id in self.vehicle_ids
            if v_id in vehicles_map and vehicles_map[v_id].status == "AVAILABLE" and vehicles_map[v_id].vehicle_type == "E_SCOOTER"
        )

    def get_available_slots_count(self, slot_type: Optional[SlotType] = None) -> int:
        if slot_type:
            return sum(1 for s in self.slots if s.is_available() and s.slot_type == slot_type)
        return sum(1 for s in self.slots if s.is_available())

    def get_available_ports_count(self) -> int:
        return sum(1 for p in self.ports if p.is_available())

    def get_current_power_draw_kw(self) -> float:
        return sum(p.power_kw for p in self.ports if p.status == PortStatus.CHARGING)

    def get_slot_utilization(self) -> float:
        if not self.slots:
            return 0.0
        occupied = sum(1 for s in self.slots if s.status == SlotStatus.OCCUPIED)
        return round((occupied / len(self.slots)) * 100.0, 1)

    def get_charger_utilization(self) -> float:
        if not self.ports:
            return 0.0
        charging = sum(1 for p in self.ports if p.status == PortStatus.CHARGING)
        return round((charging / len(self.ports)) * 100.0, 1)
