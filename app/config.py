"""
Cấu hình hệ thống Smart E-Mobility Hub - Khu đô thị ĐHQG-HCM
"""

from typing import Dict, Any

# Thông tin cơ bản dự án
PROJECT_NAME = "Smart E-Mobility Hub - ĐHQG-HCM"
VERSION = "1.0.0"
HOST = "0.0.0.0"
PORT = 8000

# Tọa độ trung tâm Khu đô thị ĐHQG-HCM (Linh Trung, Thủ Đức / Dĩ An)
VNU_CENTER_LAT = 10.8765
VNU_CENTER_LNG = 106.7985

# Danh sách 6 Mobility Hub chiến lược trong ĐHQG-HCM
HUBS_SEED_DATA = [
    {
        "id": "HUB_METRO",
        "code": "METRO-01",
        "name": "Hub Ga Metro ĐHQG",
        "category": "Transit Hub",
        "latitude": 10.8752,
        "longitude": 106.8005,
        "description": "Cửa ngõ đón sinh viên từ Tuyến Metro số 1 (Bến Thành - Suối Tiên). Nhu cầu xe đỉnh điểm vào giờ cao điểm sáng/chiều.",
        "capacity_slots": 40,
        "capacity_chargers": 12,
        "grid_power_limit_kw": 80.0,
        "initial_ebikes": 14,
        "initial_escooters": 12,
        "initial_personal_slots_occupied": 8,
    },
    {
        "id": "HUB_KTX_A",
        "code": "KTXA-02",
        "name": "Hub KTX Khu A ĐHQG",
        "category": "Residential Hub",
        "latitude": 10.8785,
        "longitude": 106.8062,
        "description": "Cụm KTX Khu A và Sân Vận động ĐHQG. Nhu cầu lấy xe buổi sáng đi học, tập trung sạc đêm.",
        "capacity_slots": 50,
        "capacity_chargers": 16,
        "grid_power_limit_kw": 100.0,
        "initial_ebikes": 18,
        "initial_escooters": 14,
        "initial_personal_slots_occupied": 12,
    },
    {
        "id": "HUB_KTX_B",
        "code": "KTXB-03",
        "name": "Hub KTX Khu B ĐHQG",
        "category": "Residential Hub",
        "latitude": 10.8838,
        "longitude": 106.7825,
        "description": "Khu KTX lớn nhất ĐHQG với hơn 40.000 sinh viên. Lưu lượng di chuyển lớn sang các trường thành viên.",
        "capacity_slots": 60,
        "capacity_chargers": 20,
        "grid_power_limit_kw": 120.0,
        "initial_ebikes": 22,
        "initial_escooters": 18,
        "initial_personal_slots_occupied": 15,
    },
    {
        "id": "HUB_BK_KHTN",
        "code": "BKHT-04",
        "name": "Hub Cụm ĐH Bách Khoa & KHTN",
        "category": "Academic Hub",
        "latitude": 10.8808,
        "longitude": 106.8055,
        "description": "Cụm Giảng đường ĐH Bách Khoa CS2 & ĐH Khoa học Tự nhiên CS2. Nhu cầu đỗ xe giờ học và trả xe giữa ca.",
        "capacity_slots": 45,
        "capacity_chargers": 10,
        "grid_power_limit_kw": 70.0,
        "initial_ebikes": 10,
        "initial_escooters": 10,
        "initial_personal_slots_occupied": 10,
    },
    {
        "id": "HUB_UIT_IU",
        "code": "UITIU-05",
        "name": "Hub Cụm ĐH CNTT (UIT) & Quốc Tế (IU)",
        "category": "Academic Hub",
        "latitude": 10.8702,
        "longitude": 106.8030,
        "description": "Cụm ĐH Công nghệ Thông tin (UIT) và ĐH Quốc tế (IU). Mật độ sinh viên công nghệ sử dụng phương tiện xanh cao.",
        "capacity_slots": 45,
        "capacity_chargers": 12,
        "grid_power_limit_kw": 80.0,
        "initial_ebikes": 12,
        "initial_escooters": 10,
        "initial_personal_slots_occupied": 8,
    },
    {
        "id": "HUB_LIB_NVHSV",
        "code": "LIBNVH-06",
        "name": "Hub Thư viện TT & NVH Sinh viên",
        "category": "Amenity Hub",
        "latitude": 10.8755,
        "longitude": 106.8078,
        "description": "Khu phức hợp Thư viện Trung tâm và Nhà văn hóa Sinh viên. Thường diễn ra sự kiện, triển lãm, hoạt động CLB.",
        "capacity_slots": 35,
        "capacity_chargers": 10,
        "grid_power_limit_kw": 65.0,
        "initial_ebikes": 8,
        "initial_escooters": 8,
        "initial_personal_slots_occupied": 6,
    }
]

# Thông số vận hành và biểu phí (VNĐ - hỗ trợ sinh viên ĐHQG)
FEES: Dict[str, Any] = {
    "e_bike_unlock": 0,           # Miễn phí mở khóa xe đạp điện
    "e_bike_per_minute": 150,     # 9.000đ / giờ
    "e_scooter_unlock": 2000,     # Mở khóa xe máy điện 2.000đ
    "e_scooter_per_minute": 300,  # 18.000đ / giờ
    "parking_per_hour": 2000,     # Chỗ đỗ xe cá nhân: 2.000đ / giờ
    "charging_per_kwh": 3500,     # Phí sạc: 3.500đ / kWh
}

# Thông số kỹ thuật cổng sạc
PORT_TYPES = {
    "STANDARD_3_3KW": {
        "name": "Sạc Chuẩn AC (3.3 kW)",
        "power_kw": 3.3,
        "applicable_to": ["E_BIKE", "E_SCOOTER", "PERSONAL_EV"],
        "charge_rate_soc_per_hour": 25.0  # Tăng ~25% SoC / giờ
    },
    "FAST_7_4KW": {
        "name": "Sạc Nhanh AC (7.4 kW)",
        "power_kw": 7.4,
        "applicable_to": ["E_SCOOTER", "PERSONAL_EV"],
        "charge_rate_soc_per_hour": 55.0  # Tăng ~55% SoC / giờ
    },
    "SUPER_11KW": {
        "name": "Sạc Siêu Tốc (11.0 kW)",
        "power_kw": 11.0,
        "applicable_to": ["E_SCOOTER", "PERSONAL_EV"],
        "charge_rate_soc_per_hour": 85.0  # Tăng ~85% SoC / giờ
    }
}

# Ngưỡng cảnh báo mạng lưới
ALERT_THRESHOLDS = {
    "vehicle_depletion_min": 3,      # Dưới 3 xe khả dụng -> Cảnh báo thiếu xe
    "slot_congestion_free_max": 2,   # Còn dưới 2 chỗ đỗ trống -> Cảnh báo đầy bãi
    "battery_low_soc": 25.0,         # Pin dưới 25% -> Ưu tiên sạc khẩn cấp
    "hub_overload_ratio": 0.85,      # Tỷ lệ chiếm dụng trên 85% -> Cảnh báo quá tải
}
