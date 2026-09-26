# BÁO CÁO THIẾT KẾ ĐỘNG & SƠ ĐỒ (SUBMISSION #2)
## Smart E-Mobility Hub – Hệ thống Điều phối Phương tiện Điện trong Khu đô thị ĐHQG-HCM

---

## 1. Sơ Đồ Trình Tự (Sequence Diagrams)

### 1.1. Sơ đồ Trình tự: Sinh viên Thuê và Trả xe (Rent & Return Vehicle)

```mermaid
sequenceDiagram
    autonumber
    actor Student as Sinh Viên
    participant UI as Giao Diện Web / App
    participant BS as BookingService
    participant HS as HubService
    participant SS as SmartScheduler

    Student->>UI: Chọn Hub xuất phát, loại xe (E-Bike) & Hub đích
    UI->>BS: rent_vehicle(userId, originHub, vType, destHub)
    BS->>HS: get_hub_by_id(originHub)
    HS-->>BS: Hub object (kèm danh sách xe, slots, ports)
    
    alt Hub còn xe khả dụng
        BS->>HS: Tìm xe có mức pin SoC cao nhất >= 20%
        BS->>BS: Tạo Booking (ACTIVE) & Trip (IN_PROGRESS)
        BS->>HS: Giải phóng vị trí đỗ tại Hub xuất phát
        BS-->>UI: Mở khóa xe thành công (Mã xe, % Pin, Mã chuyến)
        UI-->>Student: Thông báo xe đã mở khóa, bắt đầu hành trình
    else Hub hết xe
        BS->>HS: get_fallback_hub(originHub, "vehicle")
        HS-->>BS: Fallback Hub gần nhất (khoảng cách, số xe)
        BS-->>UI: Cảnh báo hết xe & gợi ý Fallback Hub
        UI-->>Student: Hiển thị trạm lân cận thay thế
    end

    Note over Student, UI: Sinh viên di chuyển đến Hub đích...

    Student->>UI: Bấm "Trả xe" tại Hub đích
    UI->>BS: return_vehicle(tripId, destHub, duration)
    BS->>HS: Kiểm tra vị trí đỗ trống tại destHub
    BS->>BS: Tính cước phí sinh viên, quãng đường, tiêu hao % pin
    BS->>HS: Gán xe vào vị trí đỗ tại destHub
    
    opt Nếu mức pin sau chuyến đi < 25%
        BS->>SS: enqueue_charging_request(destHub, vehicleId, priority)
    end
    
    BS-->>UI: Trả xe thành công (Cước phí, Quãng đường, Pin còn lại)
    UI-->>Student: Thông báo kết thúc chuyến đi và hóa đơn
```

---

### 1.2. Sơ đồ Trình tự: Lập lịch Sạc thông minh (Smart Charging Scheduling)

```mermaid
sequenceDiagram
    autonumber
    actor User as Sinh Viên / Xe Cần Sạc
    participant SS as SmartScheduler
    participant HS as HubService
    participant Port as Cổng Sạc
    participant Grid as Lưới Điện Hub

    User->>SS: enqueue_charging_request(hubId, vehicleId, targetSoc, minutesUntilNeeded)
    SS->>SS: calculate_priority_score(SoC, minutesUntilNeeded, isSharedFleet)
    SS->>SS: Chèn vào hàng đợi ưu tiên (Priority Queue) theo thứ tự giảm dần
    
    SS->>HS: Lấy thông tin trạm sạc và công suất tải hiện tại
    HS-->>SS: Grid limit (kW) & Current power draw (kW)
    
    loop Duyệt từng yêu cầu trong hàng đợi
        SS->>HS: Tìm cổng sạc khả dụng có công suất phù hợp
        alt Cổng rảnh & Tổng công suất + Port.power <= Grid.limit
            SS->>Port: Chuyển trạng thái sang CHARGING
            SS->>SS: Tạo ChargingSession (Gán xe vào cổng)
            SS->>Grid: Tăng công suất phụ tải trạm
        else Vượt quá công suất lưới điện
            Note over SS: Giữ yêu cầu trong hàng đợi chờ đợt sau (tránh quá tải)
        end
    end
```

---

### 1.3. Sơ đồ Trình tự: Điều phối Cân bằng Phương tiện (Vehicle Rebalancing)

```mermaid
sequenceDiagram
    autonumber
    actor Operator as Nhân Viên Vận Hành
    participant RS as RebalanceService
    participant HS as HubService

    Operator->>RS: analyze_network_balance()
    RS->>HS: Lấy số lượng xe sẵn sàng tại 6 Hubs
    HS-->>RS: Dữ liệu xe và sức chứa từng Hub
    RS->>RS: Tính delta_i = Current_i - Target_i
    RS->>RS: Phân loại Surplus Hubs (thừa xe) & Deficit Hubs (thiếu xe)
    RS-->>Operator: Hiển thị báo cáo mất cân bằng tải

    Operator->>RS: generate_rebalance_plan()
    RS->>RS: Ghép cặp Surplus - Deficit tối ưu khoảng cách Haversine
    RS-->>Operator: Danh sách lệnh điều chuyển đề xuất
    
    Operator->>RS: execute_all_recommended_plans()
    loop Với từng lệnh điều chuyển
        RS->>HS: Rút xe khỏi Hub thừa & giải phóng slot
        RS->>HS: Đưa xe vào Hub thiếu & chiếm slot trống
    end
    RS-->>Operator: Thông báo hoàn tất điều chuyển toàn mạng lưới
```

