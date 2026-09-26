"""
Script Chạy Mô Phỏng Dòng Lệnh (CLI Demo)
Dành cho kiểm tra nhanh tính năng và xuất kết quả trực tiếp trên Terminal
Cách chạy:
    python demo_cli.py
"""

import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Đảm bảo in tiếng Việt chuẩn trên Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.services import (
    HubService,
    BookingService,
    SmartChargingScheduler,
    RebalanceService,
    IncidentService,
    SimulationEngine
)
from app.models.simulation import ScenarioType, SimulationConfig


def run_cli_demo():
    print("=" * 75)
    print("       SMART E-MOBILITY HUB - KHU ĐÔ THỊ ĐHQG-HCM")
    print("                  DEMO DÒNG LỆNH (CLI)")
    print("=" * 75)

    # 1. Khởi tạo các dịch vụ
    print("\n[1] Đang khởi tạo mạng lưới 6 Hubs ĐHQG-HCM...")
    hub_service = HubService()
    booking_service = BookingService(hub_service)
    scheduler = SmartChargingScheduler(hub_service)
    rebalance_service = RebalanceService(hub_service)
    incident_service = IncidentService(hub_service)
    sim_engine = SimulationEngine(hub_service, booking_service, scheduler, rebalance_service, incident_service)

    overview = hub_service.get_network_overview()
    print(f"    -> Tổng số Hub: {overview['total_hubs']}")
    print(f"    -> Tổng số xe: {overview['vehicles']['total']} (Sẵn sàng: {overview['vehicles']['available']})")
    print(f"    -> Tổng vị trí đỗ: {overview['slots']['total']} (Trống: {overview['slots']['available']})")
    print(f"    -> Tổng cổng sạc: {overview['ports']['total']} (Rảnh: {overview['ports']['available']})")

    # 2. Demo Sinh viên thuê xe
    print("\n[2] Mô phỏng Sinh viên đặt và nhận xe tại Ga Metro ĐHQG...")
    rent_res = booking_service.rent_vehicle(
        user_id="SV21001",
        user_name="Nguyễn Văn A",
        origin_hub_id="HUB_METRO",
        vehicle_type="E_BIKE",
        destination_hub_id="HUB_BK_KHTN"
    )
    if rent_res["success"]:
        trip = rent_res["trip"]
        veh = rent_res["vehicle"]
        print(f"    -> Thành công! Xe: {veh['plate_number']} ({veh['model_name']})")
        print(f"    -> Mức pin xuất phát: {veh['battery_soc']}%")
        print(f"    -> Mã chuyến đi: {trip['id']}")

        # Trả xe tại Bách Khoa
        print("    -> Sinh viên di chuyển đến Cụm BK-KHTN và trả xe...")
        time.sleep(0.5)
        return_res = booking_service.return_vehicle(trip["id"], "HUB_BK_KHTN", simulated_duration_minutes=15.0)
        print(f"    -> {return_res['message']}")
    else:
        print(f"    -> Lỗi: {rent_res['message']}")

    # 3. Demo Lập lịch sạc thông minh
    print("\n[3] Mô phỏng Lập lịch sạc thông minh đa tiêu chí...")
    sched_res = scheduler.enqueue_charging_request(
        hub_id="HUB_KTX_A",
        vehicle_id="EB_002",
        user_id="SV21002",
        target_soc=100.0,
        minutes_until_needed=30.0,
        is_personal=False
    )
    print(f"    -> Đăng ký sạc xe EB_002: Điểm ưu tiên = {sched_res['request']['priority_score']}")
    status = scheduler.get_scheduler_status()
    print(f"    -> Số phiên sạc đang kích hoạt: {status['active_charging_count']}")

    # 4. Demo Phân tích cân bằng và Điều phối xe
    print("\n[4] Mô phỏng Thuật toán Điều phối Cân bằng Tải (Rebalancing)...")
    plans = rebalance_service.generate_rebalance_plan()
    if plans:
        for p in plans[:2]:
            print(f"    -> Kế hoạch: Chuyển {p['quantity']} xe từ [{p['from_hub_name']}] sang [{p['to_hub_name']}] ({p['distance_km']} km)")
        exec_res = rebalance_service.execute_all_recommended_plans()
        print(f"    -> Đã thực thi {exec_res['executed_transfers_count']} lệnh điều phối ({exec_res['total_vehicles_moved']} xe chuyển giao thành công)!")
    else:
        print("    -> Mạng lưới đang cân bằng tối ưu.")

    # 5. Demo Kịch bản What-if: Giờ cao điểm Ga Metro
    print("\n[5] Mô phỏng Kịch bản What-if: Giờ cao điểm tại Ga Metro ĐHQG...")
    config = SimulationConfig(
        scenario_type=ScenarioType.METRO_RUSH_HOUR,
        scenario_name="Metro Rush Hour Peak",
        duration_ticks=6,
        student_demand_multiplier=2.0,
        auto_rebalance=True,
        smart_charging=True
    )
    summary = sim_engine.run_scenario(config)

    print(f"    -> Tổng số yêu cầu sinh viên phát sinh: {summary.total_student_requests}")
    print(f"    -> Số yêu cầu đáp ứng thành công: {summary.fulfilled_requests}")
    print(f"    -> Tỷ lệ phục vụ (% Service Level): {summary.service_level_percent}%")
    print(f"    -> Thời gian chờ trung bình: {summary.average_wait_time_minutes} phút")
    print(f"    -> Đỉnh tải trạm sạc: {summary.peak_grid_load_kw} kW")
    print("    -> Khuyến nghị của hệ thống:")
    for rec in summary.recommendations:
        print(f"       * {rec}")

    print("\n" + "=" * 75)
    print("  HOÀN TẤT DEMO CLI!")
    print("  Để mở Giao diện Web Trực quan hóa, vui lòng chạy: python run.py")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    run_cli_demo()
