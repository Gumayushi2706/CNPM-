"""
Dịch vụ Điều phối Cân bằng Phương tiện giữa các Hub (Vehicle Rebalancing & Dispatcher)
"""

import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from ..models.hub import SlotStatus, SlotType
from ..models.vehicle import VehicleStatus
from .hub_service import HubService, haversine_distance


class RebalanceService:
    def __init__(self, hub_service: HubService):
        self.hub_service = hub_service
        self.transfer_history: List[Dict[str, Any]] = []

    def analyze_network_balance(self, target_fill_ratio: float = 0.40) -> Dict[str, Any]:
        """
        Phân tích tình trạng chênh lệch xe giữa các Hub:
        - Xác định các Hub thâm hụt (Deficit) có nguy cơ cạn kiệt
        - Xác định các Hub dư thừa (Surplus) có nhiều xe tồn đọng
        """
        surplus_hubs = []
        deficit_hubs = []
        balanced_hubs = []

        for hub_id, hub in self.hub_service.hubs.items():
            avail = hub.get_available_vehicles_count(self.hub_service.vehicles)
            target = max(4, int(hub.capacity_slots * target_fill_ratio))
            delta = avail - target

            hub_info = {
                "hub_id": hub.id,
                "hub_name": hub.name,
                "current_available": avail,
                "target_level": target,
                "delta": delta,
                "latitude": hub.latitude,
                "longitude": hub.longitude
            }

            if delta >= 3:
                surplus_hubs.append(hub_info)
            elif delta <= -3:
                deficit_hubs.append(hub_info)
            else:
                balanced_hubs.append(hub_info)

        # Sắp xếp thâm hụt nhiều nhất lên đầu
        deficit_hubs.sort(key=lambda x: x["delta"])
        # Sắp xếp dư thừa nhiều nhất lên đầu
        surplus_hubs.sort(key=lambda x: x["delta"], reverse=True)

        return {
            "surplus_hubs": surplus_hubs,
            "deficit_hubs": deficit_hubs,
            "balanced_hubs": balanced_hubs,
            "is_rebalance_needed": len(deficit_hubs) > 0 and len(surplus_hubs) > 0
        }

    def generate_rebalance_plan(self) -> List[Dict[str, Any]]:
        """
        Thuật toán sinh kế hoạch điều phối xe tối ưu:
        Ghép cặp Hub dư thừa với Hub thiếu hụt gần nhất để giảm thiểu quãng đường điều xe.
        """
        analysis = self.analyze_network_balance()
        surplus = [dict(h) for h in analysis["surplus_hubs"]]
        deficit = [dict(h) for h in analysis["deficit_hubs"]]

        planned_transfers = []

        for def_hub in deficit:
            needed = abs(def_hub["delta"])
            if needed <= 0:
                continue

            # Tìm Hub thừa có khoảng cách ngắn nhất đến Hub thiếu này
            eligible_surplus = [s for s in surplus if s["delta"] > 0]
            if not eligible_surplus:
                break

            eligible_surplus.sort(
                key=lambda s: haversine_distance(def_hub["latitude"], def_hub["longitude"], s["latitude"], s["longitude"])
            )

            for sur_hub in eligible_surplus:
                if needed <= 0 or sur_hub["delta"] <= 0:
                    continue

                transfer_qty = min(needed, sur_hub["delta"])
                dist = haversine_distance(def_hub["latitude"], def_hub["longitude"], sur_hub["latitude"], sur_hub["longitude"])

                transfer_order = {
                    "from_hub_id": sur_hub["hub_id"],
                    "from_hub_name": sur_hub["hub_name"],
                    "to_hub_id": def_hub["hub_id"],
                    "to_hub_name": def_hub["hub_name"],
                    "quantity": transfer_qty,
                    "distance_km": dist,
                    "estimated_minutes": round(dist * 6.0, 1),  # ~10km/h tốc độ xe tải điều chuyển
                    "reason": f"Cân bằng tải: Chuyển {transfer_qty} xe từ {sur_hub['hub_name']} sang {def_hub['hub_name']}"
                }
                planned_transfers.append(transfer_order)

                sur_hub["delta"] -= transfer_qty
                needed -= transfer_qty

        return planned_transfers

    def execute_rebalance_transfer(
        self,
        from_hub_id: str,
        to_hub_id: str,
        quantity: int
    ) -> Dict[str, Any]:
        """
        Thực thi lệnh điều phối xe vật lý từ Hub xuất phát sang Hub đích:
        - Rút xe rảnh từ from_hub
        - Giải phóng slot tại from_hub
        - Chuyển sang to_hub và gán slot trống tại to_hub
        """
        from_hub = self.hub_service.get_hub_by_id(from_hub_id)
        to_hub = self.hub_service.get_hub_by_id(to_hub_id)

        if not from_hub or not to_hub:
            return {"success": False, "message": "Hub không tồn tại"}

        # Chọn xe có pin tốt và trạng thái AVAILABLE
        eligible_vehicles = [
            self.hub_service.vehicles[v_id]
            for v_id in from_hub.vehicle_ids
            if v_id in self.hub_service.vehicles
            and self.hub_service.vehicles[v_id].status == VehicleStatus.AVAILABLE
        ]

        if len(eligible_vehicles) < quantity:
            quantity = len(eligible_vehicles)

        if quantity == 0:
            return {"success": False, "message": f"Không có đủ xe khả dụng tại {from_hub.name} để điều phối"}

        # Kiểm tra slot trống tại to_hub
        avail_to_slots = [s for s in to_hub.slots if s.slot_type == SlotType.SHARED_VEHICLE and s.is_available()]
        if len(avail_to_slots) < quantity:
            quantity = len(avail_to_slots)

        if quantity == 0:
            return {"success": False, "message": f"Hub {to_hub.name} không còn đủ chỗ đỗ trống để tiếp nhận"}

        moved_vehicles = eligible_vehicles[:quantity]
        for idx, vehicle in enumerate(moved_vehicles):
            # Rút khỏi from_hub
            from_hub.vehicle_ids.remove(vehicle.id)
            if vehicle.current_slot_id:
                for s in from_hub.slots:
                    if s.id == vehicle.current_slot_id:
                        s.status = SlotStatus.AVAILABLE
                        s.occupied_vehicle_id = None
                        break

            # Đưa vào to_hub
            target_slot = avail_to_slots[idx]
            target_slot.status = SlotStatus.OCCUPIED
            target_slot.occupied_vehicle_id = vehicle.id

            to_hub.vehicle_ids.append(vehicle.id)
            vehicle.current_hub_id = to_hub.id
            vehicle.current_slot_id = target_slot.id

        dist = haversine_distance(from_hub.latitude, from_hub.longitude, to_hub.latitude, to_hub.longitude)
        record = {
            "transfer_id": f"DISP_{uuid.uuid4().hex[:8].upper()}",
            "from_hub_id": from_hub_id,
            "from_hub_name": from_hub.name,
            "to_hub_id": to_hub_id,
            "to_hub_name": to_hub.name,
            "quantity": quantity,
            "vehicle_ids": [v.id for v in moved_vehicles],
            "distance_km": dist,
            "executed_at": datetime.now().isoformat(),
            "status": "COMPLETED"
        }
        self.transfer_history.append(record)

        return {
            "success": True,
            "message": f"Đã điều chuyển thành công {quantity} xe từ {from_hub.name} sang {to_hub.name}!",
            "record": record
        }

    def execute_all_recommended_plans(self) -> Dict[str, Any]:
        """Tự động thực thi toàn bộ các kế hoạch điều phối được hệ thống gợi ý"""
        plans = self.generate_rebalance_plan()
        results = []
        total_moved = 0

        for plan in plans:
            res = self.execute_rebalance_transfer(
                from_hub_id=plan["from_hub_id"],
                to_hub_id=plan["to_hub_id"],
                quantity=plan["quantity"]
            )
            if res.get("success"):
                results.append(res["record"])
                total_moved += plan["quantity"]

        return {
            "executed_transfers_count": len(results),
            "total_vehicles_moved": total_moved,
            "records": results
        }