---

## 2. Sơ Đồ Hoạt Động (Activity Diagrams)

### 2.1. Sơ đồ Hoạt động: Quy trình Đặt xe & Điều hướng Fallback

```mermaid
flowchart TD
    Start([Bắt đầu]) --> InputChoice[Sinh viên chọn Hub xuất phát và Loại xe]
    InputChoice --> CheckAvail{Hub xuất phát<br/>còn xe khả dụng?}
    
    CheckAvail -- Có --> SelectBest[Chọn xe có % pin cao nhất >= 20%]
    SelectBest --> CheckDest{Có chọn Hub đích trước không?}
    
    CheckDest -- Có --> CheckDestSlot{Hub đích còn<br/>chỗ đỗ trống?}
    CheckDestSlot -- Hết --> WarnDest[Cảnh báo Hub đích đầy bãi & gợi ý trạm lân cận]
    CheckDestSlot -- Còn --> Unlock[Mở khóa xe]
    CheckDest -- Không --> Unlock
    WarnDest --> Unlock
    
    CheckAvail -- Hết --> FindFallback[Gọi thuật toán tìm Hub thay thế gần nhất]
    FindFallback --> ShowFallback[Hiển thị trạm thay thế & khoảng cách di chuyển]
    ShowFallback --> AcceptFallback{Sinh viên đồng ý<br/>chuyển Hub?}
    AcceptFallback -- Có --> ChangeHub[Đổi Hub xuất phát sang Hub gợi ý] --> CheckAvail
    AcceptFallback -- Không --> EndFail([Kết thúc: Hủy yêu cầu])
    
    Unlock --> StartTrip[Khởi tạo chuyến đi và ghi nhận thời gian bắt đầu]
    StartTrip --> Moving[Sinh viên đang di chuyển...]
    Moving --> ReturnAtDest[Đến Hub trả xe]
    ReturnAtDest --> CheckReturnSlot{Hub trả xe<br/>còn chỗ đỗ?}
    
    CheckReturnSlot -- Còn --> ParkCar[Đỗ xe vào vị trí trống]
    CheckReturnSlot -- Hết --> AutoFallbackDest[Tự động điều hướng sang Hub dự phòng kế cận] --> ParkCar
    
    ParkCar --> CalcCost[Tính toán thời gian, cước phí và tiêu hao pin]
    CalcCost --> CheckBattery{Mức pin còn lại < 25%?}
    CheckBattery -- Có --> AutoQueueCharge[Đưa xe vào hàng đợi sạc thông minh]
    CheckBattery -- Không --> MarkAvail[Chuyển trạng thái xe sang SẴN SÀNG]
    AutoQueueCharge --> EndSuccess([Kết thúc chuyến đi])
    MarkAvail --> EndSuccess
```

---

## 3. Sơ Đồ Trạng Thái (State-Chart Diagrams - Bonus)

### 3.1. Sơ đồ Trạng thái Phương tiện điện (Vehicle Lifecycle Statechart)

```mermaid
stateDiagram-v2
    [*] --> AVAILABLE: Nhập đội xe vào Hub
    
    AVAILABLE --> RESERVED: Sinh viên đặt trước
    RESERVED --> IN_USE: Mở khóa xe thành công
    AVAILABLE --> IN_USE: Mở khóa trực tiếp tại trạm
    
    IN_USE --> AVAILABLE: Trả xe tại Hub (SoC >= 25%)
    IN_USE --> WAITING_CHARGE: Trả xe tại Hub (SoC < 25%)
    
    AVAILABLE --> WAITING_CHARGE: Nhân viên đưa vào hàng đợi sạc
    WAITING_CHARGE --> CHARGING: Cổng sạc tiếp nhận cấp điện
    CHARGING --> AVAILABLE: Pin nạp đầy 100% (Tự động ngắt)
    
    AVAILABLE --> MAINTENANCE: Lịch bảo dưỡng định kỳ
    MAINTENANCE --> AVAILABLE: Hoàn tất bảo dưỡng
    
    AVAILABLE --> FAULTY: Phát hiện hỏng hóc kỹ thuật
    CHARGING --> FAULTY: Sự cố chập điện / quá nhiệt
    FAULTY --> MAINTENANCE: Kỹ thuật viên tiếp nhận xử lý
```

### 3.2. Sơ đồ Trạng thái Cổng sạc điện (Charging Port Statechart)

```mermaid
stateDiagram-v2
    [*] --> AVAILABLE: Kích hoạt trạm sạc
    
    AVAILABLE --> RESERVED: Lên lịch giữ chỗ cổng sạc
    RESERVED --> CHARGING: Phương tiện cắm sạc
    AVAILABLE --> CHARGING: Gán xe ưu tiên vào sạc ngay
    
    CHARGING --> AVAILABLE: Hoàn tất nạp điện & rút phích cắm
    CHARGING --> FAULTY: Cháy cầu chì / Quá tải / Báo lỗi
    AVAILABLE --> FAULTY: Cảm biến báo đứt kết nối
    
    FAULTY --> MAINTENANCE: Kỹ thuật viên bảo trì
    MAINTENANCE --> AVAILABLE: Kiểm định an toàn thành công
```
