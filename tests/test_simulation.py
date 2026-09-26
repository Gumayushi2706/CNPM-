"""
Unit test kiểm tra Bộ máy Mô phỏng What-if Simulation
"""

from app.models.simulation import ScenarioType, SimulationConfig
from app.services.hub_service import HubService
from app.services.booking_service import BookingService
from app.services.smart_scheduler import SmartChargingScheduler
from app.services.rebalance_service import RebalanceService
from app.services.incident_service import IncidentService
from app.services.simulation_engine import SimulationEngine


def test_metro_rush_hour_simulation():
    hub_service = HubService()
    booking_service = BookingService(hub_service)
    scheduler = SmartChargingScheduler(hub_service)
    rebalance_service = RebalanceService(hub_service)
    incident_service = IncidentService(hub_service)
    sim_engine = SimulationEngine(hub_service, booking_service, scheduler, rebalance_service, incident_service)

    config = SimulationConfig(
        scenario_type=ScenarioType.METRO_RUSH_HOUR,
        scenario_name="Test Metro Rush Hour",
        duration_ticks=6,
        student_demand_multiplier=1.5,
        auto_rebalance=True,
        smart_charging=True
    )

    summary = sim_engine.run_scenario(config)

    assert summary.total_student_requests > 0
    assert summary.fulfilled_requests > 0
    assert summary.service_level_percent > 0.0
    assert len(summary.steps) == 6
    assert len(summary.recommendations) > 0


def test_port_breakdown_simulation():
    hub_service = HubService()
    booking_service = BookingService(hub_service)
    scheduler = SmartChargingScheduler(hub_service)
    rebalance_service = RebalanceService(hub_service)
    incident_service = IncidentService(hub_service)
    sim_engine = SimulationEngine(hub_service, booking_service, scheduler, rebalance_service, incident_service)

    config = SimulationConfig(
        scenario_type=ScenarioType.PORT_BREAKDOWN,
        scenario_name="Test Port Breakdown",
        duration_ticks=4,
        faulty_ports_count=3,
        auto_rebalance=False,
        smart_charging=True
    )

    summary = sim_engine.run_scenario(config)
    assert len(incident_service.get_active_incidents()) >= 3
