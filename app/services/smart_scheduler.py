"""
Thuật toán Lập lịch sạc thông minh đa tiêu chí (Smart Charging Scheduler)
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from ..config import FEES, PORT_TYPES
from ..models.booking import ChargingSession
from ..models.hub import PortStatus
from ..models.vehicle import Vehicle, VehicleStatus, VehicleType
from .hub_service import HubService


class SmartChargingScheduler:
    def __init__(self, hub_service: HubService):
        self.hub_service = hub_service
        self.active_sessions: Dict[str, ChargingSession] = {}
        # Hàng đợi yêu cầu sạc cho từng Hub: {hub_id: [dict(request_info)]}
        self.charging_queues: Dict[str, List[Dict[str, Any]]] = {}

    def calculate_priority_score(
        self,
        current_soc: float,
        minutes_until_needed: float = 120.0,
        is_shared_fleet: bool = True
    ) -> float:
        """
        Tính điểm ưu tiên sạc đa tiêu chí:
        1. Mức pin thấp: Càng cạn pin điểm càng cao (0 - 45 điểm)
        2. Thời gian cần dùng xe: Càng gần giờ đi học/chuyến đi kế tiếp điểm càng cao (0 - 35 điểm)
        3. Loại xe: Xe dùng chung phục vụ sinh viên ưu tiên hơn xe cá nhân lưu trú (0 - 20 điểm)
        """
        soc_score = max(0.0, (100.0 - current_soc)) * 0.45

        # Thời gian đến chuyến đi kế tiếp (càng ít phút càng khẩn cấp)
        urgency_score = min(35.0, (120.0 / (max(5.0, minutes_until_needed))) * 5.0)

        # Ưu tiên đội xe dùng chung phục vụ cộng đồng ĐHQG
        fleet_score = 20.0 if is_shared_fleet else 10.0

        total_score = round(soc_score + urgency_score + fleet_score, 2)
        return total_score

    def enqueue_charging_request(
        self,
        hub_id: str,
        vehicle_id: str,
        user_id: str,
        target_soc: float = 100.0,
        minutes_until_needed: float = 120.0,
        is_personal: bool = False
    ) -> Dict[str, Any]:
        """Đăng ký nhu cầu sạc vào hàng đợi thông minh tại Hub"""
        hub = self.hub_service.get_hub_by_id(hub_id)
        if not hub:
            return {"success": False, "message": f"Không tìm thấy Hub: {hub_id}"}

        vehicle = self.hub_service.vehicles.get(vehicle_id)
        if not vehicle:
            # Tạo tạm đối tượng cho xe cá nhân nếu chưa có trong bộ nhớ
            vehicle = Vehicle(
                id=vehicle_id,
                plate_number=f"PERS-{vehicle_id[-4:]}",
                vehicle_type=VehicleType.PERSONAL_EV,
                model_name="Personal E-Scooter",
                battery_soc=30.0,
                current_hub_id=hub_id,
                status=VehicleStatus.WAITING_CHARGE,
                owner_id=user_id
            )
            self.hub_service.vehicles[vehicle_id] = vehicle

        priority = self.calculate_priority_score(
            current_soc=vehicle.battery_soc,
            minutes_until_needed=minutes_until_needed,
            is_shared_fleet=(not is_personal)
        )

        req = {
            "queue_id": f"REQ_{uuid.uuid4().hex[:6].upper()}",
            "hub_id": hub_id,
            "vehicle_id": vehicle.id,
            "user_id": user_id,
            "current_soc": vehicle.battery_soc,
            "target_soc": target_soc,
            "minutes_until_needed": minutes_until_needed,
            "priority_score": priority,
            "is_personal": is_personal,
            "enqueued_at": datetime.now().isoformat()
        }

        if hub_id not in self.charging_queues:
            self.charging_queues[hub_id] = []

        self.charging_queues[hub_id].append(req)
        # Sắp xếp hàng đợi theo độ ưu tiên giảm dần
        self.charging_queues[hub_id].sort(key=lambda x: x["priority_score"], reverse=True)

        vehicle.status = VehicleStatus.WAITING_CHARGE

        # Thử phân bổ cổng sạc ngay
        self.dispatch_smart_charging(hub_id)

        return {
            "success": True,
            "message": f"Đã đăng ký lịch sạc thông minh cho xe {vehicle.plate_number} (Điểm ưu tiên: {priority})",
            "request": req,
            "queue_position": next((i + 1 for i, r in enumerate(self.charging_queues[hub_id]) if r["queue_id"] == req["queue_id"]), 1)
        }

    def dispatch_smart_charging(self, hub_id: str) -> List[Dict[str, Any]]:
        """
        Thuật toán phân bổ công suất và ghép xe vào cổng sạc:
        - Đảm bảo tổng công suất không vượt quá grid_power_limit_kw
        - Ưu tiên phương tiện có priority_score cao nhất
        """
        hub = self.hub_service.get_hub_by_id(hub_id)
        if not hub or hub_id not in self.charging_queues or not self.charging_queues[hub_id]:
            return []

        dispatched = []
        queue = self.charging_queues[hub_id]
        current_power = hub.get_current_power_draw_kw()
        available_ports = [p for p in hub.ports if p.is_available()]

        # Sắp xếp cổng sạc: ưu tiên sạc nhanh cho xe ưu tiên cao
        available_ports.sort(key=lambda p: p.power_kw, reverse=True)

        i = 0
        while i < len(queue) and available_ports:
            req = queue[i]
            vehicle = self.hub_service.vehicles.get(req["vehicle_id"])
            if not vehicle:
                queue.pop(i)
                continue

            # Tìm cổng sạc thích hợp không làm vượt công suất trạm
            assigned_port = None
            for port in available_ports:
                if current_power + port.power_kw <= hub.grid_power_limit_kw:
                    assigned_port = port
                    break

            if assigned_port:
                # Gán xe vào cổng sạc
                assigned_port.status = PortStatus.CHARGING
                assigned_port.current_vehicle_id = vehicle.id
                available_ports.remove(assigned_port)
                current_power += assigned_port.power_kw

                vehicle.status = VehicleStatus.CHARGING
                vehicle.current_port_id = assigned_port.id

                # Tạo ChargingSession
                session_id = f"CHG_{uuid.uuid4().hex[:8].upper()}"
                session = ChargingSession(
                    id=session_id,
                    hub_id=hub_id,
                    port_id=assigned_port.id,
                    vehicle_id=vehicle.id,
                    user_id=req["user_id"],
                    start_soc=vehicle.battery_soc,
                    target_soc=req["target_soc"],
                    current_soc=vehicle.battery_soc,
                    power_kw=assigned_port.power_kw,
                    priority_score=req["priority_score"],
                    status="CHARGING"
                )
                self.active_sessions[session_id] = session
                assigned_port.active_session_id = session_id

                dispatched.append({
                    "vehicle_id": vehicle.id,
                    "port_id": assigned_port.id,
                    "power_kw": assigned_port.power_kw,
                    "priority_score": req["priority_score"]
                })
                queue.pop(i)
            else:
                # Không đủ công suất điện cho xe này trong đợt này
                i += 1

        return dispatched

    def progress_charging_step(self, minutes: float = 15.0) -> Dict[str, Any]:
        """
        Mô phỏng bước tiến trình sạc theo thời gian:
        - Tăng pin theo công suất cổng sạc
        - Khi pin đạt mục tiêu -> giải phóng cổng sạc và tự động cấp cho xe kế tiếp
        """
        completed_sessions = []
        hours = minutes / 60.0

        for session_id, session in list(self.active_sessions.items()):
            if session.status != "CHARGING":
                continue

            vehicle = self.hub_service.vehicles.get(session.vehicle_id)
            port = None
            hub = self.hub_service.get_hub_by_id(session.hub_id)
            if hub:
                for p in hub.ports:
                    if p.id == session.port_id:
                        port = p
                        break

            if not vehicle or not port or not hub:
                continue

            # Năng lượng nạp (kWh) = Công suất (kW) * Thời gian (giờ) * Hiệu suất sạc (0.9)
            energy_kwh = session.power_kw * hours * 0.9
            soc_gain = (energy_kwh / max(1.0, vehicle.battery_capacity_kwh)) * 100.0

            vehicle.battery_soc = min(session.target_soc, round(vehicle.battery_soc + soc_gain, 1))
            session.current_soc = vehicle.battery_soc
            session.energy_consumed_kwh = round(session.energy_consumed_kwh + energy_kwh, 2)
            port.total_kwh_delivered = round(port.total_kwh_delivered + energy_kwh, 2)

            # Kiểm tra sạc đầy
            if vehicle.battery_soc >= session.target_soc:
                session.status = "COMPLETED"
                session.actual_end_time = datetime.now().isoformat()
                session.total_fee = round(session.energy_consumed_kwh * FEES["charging_per_kwh"], 0)

                # Giải phóng cổng sạc
                port.status = PortStatus.AVAILABLE
                port.current_vehicle_id = None
                port.active_session_id = None

                vehicle.status = VehicleStatus.AVAILABLE
                vehicle.current_port_id = None

                completed_sessions.append(session.model_dump())
                del self.active_sessions[session_id]

                # Tự động nạp xe tiếp theo từ hàng đợi
                self.dispatch_smart_charging(hub.id)

        return {
            "completed_count": len(completed_sessions),
            "completed_sessions": completed_sessions,
            "active_charging_count": len(self.active_sessions)
        }

    def get_scheduler_status(self) -> Dict[str, Any]:
        """Thống kê tổng thể về hàng đợi và tiến trình sạc tại các Hub"""
        hub_queues_summary = {}
        for hub_id, q in self.charging_queues.items():
            hub_queues_summary[hub_id] = [
                {
                    "queue_id": r["queue_id"],
                    "vehicle_id": r["vehicle_id"],
                    "current_soc": r["current_soc"],
                    "priority_score": r["priority_score"],
                    "is_personal": r["is_personal"]
                }
                for r in q
            ]

        return {
            "active_charging_count": len(self.active_sessions),
            "active_sessions": [s.model_dump() for s in self.active_sessions.values()],
            "queues_by_hub": hub_queues_summary,
            "total_vehicles_waiting": sum(len(q) for q in self.charging_queues.values())
        }
