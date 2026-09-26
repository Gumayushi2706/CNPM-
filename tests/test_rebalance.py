"""
Unit test kiểm tra Thuật toán Điều phối Cân bằng Phương tiện giữa các Hubs
"""

from app.services.hub_service import HubService
from app.services.rebalance_service import RebalanceService


def test_rebalance_analysis():
    hub_service = HubService()
    rebalance_service = RebalanceService(hub_service)

    analysis = rebalance_service.analyze_network_balance()
    assert "surplus_hubs" in analysis
    assert "deficit_hubs" in analysis
    assert "balanced_hubs" in analysis


def test_execute_transfer():
    hub_service = HubService()
    rebalance_service = RebalanceService(hub_service)

    # Lấy xe từ KTX B (nhiều xe) sang Metro (ít xe hơn)
    from_hub = hub_service.get_hub_by_id("HUB_KTX_B")
    to_hub = hub_service.get_hub_by_id("HUB_METRO")

    initial_from_count = len(from_hub.vehicle_ids)
    initial_to_count = len(to_hub.vehicle_ids)

    # Kiểm tra số slot khả dụng tại to_hub
    avail_slots = len([s for s in to_hub.slots if s.slot_type.value == "SHARED_VEHICLE" and s.is_available()])
    transfer_qty = min(2, avail_slots)

    res = rebalance_service.execute_rebalance_transfer("HUB_KTX_B", "HUB_METRO", quantity=transfer_qty)
    assert res["success"] is True

    assert len(from_hub.vehicle_ids) == initial_from_count - transfer_qty
    assert len(to_hub.vehicle_ids) == initial_to_count + transfer_qty
