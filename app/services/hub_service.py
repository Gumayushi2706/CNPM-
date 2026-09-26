"""
Dịch vụ Quản lý Mạng lưới Mobility Hub (Hub Management Service)
"""

import math
from typing import Dict, List, Optional, Any, Tuple
from ..config import HUBS_SEED_DATA, ALERT_THRESHOLDS, PORT_TYPES
from ..models.hub import Hub, ParkingSlot, ChargingPort, SlotStatus, SlotType, PortStatus
from ..models.vehicle import Vehicle, VehicleType, VehicleStatus


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Tính khoảng cách đường chim bay giữa 2 tọa độ (km)"""
    R = 6371.0  # Bán kính trái đất (km)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)


class HubService:
    def __init__(self):
        self.hubs: Dict[str, Hub] = {}
        self.vehicles: Dict[str, Vehicle] = {}
        self._initialize_seed_data()

    def _initialize_seed_data(self):
        """Khởi tạo 6 Hub cùng phương tiện và trạm sạc mẫu tại ĐHQG-HCM"""
        vehicle_counter = 1

        for data in HUBS_SEED_DATA:
            hub_id = data["id"]
            slots: List[ParkingSlot] = []
            ports: List[ChargingPort] = []
            vehicle_ids: List[str] = []

            # 1. Khởi tạo danh sách vị trí đỗ (Parking Slots)
            # 70% dành cho xe công cộng, 30% dành cho xe cá nhân sinh viên
            shared_slots_count = int(data["capacity_slots"] * 0.7)
            for s_idx in range(1, data["capacity_slots"] + 1):
                slot_type = SlotType.SHARED_VEHICLE if s_idx <= shared_slots_count else SlotType.PERSONAL_VEHICLE
                slots.append(ParkingSlot(
                    id=f"{hub_id}_SLOT_{s_idx:02d}",
                    hub_id=hub_id,
                    slot_number=s_idx,
                    slot_type=slot_type,
                    status=SlotStatus.AVAILABLE,
                    occupied_vehicle_id=None
                ))

            # 2. Khởi tạo danh sách cổng sạc (Charging Ports)
            port_type_keys = list(PORT_TYPES.keys())
            for p_idx in range(1, data["capacity_chargers"] + 1):
                # Phân bổ: 50% 3.3kW, 35% 7.4kW, 15% 11kW
                if p_idx <= int(data["capacity_chargers"] * 0.5):
                    ptype = "STANDARD_3_3KW"
                elif p_idx <= int(data["capacity_chargers"] * 0.85):
                    ptype = "FAST_7_4KW"
                else:
                    ptype = "SUPER_11KW"

                power = PORT_TYPES[ptype]["power_kw"]
                ports.append(ChargingPort(
                    id=f"{hub_id}_PORT_{p_idx:02d}",
                    hub_id=hub_id,
                    port_number=p_idx,
                    port_type=ptype,
                    power_kw=power,
                    status=PortStatus.AVAILABLE,
                    current_vehicle_id=None
                ))

            # 3. Khởi tạo phương tiện công cộng (E-Bike & E-Scooter)
            # E-Bikes
            for b_idx in range(data["initial_ebikes"]):
                v_id = f"EB_{vehicle_counter:03d}"
                soc = 75.0 + (vehicle_counter % 5) * 5.0  # 75% - 95%
                v = Vehicle(
                    id=v_id,
                    plate_number=f"59-EB-{vehicle_counter:04d}",
                    vehicle_type=VehicleType.E_BIKE,
                    model_name="VNU Smart Bike X1",
                    battery_soc=min(100.0, soc),
                    battery_capacity_kwh=1.2,
                    current_hub_id=hub_id,
                    status=VehicleStatus.AVAILABLE
                )
                self.vehicles[v_id] = v
                vehicle_ids.append(v_id)
                # Gán vào slot trống
                for slot in slots:
                    if slot.slot_type == SlotType.SHARED_VEHICLE and slot.is_available():
                        slot.status = SlotStatus.OCCUPIED
                        slot.occupied_vehicle_id = v_id
                        v.current_slot_id = slot.id
                        break
                vehicle_counter += 1

            # E-Scooters
            for s_idx in range(data["initial_escooters"]):
                v_id = f"ES_{vehicle_counter:03d}"
                soc = 65.0 + (vehicle_counter % 7) * 5.0  # 65% - 95%
                v = Vehicle(
                    id=v_id,
                    plate_number=f"59-ES-{vehicle_counter:04d}",
                    vehicle_type=VehicleType.E_SCOOTER,
                    model_name="VinFast Feliz Neo S",
                    battery_soc=min(100.0, soc),
                    battery_capacity_kwh=3.5,
                    current_hub_id=hub_id,
                    status=VehicleStatus.AVAILABLE
                )
                self.vehicles[v_id] = v
                vehicle_ids.append(v_id)
                for slot in slots:
                    if slot.slot_type == SlotType.SHARED_VEHICLE and slot.is_available():
                        slot.status = SlotStatus.OCCUPIED
                        slot.occupied_vehicle_id = v_id
                        v.current_slot_id = slot.id
                        break
                vehicle_counter += 1

            # 4. Giả lập một số vị trí đỗ xe cá nhân đã có sinh viên gửi
            occupied_personal = 0
            for slot in slots:
                if slot.slot_type == SlotType.PERSONAL_VEHICLE and occupied_personal < data["initial_personal_slots_occupied"]:
                    slot.status = SlotStatus.OCCUPIED
                    slot.occupied_vehicle_id = f"PERS_SV_{hub_id}_{occupied_personal+1}"
                    occupied_personal += 1

            # 5. Cắm sạc 2-3 xe đang có mức pin thấp hơn
            charging_assigned = 0
            for v_id in vehicle_ids:
                v = self.vehicles[v_id]
                if v.battery_soc < 70.0 and charging_assigned < min(3, len(ports)):
                    port = ports[charging_assigned]
                    port.status = PortStatus.CHARGING
                    port.current_vehicle_id = v_id
                    v.status = VehicleStatus.CHARGING
                    v.current_port_id = port.id
                    charging_assigned += 1

            # Tạo Hub object
            hub = Hub(
                id=hub_id,
                code=data["code"],
                name=data["name"],
                category=data["category"],
                latitude=data["latitude"],
                longitude=data["longitude"],
                description=data["description"],
                capacity_slots=data["capacity_slots"],
                capacity_chargers=data["capacity_chargers"],
                grid_power_limit_kw=data["grid_power_limit_kw"],
                slots=slots,
                ports=ports,
                vehicle_ids=vehicle_ids
            )
            self.hubs[hub_id] = hub

    def get_all_hubs(self) -> List[Dict[str, Any]]:
        """Lấy danh sách tất cả các Hub kèm chỉ số thời gian thực"""
        result = []
        for hub in self.hubs.values():
            result.append(self.get_hub_detail(hub.id))
        return result

    def get_hub_by_id(self, hub_id: str) -> Optional[Hub]:
        return self.hubs.get(hub_id)

    def get_hub_detail(self, hub_id: str) -> Optional[Dict[str, Any]]:
        hub = self.hubs.get(hub_id)
        if not hub:
            return None

        avail_ebikes = hub.get_available_ebikes_count(self.vehicles)
        avail_escooters = hub.get_available_escooters_count(self.vehicles)
        avail_vehicles = avail_ebikes + avail_escooters
        avail_slots = hub.get_available_slots_count()
        avail_personal_slots = hub.get_available_slots_count(SlotType.PERSONAL_VEHICLE)
        avail_ports = hub.get_available_ports_count()
        power_draw = hub.get_current_power_draw_kw()

        # Kiểm tra cảnh báo
        alerts = []
        if avail_vehicles <= ALERT_THRESHOLDS["vehicle_depletion_min"]:
            alerts.append(f"Nguy cơ cạn kiệt xe (chỉ còn {avail_vehicles} xe)")
        if avail_slots <= ALERT_THRESHOLDS["slot_congestion_free_max"]:
            alerts.append(f"Nguy cơ quá tải chỗ đỗ (chỉ còn {avail_slots} vị trí)")
        if power_draw >= hub.grid_power_limit_kw * 0.9:
            alerts.append(f"Công suất sạc chạm ngưỡng trạm ({power_draw:.1f}/{hub.grid_power_limit_kw} kW)")

        return {
            "id": hub.id,
            "code": hub.code,
            "name": hub.name,
            "category": hub.category,
            "latitude": hub.latitude,
            "longitude": hub.longitude,
            "description": hub.description,
            "capacity_slots": hub.capacity_slots,
            "capacity_chargers": hub.capacity_chargers,
            "grid_power_limit_kw": hub.grid_power_limit_kw,
            "current_power_draw_kw": power_draw,
            "available_vehicles_count": avail_vehicles,
            "available_ebikes_count": avail_ebikes,
            "available_escooters_count": avail_escooters,
            "available_slots_count": avail_slots,
            "available_personal_slots_count": avail_personal_slots,
            "available_ports_count": avail_ports,
            "slot_utilization_percent": hub.get_slot_utilization(),
            "charger_utilization_percent": hub.get_charger_utilization(),
            "alerts": alerts,
            "vehicles": [
                self.vehicles[v_id].to_dict()
                for v_id in hub.vehicle_ids if v_id in self.vehicles
            ],
            "ports": [p.model_dump() for p in hub.ports],
            "slots_summary": {
                "total": len(hub.slots),
                "available": avail_slots,
                "occupied": len(hub.slots) - avail_slots
            }
        }

    def find_nearest_hubs(self, lat: float, lng: float, vehicle_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Tìm Hub gần nhất với tọa độ cho trước và sắp xếp theo khoảng cách"""
        scored = []
        for hub in self.hubs.values():
            dist = haversine_distance(lat, lng, hub.latitude, hub.longitude)
            avail = hub.get_available_vehicles_count(self.vehicles)
            if vehicle_type == "E_BIKE":
                avail = hub.get_available_ebikes_count(self.vehicles)
            elif vehicle_type == "E_SCOOTER":
                avail = hub.get_available_escooters_count(self.vehicles)

            scored.append({
                "hub_id": hub.id,
                "name": hub.name,
                "distance_km": dist,
                "available_vehicles": avail,
                "available_slots": hub.get_available_slots_count(),
                "available_ports": hub.get_available_ports_count()
            })
        return sorted(scored, key=lambda x: x["distance_km"])

    def get_fallback_hub(self, target_hub_id: str, required_resource: str = "vehicle") -> Optional[Dict[str, Any]]:
        """Gợi ý Hub thay thế gần nhất khi Hub mục tiêu bị hết xe hoặc hết chỗ đỗ"""
        target = self.hubs.get(target_hub_id)
        if not target:
            return None

        candidates = []
        for hub_id, hub in self.hubs.items():
            if hub_id == target_hub_id:
                continue
            dist = haversine_distance(target.latitude, target.longitude, hub.latitude, hub.longitude)

            is_eligible = False
            if required_resource == "vehicle" and hub.get_available_vehicles_count(self.vehicles) >= 2:
                is_eligible = True
            elif required_resource == "slot" and hub.get_available_slots_count() >= 3:
                is_eligible = True
            elif required_resource == "port" and hub.get_available_ports_count() >= 1:
                is_eligible = True

            if is_eligible:
                candidates.append((dist, hub))

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[0])
        best_dist, best_hub = candidates[0]
        return {
            "fallback_hub_id": best_hub.id,
            "fallback_hub_name": best_hub.name,
            "distance_km": best_dist,
            "available_vehicles": best_hub.get_available_vehicles_count(self.vehicles),
            "available_slots": best_hub.get_available_slots_count(),
            "available_ports": best_hub.get_available_ports_count(),
            "message": f"Hub {target.name} đang quá tải. Đề xuất di chuyển sang {best_hub.name} (cách {best_dist} km)."
        }

    def get_network_overview(self) -> Dict[str, Any]:
        """Tổng hợp toàn bộ chỉ số mạng lưới E-Mobility ĐHQG-HCM"""
        total_vehicles = len(self.vehicles)
        available_vehicles = sum(1 for v in self.vehicles.values() if v.status == VehicleStatus.AVAILABLE)
        in_use_vehicles = sum(1 for v in self.vehicles.values() if v.status == VehicleStatus.IN_USE)
        charging_vehicles = sum(1 for v in self.vehicles.values() if v.status == VehicleStatus.CHARGING)
        faulty_vehicles = sum(1 for v in self.vehicles.values() if v.status in [VehicleStatus.FAULTY, VehicleStatus.MAINTENANCE])

        total_ports = sum(len(h.ports) for h in self.hubs.values())
        available_ports = sum(h.get_available_ports_count() for h in self.hubs.values())
        charging_ports = sum(sum(1 for p in h.ports if p.status == PortStatus.CHARGING) for h in self.hubs.values())
        faulty_ports = sum(sum(1 for p in h.ports if p.status == PortStatus.FAULTY) for h in self.hubs.values())

        total_slots = sum(len(h.slots) for h in self.hubs.values())
        available_slots = sum(h.get_available_slots_count() for h in self.hubs.values())

        total_power_kw = sum(h.get_current_power_draw_kw() for h in self.hubs.values())

        # Tổng hợp cảnh báo mạng lưới
        active_alerts = []
        for h in self.hubs.values():
            detail = self.get_hub_detail(h.id)
            if detail and detail["alerts"]:
                for a in detail["alerts"]:
                    active_alerts.append(f"[{h.name}] {a}")

        return {
            "total_hubs": len(self.hubs),
            "vehicles": {
                "total": total_vehicles,
                "available": available_vehicles,
                "in_use": in_use_vehicles,
                "charging": charging_vehicles,
                "faulty_or_maintenance": faulty_vehicles
            },
            "ports": {
                "total": total_ports,
                "available": available_ports,
                "charging": charging_ports,
                "faulty": faulty_ports
            },
            "slots": {
                "total": total_slots,
                "available": available_slots,
                "occupied": total_slots - available_slots
            },
            "grid": {
                "total_current_power_kw": round(total_power_kw, 2),
                "grid_load_ratio": round((total_power_kw / (sum(h.grid_power_limit_kw for h in self.hubs.values()))) * 100, 1)
            },
            "alerts": active_alerts
        }
