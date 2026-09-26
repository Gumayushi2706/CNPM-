"""
Unit test kiểm tra Thuật toán Lập lịch sạc thông minh (Smart Scheduler)
"""

from app.services.hub_service import HubService
from app.services.smart_scheduler import SmartChargingScheduler


def test_priority_score_calculation():
    hub_service = HubService()
    scheduler = SmartChargingScheduler(hub_service)

    # Xe pin 10% cần đi trong 20 phút
    urgent_score = scheduler.calculate_priority_score(current_soc=10.0, minutes_until_needed=20.0, is_shared_fleet=True)
    
    # Xe pin 80% cần đi trong 180 phút
    relaxed_score = scheduler.calculate_priority_score(current_soc=80.0, minutes_until_needed=180.0, is_shared_fleet=False)

    assert urgent_score > relaxed_score


def test_enqueue_and_dispatch():
    hub_service = HubService()
    scheduler = SmartChargingScheduler(hub_service)

    res = scheduler.enqueue_charging_request(
        hub_id="HUB_KTX_A",
        vehicle_id="EB_TEST_SCHED",
        user_id="SV_TEST",
        target_soc=100.0,
        minutes_until_needed=30.0,
        is_personal=False
    )
    assert res["success"] is True
    assert "priority_score" in res["request"]


def test_charging_progress_and_completion():
    hub_service = HubService()
    scheduler = SmartChargingScheduler(hub_service)

    # Thêm xe cần sạc từ 95% lên 100%
    scheduler.enqueue_charging_request(
        hub_id="HUB_KTX_A",
        vehicle_id="EB_NEAR_FULL",
        user_id="SV_TEST_2",
        target_soc=100.0,
        minutes_until_needed=15.0
    )
    
    # Xe được gán sạc
    v = hub_service.vehicles.get("EB_NEAR_FULL")
    v.battery_soc = 98.0

    step_res = scheduler.progress_charging_step(minutes=30.0)
    assert step_res["completed_count"] >= 1
    assert v.battery_soc == 100.0
