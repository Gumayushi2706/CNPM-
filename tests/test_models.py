"""
Unit test kiểm tra tính toàn vẹn của các Domain Models
"""

from app.models.vehicle import Vehicle, VehicleType, VehicleStatus
from app.models.hub import Hub, ParkingSlot, ChargingPort, SlotStatus, SlotType, PortStatus
from app.models.booking import Booking, BookingType, BookingStatus, Trip


def test_vehicle_creation_and_range():
    v = Vehicle(
        id="EB_TEST_01",
        plate_number="59-EB-0001",
        vehicle_type=VehicleType.E_BIKE,
        model_name="VNU Bike Test",
        battery_soc=80.0
    )
    assert v.is_usable(min_soc=20.0) is True
    assert v.estimated_range_km() == 40.0  # 80 * 0.5


def test_hub_capacity_and_utilization():
    slot1 = ParkingSlot(id="S1", hub_id="H1", slot_number=1, status=SlotStatus.OCCUPIED)
    slot2 = ParkingSlot(id="S2", hub_id="H1", slot_number=2, status=SlotStatus.AVAILABLE)
    port1 = ChargingPort(id="P1", hub_id="H1", port_number=1, power_kw=7.4, status=PortStatus.CHARGING)
    port2 = ChargingPort(id="P2", hub_id="H1", port_number=2, power_kw=3.3, status=PortStatus.AVAILABLE)

    hub = Hub(
        id="H1",
        code="H1",
        name="Test Hub",
        category="Test",
        latitude=10.87,
        longitude=106.80,
        description="Test",
        capacity_slots=2,
        capacity_chargers=2,
        grid_power_limit_kw=50.0,
        slots=[slot1, slot2],
        ports=[port1, port2]
    )

    assert hub.get_available_slots_count() == 1
    assert hub.get_available_ports_count() == 1
    assert hub.get_current_power_draw_kw() == 7.4
    assert hub.get_slot_utilization() == 50.0
    assert hub.get_charger_utilization() == 50.0


def test_booking_and_trip():
    b = Booking(
        id="BK_01",
        user_id="SV001",
        user_name="Nguyen Van A",
        booking_type=BookingType.VEHICLE_RENTAL,
        hub_id="HUB_METRO"
    )
    assert b.status == BookingStatus.CONFIRMED

    t = Trip(
        id="TRIP_01",
        booking_id=b.id,
        user_id="SV001",
        vehicle_id="EB_001",
        origin_hub_id="HUB_METRO",
        destination_hub_id="HUB_BK_KHTN",
        distance_km=2.5,
        fare=15000.0
    )
    assert t.status == "IN_PROGRESS"
    assert t.distance_km == 2.5
