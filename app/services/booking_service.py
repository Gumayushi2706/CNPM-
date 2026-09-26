"""
Dịch vụ Quản lý Đặt xe, Chuyến đi và Thuê bãi (Booking Service)
"""

import uuid
from datetime import datetime
from typing import Dict, Optional, Any, List
from ..config import FEES
from ..models.booking import Booking, BookingType, BookingStatus, Trip
from ..models.hub import SlotStatus, SlotType
from ..models.vehicle import VehicleStatus, VehicleType
from .hub_service import HubService, haversine_distance


class BookingService:
    def __init__(self, hub_service: HubService):
        self.hub_service = hub_service
        self.bookings: Dict[str, Booking] = {}
        self.trips: Dict[str, Trip] = {}

    def rent_vehicle(
        self,
        user_id: str,
        user_name: str,
        origin_hub_id: str,
        vehicle_type: str = "E_BIKE",
        destination_hub_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Sinh viên đặt xe công cộng tại Hub xuất phát"""
        hub = self.hub_service.get_hub_by_id(origin_hub_id)
        if not hub:
            return {"success": False, "message": f"Không tìm thấy Hub: {origin_hub_id}"}

        # Tìm xe phù hợp có mức pin cao nhất và trạng thái AVAILABLE
        target_vtype = VehicleType(vehicle_type)
        candidate_vehicles = [
            self.hub_service.vehicles[v_id]
            for v_id in hub.vehicle_ids
            if v_id in self.hub_service.vehicles
            and self.hub_service.vehicles[v_id].status == VehicleStatus.AVAILABLE
            and self.hub_service.vehicles[v_id].vehicle_type == target_vtype
            and self.hub_service.vehicles[v_id].battery_soc >= 20.0
        ]

        if not candidate_vehicles:
            # Gợi ý Hub thay thế gần nhất
            fallback = self.hub_service.get_fallback_hub(origin_hub_id, required_resource="vehicle")
            return {
                "success": False,
                "message": f"Hub {hub.name} hiện hết loại xe {vehicle_type} khả dụng.",
                "fallback_suggestion": fallback
            }

        # Chọn xe có mức pin tốt nhất
        best_vehicle = max(candidate_vehicles, key=lambda v: v.battery_soc)

        # Kiểm tra Hub đích (nếu có chỉ định trước) xem còn chỗ đỗ không
        if destination_hub_id:
            dest_hub = self.hub_service.get_hub_by_id(destination_hub_id)
            if dest_hub and dest_hub.get_available_slots_count(SlotType.SHARED_VEHICLE) == 0:
                fallback_dest = self.hub_service.get_fallback_hub(destination_hub_id, required_resource="slot")
                # Vẫn cho đặt nhưng cảnh báo trước
                warning = f"Lưu ý: Hub đích {dest_hub.name} đang đầy chỗ đỗ! Đề xuất trả tại {fallback_dest['fallback_hub_name'] if fallback_dest else 'Hub lân cận'}."
            else:
                warning = None
        else:
            warning = None

        booking_id = f"BK_{uuid.uuid4().hex[:8].upper()}"
        booking = Booking(
            id=booking_id,
            user_id=user_id,
            user_name=user_name,
            booking_type=BookingType.VEHICLE_RENTAL,
            hub_id=origin_hub_id,
            destination_hub_id=destination_hub_id,
            vehicle_id=best_vehicle.id,
            status=BookingStatus.ACTIVE,
            start_time=datetime.now().isoformat(),
            note="Sinh viên đã nhận xe và bắt đầu di chuyển"
        )
        self.bookings[booking_id] = booking

        # Cập nhật trạng thái xe: rời khỏi Hub
        best_vehicle.status = VehicleStatus.IN_USE
        if best_vehicle.id in hub.vehicle_ids:
            hub.vehicle_ids.remove(best_vehicle.id)

        # Giải phóng vị trí đỗ tại Hub xuất phát
        if best_vehicle.current_slot_id:
            for s in hub.slots:
                if s.id == best_vehicle.current_slot_id:
                    s.status = SlotStatus.AVAILABLE
                    s.occupied_vehicle_id = None
                    break
            best_vehicle.current_slot_id = None

        best_vehicle.current_hub_id = None

        # Tạo bản ghi chuyến đi (Trip)
        trip_id = f"TRIP_{uuid.uuid4().hex[:8].upper()}"
        trip = Trip(
            id=trip_id,
            booking_id=booking_id,
            user_id=user_id,
            vehicle_id=best_vehicle.id,
            origin_hub_id=origin_hub_id,
            destination_hub_id=destination_hub_id,
            start_time=datetime.now().isoformat(),
            start_soc=best_vehicle.battery_soc,
            status="IN_PROGRESS"
        )
        self.trips[trip_id] = trip

        return {
            "success": True,
            "message": f"Mở khóa thành công xe {best_vehicle.plate_number} ({best_vehicle.model_name})!",
            "booking": booking.model_dump(),
            "trip": trip.model_dump(),
            "vehicle": best_vehicle.to_dict(),
            "warning": warning
        }

    def return_vehicle(
        self,
        trip_id: str,
        destination_hub_id: str,
        simulated_duration_minutes: float = 15.0
    ) -> Dict[str, Any]:
        """Sinh viên hoàn tất chuyến đi và trả xe tại Hub đích"""
        trip = self.trips.get(trip_id)
        if not trip:
            return {"success": False, "message": f"Không tìm thấy chuyến đi: {trip_id}"}
        if trip.status == "COMPLETED":
            return {"success": False, "message": "Chuyến đi này đã được hoàn tất trước đó."}

        dest_hub = self.hub_service.get_hub_by_id(destination_hub_id)
        if not dest_hub:
            return {"success": False, "message": f"Không tìm thấy Hub đích: {destination_hub_id}"}

        # Tìm slot đỗ xe công cộng còn trống
        avail_slot = None
        for s in dest_hub.slots:
            if s.slot_type == SlotType.SHARED_VEHICLE and s.is_available():
                avail_slot = s
                break

        if not avail_slot:
            # Bãi xe đầy -> Đề xuất Hub fallback ngay lập tức
            fallback = self.hub_service.get_fallback_hub(destination_hub_id, required_resource="slot")
            return {
                "success": False,
                "message": f"Hub {dest_hub.name} đã đầy chỗ đỗ xe công cộng!",
                "fallback_hub": fallback
            }

        vehicle = self.hub_service.vehicles.get(trip.vehicle_id)
        if not vehicle:
            return {"success": False, "message": "Phương tiện không tồn tại trong hệ thống."}

        origin_hub = self.hub_service.get_hub_by_id(trip.origin_hub_id)
        distance = 0.0
        if origin_hub:
            distance = haversine_distance(origin_hub.latitude, origin_hub.longitude, dest_hub.latitude, dest_hub.longitude)
            if distance == 0.0:
                distance = 1.2  # Di chuyển nội bộ quanh Hub

        # Tiêu hao pin ước tính: ~2% pin / 1 km (xe đạp), ~3% pin / 1 km (xe máy)
        consumption_rate = 2.0 if vehicle.vehicle_type == VehicleType.E_BIKE else 3.0
        battery_consumed = round(distance * consumption_rate, 1)
        end_soc = max(5.0, round(trip.start_soc - battery_consumed, 1))

        # Tính cước phí sinh viên
        if vehicle.vehicle_type == VehicleType.E_BIKE:
            fare = FEES["e_bike_unlock"] + (simulated_duration_minutes * FEES["e_bike_per_minute"])
        else:
            fare = FEES["e_scooter_unlock"] + (simulated_duration_minutes * FEES["e_scooter_per_minute"])

        # Cập nhật Trip
        trip.end_time = datetime.now().isoformat()
        trip.duration_minutes = simulated_duration_minutes
        trip.distance_km = distance
        trip.destination_hub_id = destination_hub_id
        trip.end_soc = end_soc
        trip.fare = round(fare, 0)
        trip.status = "COMPLETED"

        # Cập nhật Booking
        booking = self.bookings.get(trip.booking_id)
        if booking:
            booking.status = BookingStatus.COMPLETED
            booking.end_time = trip.end_time
            booking.actual_cost = trip.fare

        # Đỗ xe vào Hub mới
        avail_slot.status = SlotStatus.OCCUPIED
        avail_slot.occupied_vehicle_id = vehicle.id

        dest_hub.vehicle_ids.append(vehicle.id)
        vehicle.current_hub_id = destination_hub_id
        vehicle.current_slot_id = avail_slot.id
        vehicle.battery_soc = end_soc
        vehicle.total_km = round(vehicle.total_km + distance, 1)
        vehicle.total_trips += 1

        # Nếu pin thấp (< 25%), tự động đánh dấu xe cần sạc
        if vehicle.battery_soc < 25.0:
            vehicle.status = VehicleStatus.WAITING_CHARGE
            need_charge_msg = " [Lưu ý: Mức pin thấp, xe tự động chuyển vào hàng đợi sạc thông minh]"
        else:
            vehicle.status = VehicleStatus.AVAILABLE
            need_charge_msg = ""

        return {
            "success": True,
            "message": f"Trả xe thành công tại {dest_hub.name}! Phí hành trình: {trip.fare:,.0f} VNĐ.{need_charge_msg}",
            "trip": trip.model_dump(),
            "vehicle": vehicle.to_dict()
        }

    def reserve_personal_parking(
        self,
        user_id: str,
        user_name: str,
        hub_id: str,
        vehicle_plate: str,
        estimated_hours: float = 4.0
    ) -> Dict[str, Any]:
        """Sinh viên đặt trước vị trí đỗ xe điện cá nhân tại Hub"""
        hub = self.hub_service.get_hub_by_id(hub_id)
        if not hub:
            return {"success": False, "message": f"Không tìm thấy Hub: {hub_id}"}

        # Tìm slot cá nhân còn trống
        target_slot = None
        for s in hub.slots:
            if s.slot_type == SlotType.PERSONAL_VEHICLE and s.is_available():
                target_slot = s
                break

        if not target_slot:
            fallback = self.hub_service.get_fallback_hub(hub_id, required_resource="slot")
            return {
                "success": False,
                "message": f"Hub {hub.name} đã hết vị trí đỗ xe cá nhân!",
                "fallback_suggestion": fallback
            }

        target_slot.status = SlotStatus.RESERVED
        target_slot.occupied_vehicle_id = f"PERS_{vehicle_plate}"

        booking_id = f"BK_PARK_{uuid.uuid4().hex[:8].upper()}"
        estimated_cost = estimated_hours * FEES["parking_per_hour"]

        booking = Booking(
            id=booking_id,
            user_id=user_id,
            user_name=user_name,
            booking_type=BookingType.PARKING_RESERVATION,
            hub_id=hub_id,
            slot_id=target_slot.id,
            status=BookingStatus.CONFIRMED,
            estimated_cost=estimated_cost,
            note=f"Xe cá nhân BKS {vehicle_plate} - Đặt giữ chỗ {estimated_hours} giờ"
        )
        self.bookings[booking_id] = booking

        return {
            "success": True,
            "message": f"Đã đặt thành công vị trí đỗ {target_slot.slot_number} tại {hub.name}!",
            "booking": booking.model_dump(),
            "slot": target_slot.model_dump()
        }

    def get_user_bookings(self, user_id: str) -> List[Dict[str, Any]]:
        return [b.model_dump() for b in self.bookings.values() if b.user_id == user_id]

    def get_all_trips(self) -> List[Dict[str, Any]]:
        return [t.model_dump() for t in self.trips.values()]
