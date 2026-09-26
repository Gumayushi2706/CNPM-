# Smart E-Mobility Hub – Hệ thống Điều phối Phương tiện Điện trong Khu đô thị ĐHQG-HCM

> Dự án đồ án môn học Công nghệ Phần mềm: Xây dựng hệ thống điều phối mạng lưới phương tiện điện (E-Bike, E-Scooter, Xe cá nhân), trạm sạc thông minh và mô phỏng kịch bản vận hành What-if trong Khu đô thị ĐHQG-HCM.

---

## 🌟 Giới Thiệu & Bối Cảnh Dự Án

Khu đô thị Đại học Quốc gia TP.HCM (ĐHQG-HCM) có diện tích hơn 643 hecta với hơn 90.000 sinh viên, giảng viên phân bổ tại nhiều trường thành viên (Bách Khoa, KHTN, KHXH&NV, Quốc Tế, CNTT - UIT, Kinh tế - Luật), các cụm Ký túc xá (Khu A, Khu B), Nhà văn hóa Sinh viên, Thư viện Trung tâm và Ga Metro số 1 (Ga ĐHQG).

Hệ thống **Smart E-Mobility Hub** giải quyết bài toán:
1. **Quản lý mạng lưới 6 Mobility Hubs**: Theo dõi vị trí đỗ, cổng sạc đa công suất (3.3kW, 7.4kW, 11kW), tình trạng xe và mức pin gần thời gian thực.
2. **Phân hệ Sinh viên (Student Portal)**: Tìm kiếm xe, đặt xe, mở khóa nhận xe, trả xe tự động tính cước sinh viên, đặt chỗ đỗ & đăng ký sạc xe cá nhân, tự động điều hướng sang Hub thay thế khi hết chỗ.
3. **Phân hệ Vận hành (Operator Dashboard)**: Giám sát toàn mạng lưới, bản đồ nhiệt thời gian thực, cảnh báo quá tải/cạn kiệt xe, **Thuật toán điều phối cân bằng xe (Rebalancing)** giữa các Hub, và **Thuật toán lập lịch sạc thông minh (Smart Charging Scheduler)** ưu tiên SoC thấp, kiểm soát đỉnh tải trạm điện.
4. **Bộ máy Mô phỏng Kịch bản (What-if Simulation Engine)**: Thử nghiệm 5 kịch bản khắc nghiệt (Giờ cao điểm ga Metro, Cạn kiệt Hub, Quá tải sạc, Hỏng hàng loạt cổng sạc, Dồn ứ xe sự kiện) kèm xuất báo cáo KPI và khuyến nghị điều phối tự động.

---

## 🚀 Hướng Dẫn Khởi Chạy Trên Ổ D:

Hệ thống được thiết kế hoàn chỉnh để chạy trực tiếp trên **ổ D:** (`D:\smart_emobility_hub`) với môi trường Python:

### Cáách 1: Khởi chạy bằng lệnh Python trong Terminal / PowerShell
```powershell
cd D:\smart_emobility_hub
python run.py
```
Sau đó mở trình duyệt tại:
- **Giao diện Dashboard trực quan:** [http://localhost:8000](http://localhost:8000)
- **Tài liệu API Swagger tương tác:** [http://localhost:8000/docs](http://localhost:8000/docs)

### Cách 2: Chạy thử nghiệm qua CLI (Dòng lệnh)
```powershell
cd D:\smart_emobility_hub
python demo_cli.py
```

### Chạy Kiểm Thử Tự Động (Unit Tests)
```powershell
cd D:\smart_emobility_hub
python -m pytest tests/ -v
```

---

## 📁 Cấu Trúc Thư Mục Dự Án

```
D:\smart_emobility_hub\
├── app/
│   ├── __init__.py
│   ├── config.py                 # Tọa độ 6 Hub ĐHQG-HCM, thông số kỹ thuật, biểu phí
│   ├── main.py                   # FastAPI application & các REST API endpoints
│   ├── models/                   # Lớp thực thể dữ liệu (Domain Models)
│   │   ├── __init__.py
│   │   ├── hub.py                # Hub, ParkingSlot, ChargingPort
│   │   ├── vehicle.py            # Vehicle, VehicleType, VehicleStatus
│   │   ├── booking.py            # Booking, Trip, ChargingSession
│   │   ├── incident.py           # Incident, IncidentSeverity, IncidentStatus
│   │   └── simulation.py         # Kịch bản What-if, SimulationConfig, SimulationSummary
│   ├── services/                 # Lớp nghiệp vụ & Thuật toán (Business Logic)
│   │   ├── __init__.py
│   │   ├── hub_service.py        # Quản lý 6 Hubs, tính khoảng cách GPS Haversine, Fallback Hub
│   │   ├── booking_service.py    # Đặt xe, nhận xe, trả xe, đặt chỗ đỗ cá nhân, tính cước
│   │   ├── smart_scheduler.py    # Lập lịch sạc thông minh đa tiêu chí, bảo vệ lưới điện
│   │   ├── rebalance_service.py  # Thuật toán phân tích thâm hụt/dư thừa & điều phối xe
│   │   ├── incident_service.py   # Quản lý sự cố, cô lập trạm sạc hỏng, chuyển mạch tự động
│   │   └── simulation_engine.py  # Bộ máy mô phỏng What-if 5 kịch bản & đo lường KPIs
│   └── web/                      # Giao diện Web SPA hiện đại
│       ├── static/
│       │   ├── css/style.css     # Glassmorphism, Dark modern UI, responsive
│       │   └── js/app.js         # Leaflet Map ĐHQG, Chart.js KPI, tương tác thời gian thực
│       └── templates/
│           └── index.html        # Giao diện chính tích hợp 3 phân hệ
├── tests/                        # Bộ kiểm thử tự động
│   ├── test_models.py
│   ├── test_smart_scheduler.py
│   ├── test_rebalance.py
│   └── test_simulation.py
├── run.py                        # Script khởi chạy web server
├── demo_cli.py                   # Script chạy demo trên console
└── README.md                     # Hướng dẫn chi tiết dự án
```
---

## 👥 Danh Sách 6 Mobility Hubs Chiến Lược

1. **Hub Ga Metro ĐHQG** (`HUB_METRO`): Cửa ngõ đón sinh viên từ Metro số 1 Bến Thành - Suối Tiên.
2. **Hub KTX Khu A** (`HUB_KTX_A`): Cụm KTX Khu A & Sân vận động ĐHQG.
3. **Hub KTX Khu B** (`HUB_KTX_B`): Cụm KTX lớn nhất với hơn 40.000 sinh viên.
4. **Hub Cụm BK - KHTN** (`HUB_BK_KHTN`): Cụm giảng đường ĐH Bách Khoa CS2 & ĐH KHTN CS2.
5. **Hub Cụm UIT - IU** (`HUB_UIT_IU`): Cụm ĐH Công nghệ Thông tin & ĐH Quốc tế.
6. **Hub Thư viện TT & NVHSV** (`HUB_LIB_NVHSV`): Nhà văn hóa Sinh viên & Thư viện Trung tâm ĐHQG.
