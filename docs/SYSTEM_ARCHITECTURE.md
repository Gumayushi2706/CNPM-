# KIẾN TRÚC TỔNG THỂ HỆ THỐNG SMART E-MOBILITY HUB
## Khu Đô Thị Đại Học Quốc Gia TP. Hồ Chí Minh (ĐHQG-HCM)

---

## 1. Mục Tiêu & Nguyên Lý Thiết Kế

Hệ thống được thiết kế hướng tới giải quyết bài toán giao thông vi mô (micro-mobility) xanh, thông minh trong khuôn viên Đại học Quốc gia TP.HCM. Các nguyên lý thiết kế then chốt:

1. **Kiến trúc Hướng Dịch vụ & Hướng Thực thể (Domain-Driven & Service-Oriented)**:
   - Các thực thể cốt lõi (`Hub`, `Vehicle`, `ChargingPort`, `ParkingSlot`, `Booking`, `Trip`, `Incident`) được thiết kế độc lập, đóng gói đầy đủ trạng thái và hành vi.
   - Các dịch vụ xử lý logic phân tách rõ ràng: quản lý hạ tầng (`HubService`), luồng người dùng (`BookingService`), điều khiển sạc thông minh (`SmartChargingScheduler`), cân bằng mạng lưới (`RebalanceService`), xử lý lỗi (`IncidentService`) và mô phỏng thực nghiệm (`SimulationEngine`).

2. **Thuật toán Thông minh & Tối ưu hóa Thực tế**:
   - **Định vị & Khoảng cách Địa lý (Haversine Distance Formula)**: Tính toán chính xác khoảng cách giữa các trường thành viên và KTX trong ĐHQG-HCM.
   - **Điều phối Cân bằng Tải (Greedy Nearest-Pair Rebalancing)**: Tự động ghép cặp các Hub thâm hụt và dư thừa để giảm thiểu thời gian và năng lượng của đội xe trung chuyển.
   - **Lập lịch Sạc Đa Tiêu chí (Multi-Criteria Priority Scheduling)**: Đánh giá theo State of Charge (SoC), thời gian cần sử dụng xe và kiểm soát ngưỡng công suất điện trạm (Dynamic Load Balancing).

3. **Giao diện Trực quan & Dễ Trình Diễn (High Visual Appeal & Usability)**:
   - Tích hợp Bản đồ Leaflet tương tác thực tế khu ĐHQG-HCM (Linh Trung, Thủ Đức / Dĩ An).
   - Đồ thị Chart.js phản ánh diễn tiến phụ tải và nhu cầu theo thời gian thực.
   - Hệ thống thông báo Toast trực quan, hỗ trợ chế độ Dark Mode hiện đại.

---

## 2. Bản Đồ Mạng Lưới 6 Mobility Hubs

| Mã Hub | Tên Trạm | Tọa độ GPS | Sức chứa Xe / Chỗ đỗ | Cổng sạc | Công suất trạm | Đặc điểm vận hành |
| :--- | :--- | :--- | :---: | :---: | :---: | :--- |
| `HUB_METRO` | **Ga Metro ĐHQG** | 10.8752, 106.8005 | 26 xe / 40 slots | 12 cổng | 80 kW | Cửa ngõ Metro số 1. Nhu cầu xe đỉnh điểm giờ cao điểm sáng/chiều. |
| `HUB_KTX_A` | **KTX Khu A ĐHQG** | 10.8785, 106.8062 | 32 xe / 50 slots | 16 cổng | 100 kW | Cụm KTX Khu A & Sân vận động. Nhu cầu lấy xe buổi sáng, sạc ban đêm. |
| `HUB_KTX_B` | **KTX Khu B ĐHQG** | 10.8838, 106.7825 | 40 xe / 60 slots | 20 cổng | 120 kW | KTX lớn nhất (40.000 sinh viên). Điểm xuất phát lớn nhất toàn khu đô thị. |
| `HUB_BK_KHTN` | **Cụm ĐH Bách Khoa & KHTN** | 10.8808, 106.8055 | 20 xe / 45 slots | 10 cổng | 70 kW | Giảng đường chính. Nhu cầu đỗ xe giờ học và trả xe giữa ca. |
| `HUB_UIT_IU` | **Cụm ĐH CNTT (UIT) & Quốc Tế**| 10.8702, 106.8030 | 22 xe / 45 slots | 12 cổng | 80 kW | Cụm sinh viên công nghệ, mật độ sử dụng xe điện vi mô rất cao. |
| `HUB_LIB_NVHSV`| **Thư viện TT & NVH Sinh viên** | 10.8755, 106.8078 | 16 xe / 35 slots | 10 cổng | 65 kW | Khu phức hợp văn hóa, sự kiện, triển lãm. Dễ phát sinh dồn ứ xe đột biến. |

---

## 3. Quy Trình Chạy Mô Phỏng Kịch Bản What-if

```
[Chọn Kịch bản] ➔ [Cấu hình Hệ số Tải & Tùy chọn] ➔ [Chạy Mô phỏng 12 Ticks]
                                                            │
         ┌──────────────────────────────────────────────────┴──────────────────────────────────────────────────┐
         ▼                                                  ▼                                                  ▼
[Đo Lường Nhu Cầu]                                [Lập Lịch Sạc Thông Minh]                             [Điều Phối Tái Cân Bằng]
Sinh viên đổ về trạm.                              Kiểm soát phụ tải < Grid Limit.                       Phát hiện Hub thiếu / thừa.
Xử lý thuê/trả & Fallback.                        Ưu tiên xe cạn pin & giờ gấp.                         Điều xe trung chuyển tăng viện.
         │                                                  │                                                  │
         └──────────────────────────────────────────────────┬──────────────────────────────────────────────────┘
                                                            ▼
                                           [Báo Cáo Tổng Hợp & Đánh Giá KPIs]
                                           - Tỷ lệ phục vụ (% Service Level)
                                           - Thời gian chờ trung bình (phút)
                                           - Đỉnh công suất điện lưới (kW)
                                           - Khuyến nghị chiến lược vận hành
```
