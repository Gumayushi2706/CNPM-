"""
Mô hình Mô phỏng & Phân tích Kịch bản (What-if Simulation Engine)
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ScenarioType(str, Enum):
    METRO_RUSH_HOUR = "METRO_RUSH_HOUR"         # Giờ cao điểm tại Ga Metro ĐHQG
    HUB_EXHAUSTION = "HUB_EXHAUSTION"           # Hub cạn kiệt xe hoặc hết chỗ đỗ
    CHARGING_SPIKE = "CHARGING_SPIKE"           # Nhu cầu sạc tăng đột biến
    PORT_BREAKDOWN = "PORT_BREAKDOWN"           # Hỏng cổng sạc / sự cố điện
    CLUSTER_IMBALANCE = "CLUSTER_IMBALANCE"     # Dồn ứ xe do sự kiện tại NVH Sinh viên


class SimulationConfig(BaseModel):
    scenario_type: ScenarioType
    scenario_name: str
    duration_ticks: int = 12                     # Mỗi tick tương đương 15 phút (tổng 3 giờ)
    student_demand_multiplier: float = 2.5       # Hệ số nhân lượng sinh viên
    target_hub_id: Optional[str] = "HUB_METRO"
    faulty_ports_count: int = 4
    auto_rebalance: bool = True                  # Bật/tắt thuật toán điều phối tự động
    smart_charging: bool = True                  # Bật/tắt thuật toán lập lịch sạc thông minh
    custom_params: Dict[str, Any] = Field(default_factory=dict)


class SimulationStepResult(BaseModel):
    tick: int
    time_label: str
    requests_generated: int
    requests_fulfilled: int
    requests_unmet: int
    active_trips: int
    active_charging_sessions: int
    grid_total_power_kw: float
    hub_states: Dict[str, Dict[str, Any]]
    rebalance_actions: List[Dict[str, Any]] = Field(default_factory=list)
    alerts: List[str] = Field(default_factory=list)


class SimulationSummary(BaseModel):
    scenario_type: str
    scenario_name: str
    total_duration_minutes: int
    total_student_requests: int
    fulfilled_requests: int
    unmet_requests: int
    service_level_percent: float
    average_wait_time_minutes: float
    total_rebalanced_vehicles: int
    total_energy_delivered_kwh: float
    peak_grid_load_kw: float
    recommendations: List[str] = Field(default_factory=list)
    steps: List[SimulationStepResult] = Field(default_factory=list)
