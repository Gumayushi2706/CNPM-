"""
Bộ máy Mô phỏng và Phân tích Kịch bản (What-if Simulation Engine)
"""

import copy
import random
from typing import Dict, List, Any
from ..models.simulation import (
    ScenarioType,
    SimulationConfig,
    SimulationStepResult,
    SimulationSummary
)
from .hub_service import HubService
from .booking_service import BookingService
from .smart_scheduler import SmartChargingScheduler
from .rebalance_service import RebalanceService
from .incident_service import IncidentService


class SimulationEngine:
    def __init__(
        self,
        hub_service: HubService,
        booking_service: BookingService,
        scheduler: SmartChargingScheduler,
        rebalance_service: RebalanceService,
        incident_service: IncidentService
    ):
        self.hub_service = hub_service
        self.booking_service = booking_service
        self.scheduler = scheduler
        self.rebalance_service = rebalance_service
        self.incident_service = incident_service

    def run_scenario(self, config: SimulationConfig) -> SimulationSummary:
        """
        Chạy mô phỏng kịch bản What-if hoàn chỉnh:
        - Mô phỏng từng bước thời gian (mỗi tick = 15 phút)
        - Đo lường mức độ biến động tài nguyên và hiệu quả của các giải pháp điều phối
        """
        # Lưu trạng thái dự phòng để không làm ảnh hưởng môi trường thật nếu cần
        steps: List[SimulationStepResult] = []
        total_requests = 0
        total_fulfilled = 0
        total_unmet = 0
        total_rebalanced_vehicles = 0
        peak_grid_load = 0.0
        alerts_accumulated: List[str] = []
        recommendations: List[str] = []

        # Áp dụng cấu hình ban đầu theo loại kịch bản
        self._setup_scenario_initial_conditions(config)

        start_hour = 7  # Bắt đầu lúc 7:00 sáng
        for tick in range(1, config.duration_ticks + 1):
            current_minute = (tick - 1) * 15
            h = start_hour + current_minute // 60
            m = current_minute % 60
            time_label = f"{h:02d}:{m:02d}"

            # 1. Sinh lưu lượng yêu cầu sinh viên theo kịch bản
            step_reqs, step_fulfilled, step_unmet, step_alerts = self._simulate_tick_demand(tick, config)
            total_requests += step_reqs
            total_fulfilled += step_fulfilled
            total_unmet += step_unmet
            alerts_accumulated.extend(step_alerts)

            # 2. Cập nhật tiến trình sạc thông minh
            self.scheduler.progress_charging_step(minutes=15.0)

            # 3. Tự động điều phối cân bằng xe (nếu bật auto_rebalance)
            rebalance_actions = []
            if config.auto_rebalance and (tick % 2 == 0 or step_unmet > 0):
                plans = self.rebalance_service.generate_rebalance_plan()
                for p in plans[:2]:  # Thực thi tối đa 2 đợt điều chuyển khẩn cấp mỗi tick
                    res = self.rebalance_service.execute_rebalance_transfer(
                        from_hub_id=p["from_hub_id"],
                        to_hub_id=p["to_hub_id"],
                        quantity=min(p["quantity"], 6)
                    )
                    if res.get("success"):
                        rebalance_actions.append(res["record"])
                        total_rebalanced_vehicles += res["record"]["quantity"]

            # 4. Thu thập chỉ số trạng thái tại tick này
            current_grid_load = sum(h.get_current_power_draw_kw() for h in self.hub_service.hubs.values())
            peak_grid_load = max(peak_grid_load, current_grid_load)

            hub_states = {}
            for hid, hub in self.hub_service.hubs.items():
                hub_states[hid] = {
                    "name": hub.name,
                    "available_vehicles": hub.get_available_vehicles_count(self.hub_service.vehicles),
                    "available_slots": hub.get_available_slots_count(),
                    "available_ports": hub.get_available_ports_count(),
                    "power_draw_kw": hub.get_current_power_draw_kw()
                }

            step_res = SimulationStepResult(
                tick=tick,
                time_label=time_label,
                requests_generated=step_reqs,
                requests_fulfilled=step_fulfilled,
                requests_unmet=step_unmet,
                active_trips=len([t for t in self.booking_service.trips.values() if t.status == "IN_PROGRESS"]),
                active_charging_sessions=len(self.scheduler.active_sessions),
                grid_total_power_kw=round(current_grid_load, 1),
                hub_states=hub_states,
                rebalance_actions=rebalance_actions,
                alerts=step_alerts
            )
            steps.append(step_res)

        # 5. Tổng kết và đưa ra giải pháp khuyến nghị
        service_level = round((total_fulfilled / max(1, total_requests)) * 100.0, 1)
        avg_wait = round((total_unmet / max(1, total_requests)) * 18.0, 1)

        recommendations = self._generate_scenario_recommendations(
            config.scenario_type,
            service_level,
            total_unmet,
            total_rebalanced_vehicles
        )

        return SimulationSummary(
            scenario_type=config.scenario_type.value,
            scenario_name=config.scenario_name,
            total_duration_minutes=config.duration_ticks * 15,
            total_student_requests=total_requests,
            fulfilled_requests=total_fulfilled,
            unmet_requests=total_unmet,
            service_level_percent=service_level,
            average_wait_time_minutes=avg_wait,
            total_rebalanced_vehicles=total_rebalanced_vehicles,
            total_energy_delivered_kwh=round(sum(p.total_kwh_delivered for h in self.hub_service.hubs.values() for p in h.ports), 1),
            peak_grid_load_kw=round(peak_grid_load, 1),
            recommendations=recommendations,
            steps=steps
        )

    def _setup_scenario_initial_conditions(self, config: SimulationConfig):
        """Khởi tạo các điều kiện đặc thù cho từng kịch bản"""
        if config.scenario_type == ScenarioType.PORT_BREAKDOWN:
            # Mô phỏng hỏng một số cổng sạc tại Hub đích
            target_hub = self.hub_service.get_hub_by_id(config.target_hub_id or "HUB_METRO")
            if target_hub:
                for idx in range(min(config.faulty_ports_count, len(target_hub.ports))):
                    port = target_hub.ports[idx]
                    self.incident_service.report_incident(
                        hub_id=target_hub.id,
                        entity_type="CHARGING_PORT",
                        entity_id=port.id,
                        severity="CRITICAL",
                        description=f"Cháy cầu chì kỹ thuật cổng sạc số {port.port_number} do quá tải điện."
                    )

        elif config.scenario_type == ScenarioType.HUB_EXHAUSTION:
            # Giảm mạnh lượng xe tại Hub KTX Khu B để đưa vào trạng thái sắp cạn kiệt
            target_hub = self.hub_service.get_hub_by_id("HUB_KTX_B")
            if target_hub and len(target_hub.vehicle_ids) > 4:
                # Đổi bớt sang trạng thái bảo trì hoặc di dời
                for v_id in target_hub.vehicle_ids[3:]:
                    if v_id in self.hub_service.vehicles:
                        self.hub_service.vehicles[v_id].status = "MAINTENANCE"

    def _simulate_tick_demand(self, tick: int, config: SimulationConfig) -> tuple:
        """Mô phỏng nhu cầu sinh viên xuất hiện tại tick cụ thể"""
        step_reqs = 0
        step_fulfilled = 0
        step_unmet = 0
        step_alerts = []

        if config.scenario_type == ScenarioType.METRO_RUSH_HOUR:
            # Tàu Metro cập ga: Ticks 2, 4, 6 có lượng sinh viên đổ bộ ồ ạt
            if tick in [2, 4, 6]:
                demand_count = int(18 * config.student_demand_multiplier)
            else:
                demand_count = random.randint(4, 8)

            step_reqs = demand_count
            metro_hub = self.hub_service.get_hub_by_id("HUB_METRO")

            for i in range(demand_count):
                dest_hub_id = random.choice(["HUB_BK_KHTN", "HUB_UIT_IU", "HUB_KTX_A"])
                vtype = "E_BIKE" if i % 2 == 0 else "E_SCOOTER"
                res = self.booking_service.rent_vehicle(
                    user_id=f"SV_METRO_{tick}_{i}",
                    user_name=f"Sinh viên {tick}-{i}",
                    origin_hub_id="HUB_METRO",
                    vehicle_type=vtype,
                    destination_hub_id=dest_hub_id
                )
                if res["success"]:
                    step_fulfilled += 1
                    # Giả lập hoàn tất chuyến đi sau 1 tick tiếp theo
                    trip_id = res["trip"]["id"]
                    self.booking_service.return_vehicle(trip_id, dest_hub_id, simulated_duration_minutes=15.0)
                else:
                    step_unmet += 1

            if step_unmet > 0:
                step_alerts.append(f"Ga Metro thiếu hụt xe: {step_unmet}/{demand_count} sinh viên không lấy được phương tiện!")

        elif config.scenario_type == ScenarioType.CHARGING_SPIKE:
            # Đột biến nhu cầu sạc điện (ví dụ 15-25 sinh viên cùng đăng ký sạc xe cá nhân và xe công cộng)
            demand_count = int(8 * config.student_demand_multiplier)
            step_reqs = demand_count
            hubs_pool = ["HUB_KTX_A", "HUB_KTX_B"]

            for i in range(demand_count):
                target_hub_id = random.choice(hubs_pool)
                res = self.scheduler.enqueue_charging_request(
                    hub_id=target_hub_id,
                    vehicle_id=f"PERS_SPIKE_{tick}_{i}",
                    user_id=f"SV_CHARGE_{tick}_{i}",
                    target_soc=95.0,
                    minutes_until_needed=random.choice([30.0, 60.0, 120.0]),
                    is_personal=True
                )
                if res["success"]:
                    step_fulfilled += 1
                else:
                    step_unmet += 1

            step_alerts.append(f"Nhu cầu sạc cao điểm: Đã xếp {step_fulfilled} phương tiện vào hàng đợi lập lịch thông minh.")

        elif config.scenario_type == ScenarioType.CLUSTER_IMBALANCE:
            # Sự kiện tại NVH Sinh viên: Rất nhiều xe di chuyển dồn về Hub Thư viện & NVHSV
            demand_count = int(12 * config.student_demand_multiplier)
            step_reqs = demand_count
            origin_pool = ["HUB_KTX_A", "HUB_KTX_B", "HUB_UIT_IU"]

            for i in range(demand_count):
                origin = random.choice(origin_pool)
                res = self.booking_service.rent_vehicle(
                    user_id=f"SV_EVENT_{tick}_{i}",
                    user_name=f"Sinh viên Tham gia Sự kiện {i}",
                    origin_hub_id=origin,
                    vehicle_type="E_BIKE",
                    destination_hub_id="HUB_LIB_NVHSV"
                )
                if res["success"]:
                    ret_res = self.booking_service.return_vehicle(res["trip"]["id"], "HUB_LIB_NVHSV", simulated_duration_minutes=12.0)
                    if ret_res["success"]:
                        step_fulfilled += 1
                    else:
                        step_unmet += 1
                        step_alerts.append(f"Hub NVH Sinh viên đầy chỗ đỗ! Đã hướng dẫn sinh viên sang {ret_res.get('fallback_hub', {}).get('fallback_hub_name', 'Hub phụ')}.")
                else:
                    step_unmet += 1

        else:
            # Kịch bản thông thường / cạn kiệt Hub mặc định
            demand_count = random.randint(8, 15)
            step_reqs = demand_count
            for i in range(demand_count):
                orig = random.choice(list(self.hub_service.hubs.keys()))
                dest = random.choice([h for h in self.hub_service.hubs.keys() if h != orig])
                res = self.booking_service.rent_vehicle(
                    user_id=f"SV_STD_{tick}_{i}",
                    user_name=f"Sinh viên {i}",
                    origin_hub_id=orig,
                    vehicle_type="E_BIKE",
                    destination_hub_id=dest
                )
                if res["success"]:
                    step_fulfilled += 1
                    self.booking_service.return_vehicle(res["trip"]["id"], dest, simulated_duration_minutes=15.0)
                else:
                    step_unmet += 1

        return step_reqs, step_fulfilled, step_unmet, step_alerts

    def _generate_scenario_recommendations(
        self,
        scenario_type: ScenarioType,
        service_level: float,
        unmet: int,
        rebalanced: int
    ) -> List[str]:
        """Tự động sinh các giải pháp điều phối chiến lược dựa trên kết quả mô phỏng"""
        recs = []
        if scenario_type == ScenarioType.METRO_RUSH_HOUR:
            recs.append("Kích hoạt kế hoạch dự phòng Metro: Điều động trước 25-35 xe đạp điện từ KTX Khu B về Ga Metro trước giờ cao điểm 30 phút.")
            recs.append("Thiết lập luồng ưu tiên trả xe tại Hub Ga Metro bằng cách giảm 20% giá vé cho sinh viên trả xe về Ga Metro vào buổi sáng.")
        elif scenario_type == ScenarioType.PORT_BREAKDOWN:
            recs.append("Kích hoạt chuyển mạch tự động (Failover): Cô lập cổng sạc báo lỗi và tự động điều phối xe sang các cổng 7.4kW liền kề.")
            recs.append("Gửi thông báo đẩy (Push Notification) điều hướng sinh viên có nhu cầu sạc sang Hub KTX A hoặc Cụm UIT-IU.")
        elif scenario_type == ScenarioType.CHARGING_SPIKE:
            recs.append("Áp dụng biểu giá sạc động (Dynamic Pricing) và cơ chế phân phối công suất luân phiên (Time-slice Power Shifting) để tránh vượt đỉnh tải trạm.")
            recs.append("Ưu tiên tối đa cho xe có SoC dưới 25% và xe có lịch đặt trước trong 45 phút tiếp theo.")
        elif scenario_type == ScenarioType.CLUSTER_IMBALANCE:
            recs.append("Mở rộng vùng đỗ tạm thời (Virtual Overflow Geofence) tại khu vực Nhà văn hóa Sinh viên trong thời gian diễn ra sự kiện lớn.")
            recs.append("Bố trí 2 xe tải trung chuyển tuần hoàn liên tục để gom xe từ NVHSV phân phối đều về Cụm BK-KHTN và UIT.")
        else:
            recs.append("Duy trì thuật toán tái cân bằng định kỳ mỗi 30 phút một lần để đảm bảo tỷ lệ sẵn sàng của toàn mạng lưới đạt trên 92%.")

        if service_level < 85.0:
            recs.append(f"Cảnh báo: Tỷ lệ đáp ứng hiện tại ({service_level}%) chưa đạt chuẩn mục tiêu (>90%). Cần bổ sung thêm xe hoặc tăng tần suất điều xe tải.")
        else:
            recs.append(f"Hệ thống đạt hiệu suất tốt: Tỷ lệ phục vụ {service_level}%, đã hoàn tất điều phối {rebalanced} lượt phương tiện.")

        return recs
