"""
Dịch vụ Quản lý Sự cố và Bảo trì (Incident Management Service)
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from ..models.hub import PortStatus
from ..models.vehicle import VehicleStatus
from ..models.incident import Incident, IncidentSeverity, IncidentStatus, IncidentEntityType
from .hub_service import HubService


class IncidentService:
    def __init__(self, hub_service: HubService):
        self.hub_service = hub_service
        self.incidents: Dict[str, Incident] = {}

    def report_incident(
        self,
        hub_id: str,
        entity_type: str,
        entity_id: str,
        severity: str = "HIGH",
        description: str = ""
    ) -> Dict[str, Any]:
        """Báo cáo sự cố và tự động áp dụng phương án cô lập, chuyển hướng tài nguyên"""
        hub = self.hub_service.get_hub_by_id(hub_id)
        if not hub:
            return {"success": False, "message": f"Không tìm thấy Hub: {hub_id}"}

        incident_id = f"INC_{uuid.uuid4().hex[:8].upper()}"
        action_log = []

        ent_type = IncidentEntityType(entity_type)
        sev = IncidentSeverity(severity)

        if ent_type == IncidentEntityType.CHARGING_PORT:
            # Tìm cổng sạc bị sự cố
            target_port = None
            for p in hub.ports:
                if p.id == entity_id:
                    target_port = p
                    break

            if target_port:
                target_port.status = PortStatus.FAULTY
                action_log.append(f"Cổng sạc {entity_id} đã bị ngắt kết nối an toàn.")

                # Nếu đang sạc xe, tìm cổng dự phòng để chuyển giao
                if target_port.current_vehicle_id:
                    v_id = target_port.current_vehicle_id
                    vehicle = self.hub_service.vehicles.get(v_id)
                    backup_ports = [p for p in hub.ports if p.is_available()]

                    if backup_ports:
                        backup = backup_ports[0]
                        backup.status = PortStatus.CHARGING
                        backup.current_vehicle_id = v_id
                        if vehicle:
                            vehicle.current_port_id = backup.id
                        target_port.current_vehicle_id = None
                        action_log.append(f"Xe {v_id} đã được tự động chuyển sang cổng dự phòng {backup.id}.")
                    else:
                        if vehicle:
                            vehicle.status = VehicleStatus.WAITING_CHARGE
                            vehicle.current_port_id = None
                        target_port.current_vehicle_id = None
                        action_log.append(f"Không còn cổng rảnh tại Hub. Xe {v_id} đã được xếp vào hàng đợi ưu tiên cao.")

        elif ent_type == IncidentEntityType.VEHICLE:
            vehicle = self.hub_service.vehicles.get(entity_id)
            if vehicle:
                vehicle.status = VehicleStatus.FAULTY
                action_log.append(f"Phương tiện {entity_id} đã bị khóa, đưa vào danh sách chờ kỹ thuật viên kiểm tra.")

        elif ent_type == IncidentEntityType.HUB_GRID:
            # Sự cố mất nguồn điện tại Hub -> ngắt toàn bộ cổng sạc
            for p in hub.ports:
                if p.status == PortStatus.CHARGING:
                    p.status = PortStatus.FAULTY
            action_log.append(f"Toàn bộ trạm sạc tại {hub.name} đã ngắt khẩn cấp để đảm bảo an toàn lưới điện.")

        action_str = " | ".join(action_log) if action_log else "Đã ghi nhận sự cố vào hệ thống giám sát."
        incident = Incident(
            id=incident_id,
            hub_id=hub_id,
            entity_type=ent_type,
            entity_id=entity_id,
            severity=sev,
            description=description or f"Sự cố {entity_type} {entity_id} tại {hub.name}",
            action_taken=action_str,
            reported_at=datetime.now().isoformat(),
            status=IncidentStatus.ACTIVE
        )
        self.incidents[incident_id] = incident

        return {
            "success": True,
            "message": f"Đã ghi nhận và xử lý sự cố {incident_id}",
            "incident": incident.model_dump(),
            "actions_taken": action_log
        }

    def resolve_incident(self, incident_id: str, resolution_note: str = "") -> Dict[str, Any]:
        """Đóng sự cố và khôi phục hoạt động của thiết bị"""
        incident = self.incidents.get(incident_id)
        if not incident:
            return {"success": False, "message": f"Không tìm thấy sự cố: {incident_id}"}

        hub = self.hub_service.get_hub_by_id(incident.hub_id)

        if incident.entity_type == IncidentEntityType.CHARGING_PORT and hub:
            for p in hub.ports:
                if p.id == incident.entity_id:
                    p.status = PortStatus.AVAILABLE
                    break
        elif incident.entity_type == IncidentEntityType.VEHICLE:
            v = self.hub_service.vehicles.get(incident.entity_id)
            if v:
                v.status = VehicleStatus.AVAILABLE

        incident.status = IncidentStatus.RESOLVED
        incident.resolved_at = datetime.now().isoformat()
        if resolution_note:
            incident.action_taken += f" [Đã xử lý: {resolution_note}]"

        return {
            "success": True,
            "message": f"Sự cố {incident_id} đã được khắc phục hoàn toàn.",
            "incident": incident.model_dump()
        }

    def get_all_incidents(self) -> List[Dict[str, Any]]:
        return [inc.model_dump() for inc in self.incidents.values()]

    def get_active_incidents(self) -> List[Dict[str, Any]]:
        return [inc.model_dump() for inc in self.incidents.values() if inc.status == IncidentStatus.ACTIVE]
