"""
Hệ thống Smart E-Mobility Hub - Khu đô thị ĐHQG-HCM
FastAPI Backend Application & REST API
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import PROJECT_NAME, VERSION, VNU_CENTER_LAT, VNU_CENTER_LNG, FEES, PORT_TYPES
from .models.simulation import ScenarioType, SimulationConfig
from .services import (
    HubService,
    BookingService,
    SmartChargingScheduler,
    RebalanceService,
    IncidentService,
    SimulationEngine
)

# Khởi tạo FastAPI App
app = FastAPI(
    title=PROJECT_NAME,
    description="Hệ thống điều phối phương tiện điện và quản lý Mobility Hub trong Khu đô thị ĐHQG-HCM",
    version=VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Khởi tạo Singleton Services
hub_service = HubService()
booking_service = BookingService(hub_service)
scheduler = SmartChargingScheduler(hub_service)
rebalance_service = RebalanceService(hub_service)
incident_service = IncidentService(hub_service)
simulation_engine = SimulationEngine(
    hub_service,
    booking_service,
    scheduler,
    rebalance_service,
    incident_service
)

# Thiết lập đường dẫn thư mục web
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "web" / "static"
TEMPLATES_DIR = BASE_DIR / "web" / "templates"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ==========================================
# GIAO DIỆN WEB CHÍNH (HTML DASHBOARD)
# ==========================================

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    index_file = TEMPLATES_DIR / "index.html"
    if index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Smart E-Mobility Hub - ĐHQG-HCM</h1><p>Đang tải giao diện...</p>")


# ==========================================
# REQUEST BODY SCHEMAS
# ==========================================

class RentRequest(BaseModel):
    user_id: str = "SV21001"
    user_name: str = "Nguyễn Văn Sinh Viên"
    origin_hub_id: str = "HUB_METRO"
    vehicle_type: str = "E_BIKE"  # E_BIKE hoặc E_SCOOTER
    destination_hub_id: Optional[str] = "HUB_BK_KHTN"


class ReturnRequest(BaseModel):
    trip_id: str
    destination_hub_id: str
    duration_minutes: float = 15.0


class ReserveParkingRequest(BaseModel):
    user_id: str = "SV21002"
    user_name: str = "Trần Thị Lan"
    hub_id: str = "HUB_KTX_B"
    vehicle_plate: str = "59-X1-9988"
    estimated_hours: float = 4.0


class ChargeEnqueueRequest(BaseModel):
    hub_id: str = "HUB_KTX_A"
    vehicle_id: str = "EB_001"
    user_id: str = "SV21003"
    target_soc: float = 100.0
    minutes_until_needed: float = 60.0
    is_personal: bool = False


class RebalanceExecuteRequest(BaseModel):
    from_hub_id: str
    to_hub_id: str
    quantity: int = 5


class IncidentReportRequest(BaseModel):
    hub_id: str
    entity_type: str  # CHARGING_PORT, VEHICLE, HUB_GRID
    entity_id: str
    severity: str = "HIGH"
    description: str = ""


class SimulationRunRequest(BaseModel):
    scenario_type: str = "METRO_RUSH_HOUR"
    duration_ticks: int = 12
    student_demand_multiplier: float = 2.0
    target_hub_id: Optional[str] = "HUB_METRO"
    faulty_ports_count: int = 4
    auto_rebalance: bool = True
    smart_charging: bool = True


# ==========================================
# REST API: TỔNG QUAN & MOBILITY HUBS
# ==========================================

@app.get("/api/network/overview")
async def get_network_overview():
    """Lấy tổng hợp chỉ số trạng thái toàn bộ mạng lưới ĐHQG-HCM"""
    return hub_service.get_network_overview()


@app.get("/api/hubs")
async def list_hubs():
    """Lấy danh sách 6 Mobility Hubs kèm trạng thái chi tiết thời gian thực"""
    return hub_service.get_all_hubs()


@app.get("/api/hubs/{hub_id}")
async def get_hub(hub_id: str):
    detail = hub_service.get_hub_detail(hub_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Không tìm thấy Hub")
    return detail


@app.get("/api/hubs/nearest")
async def find_nearest(
    lat: float = Query(VNU_CENTER_LAT, description="Vĩ độ"),
    lng: float = Query(VNU_CENTER_LNG, description="Kinh độ"),
    vehicle_type: Optional[str] = Query(None, description="Loại xe cần tìm (E_BIKE hoặc E_SCOOTER)")
):
    return hub_service.find_nearest_hubs(lat, lng, vehicle_type)


@app.get("/api/hubs/{hub_id}/fallback")
async def get_fallback(
    hub_id: str,
    resource: str = Query("vehicle", description="Tài nguyên cần tìm (vehicle, slot, port)")
):
    fallback = hub_service.get_fallback_hub(hub_id, required_resource=resource)
    if not fallback:
        return {"has_fallback": False, "message": "Không tìm thấy Hub thay thế phù hợp."}
    return {"has_fallback": True, "data": fallback}


# ==========================================
# REST API: PHÂN HỆ SINH VIÊN (STUDENT PORTAL)
# ==========================================

@app.post("/api/student/rent")
async def rent_vehicle(req: RentRequest):
    """Sinh viên tìm và nhận xe tại Hub"""
    res = booking_service.rent_vehicle(
        user_id=req.user_id,
        user_name=req.user_name,
        origin_hub_id=req.origin_hub_id,
        vehicle_type=req.vehicle_type,
        destination_hub_id=req.destination_hub_id
    )
    return res


@app.post("/api/student/return")
async def return_vehicle(req: ReturnRequest):
    """Sinh viên trả xe tại Hub đích"""
    res = booking_service.return_vehicle(
        trip_id=req.trip_id,
        destination_hub_id=req.destination_hub_id,
        simulated_duration_minutes=req.duration_minutes
    )
    return res


@app.post("/api/student/reserve-parking")
async def reserve_parking(req: ReserveParkingRequest):
    """Sinh viên đặt chỗ đỗ xe điện cá nhân"""
    res = booking_service.reserve_personal_parking(
        user_id=req.user_id,
        user_name=req.user_name,
        hub_id=req.hub_id,
        vehicle_plate=req.vehicle_plate,
        estimated_hours=req.estimated_hours
    )
    return res


@app.get("/api/student/bookings")
async def get_user_bookings(user_id: str = Query("SV21001")):
    return booking_service.get_user_bookings(user_id)


@app.get("/api/trips")
async def list_trips():
    return booking_service.get_all_trips()


# ==========================================
# REST API: LẬP LỊCH SẠC THÔNG MINH (SMART CHARGING)
# ==========================================

@app.get("/api/operator/scheduler/status")
async def get_scheduler_status():
    return scheduler.get_scheduler_status()


@app.post("/api/operator/scheduler/enqueue")
async def enqueue_charging(req: ChargeEnqueueRequest):
    res = scheduler.enqueue_charging_request(
        hub_id=req.hub_id,
        vehicle_id=req.vehicle_id,
        user_id=req.user_id,
        target_soc=req.target_soc,
        minutes_until_needed=req.minutes_until_needed,
        is_personal=req.is_personal
    )
    return res


@app.post("/api/operator/scheduler/step")
async def progress_charging_step(minutes: float = Query(15.0)):
    return scheduler.progress_charging_step(minutes=minutes)


# ==========================================
# REST API: ĐIỀU PHỐI CÂN BẰNG PHƯƠNG TIỆN (REBALANCE)
# ==========================================

@app.get("/api/operator/rebalance/analysis")
async def analyze_rebalance():
    return rebalance_service.analyze_network_balance()


@app.get("/api/operator/rebalance/plans")
async def get_rebalance_plans():
    return rebalance_service.generate_rebalance_plan()


@app.post("/api/operator/rebalance/execute")
async def execute_rebalance(req: RebalanceExecuteRequest):
    return rebalance_service.execute_rebalance_transfer(
        from_hub_id=req.from_hub_id,
        to_hub_id=req.to_hub_id,
        quantity=req.quantity
    )


@app.post("/api/operator/rebalance/execute-all")
async def execute_all_rebalance():
    return rebalance_service.execute_all_recommended_plans()


# ==========================================
# REST API: SỰ CỐ KỸ THUẬT (INCIDENTS)
# ==========================================

@app.get("/api/incidents")
async def list_incidents():
    return incident_service.get_all_incidents()


@app.post("/api/incidents/report")
async def report_incident(req: IncidentReportRequest):
    return incident_service.report_incident(
        hub_id=req.hub_id,
        entity_type=req.entity_type,
        entity_id=req.entity_id,
        severity=req.severity,
        description=req.description
    )


@app.post("/api/incidents/{incident_id}/resolve")
async def resolve_incident(incident_id: str, note: str = Query("Đã sửa chữa và kiểm định xong")):
    return incident_service.resolve_incident(incident_id, note)


# ==========================================
# REST API: BỘ MÁY MÔ PHỎNG WHAT-IF (SIMULATION)
# ==========================================

@app.get("/api/simulation/scenarios")
async def get_scenarios():
    return [
        {
            "id": "METRO_RUSH_HOUR",
            "name": "Kịch bản 1: Giờ cao điểm tại Ga Metro ĐHQG",
            "description": "Lượng sinh viên từ tuyến Metro số 1 tăng đột biến ồ ạt, kiểm tra khả năng phục vụ và phản ứng điều xe từ các Hub khác.",
            "default_hub": "HUB_METRO",
            "multiplier": 2.5
        },
        {
            "id": "HUB_EXHAUSTION",
            "name": "Kịch bản 2: Hub KTX cạn kiệt xe hoặc đầy bãi đỗ",
            "description": "Mô phỏng tình huống KTX Khu B cạn kiệt xe đạp điện, kiểm tra cơ chế cảnh báo sớm và tự động chuyển hướng sinh viên.",
            "default_hub": "HUB_KTX_B",
            "multiplier": 2.0
        },
        {
            "id": "CHARGING_SPIKE",
            "name": "Kịch bản 3: Đột biến nhu cầu sạc điện cao điểm",
            "description": "Hàng chục xe đồng loạt cần sạc tại KTX Khu A & B, kiểm tra thuật toán lập lịch sạc thông minh và kiểm soát đỉnh tải trạm.",
            "default_hub": "HUB_KTX_A",
            "multiplier": 2.2
        },
        {
            "id": "PORT_BREAKDOWN",
            "name": "Kịch bản 4: Sự cố hỏng hàng loạt cổng sạc",
            "description": "Nhiều cổng sạc tại Ga Metro bị lỗi kỹ thuật, kiểm tra cơ chế ngắt an toàn, chuyển mạch tự động sang cổng dự phòng.",
            "default_hub": "HUB_METRO",
            "multiplier": 1.5
        },
        {
            "id": "CLUSTER_IMBALANCE",
            "name": "Kịch bản 5: Dồn ứ xe do sự kiện tại NVH Sinh viên",
            "description": "Lễ hội / Sự kiện lớn tại Nhà văn hóa Sinh viên làm xe dồn về ồ ạt, bãi đỗ đầy 100%, kiểm tra cơ chế gom xe và giải tỏa áp lực.",
            "default_hub": "HUB_LIB_NVHSV",
            "multiplier": 2.5
        }
    ]


@app.post("/api/simulation/run")
async def run_simulation(req: SimulationRunRequest):
    try:
        scen_type = ScenarioType(req.scenario_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Kịch bản không hợp lệ: {req.scenario_type}")

    scenario_names = {
        ScenarioType.METRO_RUSH_HOUR: "Mô phỏng Giờ cao điểm Ga Metro ĐHQG",
        ScenarioType.HUB_EXHAUSTION: "Mô phỏng Cạn kiệt / Đầy bãi tại Hub KTX",
        ScenarioType.CHARGING_SPIKE: "Mô phỏng Đột biến nhu cầu sạc điện",
        ScenarioType.PORT_BREAKDOWN: "Mô phỏng Sự cố hỏng cổng sạc",
        ScenarioType.CLUSTER_IMBALANCE: "Mô phỏng Dồn ứ phương tiện sự kiện NVHSV"
    }

    config = SimulationConfig(
        scenario_type=scen_type,
        scenario_name=scenario_names.get(scen_type, "Mô phỏng What-if"),
        duration_ticks=req.duration_ticks,
        student_demand_multiplier=req.student_demand_multiplier,
        target_hub_id=req.target_hub_id,
        faulty_ports_count=req.faulty_ports_count,
        auto_rebalance=req.auto_rebalance,
        smart_charging=req.smart_charging
    )

    summary = simulation_engine.run_scenario(config)
    return summary.model_dump()


@app.post("/api/simulation/reset")
async def reset_system():
    """Khôi phục trạng thái mạng lưới về cấu hình ban đầu"""
    global hub_service, booking_service, scheduler, rebalance_service, incident_service, simulation_engine
    hub_service = HubService()
    booking_service = BookingService(hub_service)
    scheduler = SmartChargingScheduler(hub_service)
    rebalance_service = RebalanceService(hub_service)
    incident_service = IncidentService(hub_service)
    simulation_engine = SimulationEngine(
        hub_service,
        booking_service,
        scheduler,
        rebalance_service,
        incident_service
    )
    return {"success": True, "message": "Đã thiết lập lại toàn bộ mạng lưới Mobility Hubs về trạng thái ban đầu."}
