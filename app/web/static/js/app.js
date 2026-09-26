// Smart E-Mobility Hub - Client Application Logic
let map = null;
let markers = {};
let currentActiveTrip = null;
let simChart = null;

// Tọa độ trung tâm Khu đô thị ĐHQG-HCM
const VNU_CENTER = [10.8765, 106.7985];

// Mô tả các kịch bản What-if
const SCENARIO_DESCS = {
  "METRO_RUSH_HOUR": "Lượng lớn sinh viên cập bến Ga Metro lúc cao điểm sáng, cần ngay phương tiện sang các trường thành viên.",
  "HUB_EXHAUSTION": "KTX Khu B cạn kiệt xe đạp điện hoặc bãi đỗ bị lấp đầy 100%, kiểm tra phản ứng điều hướng tự động.",
  "CHARGING_SPIKE": "Hơn 30 xe cùng cắm sạc giờ trưa/tối, kiểm tra thuật toán lập lịch sạc tránh sập nguồn trạm.",
  "PORT_BREAKDOWN": "Cổng sạc bị sự cố cháy cầu chì, hệ thống tự động cô lập và chuyển xe sang cổng dự phòng.",
  "CLUSTER_IMBALANCE": "Sự kiện lớn tại NVH Sinh viên khiến hàng trăm xe dồn ứ, kiểm tra cơ chế gom xe giải tỏa bãi đỗ."
};

document.addEventListener("DOMContentLoaded", () => {
  initMap();
  loadNetworkData();
  loadHubs();
  loadUserTrips();
  onScenarioChange();

  // Tự động làm mới dữ liệu định kỳ mỗi 15 giây
  setInterval(() => {
    loadNetworkData();
    loadHubs(false);
  }, 15000);
});

// ==========================================
// BẢN ĐỒ TƯƠNG TÁC (LEAFLET MAP)
// ==========================================
function initMap() {
  const mapElement = document.getElementById("map");
  if (!mapElement) return;

  map = L.map("map").setView(VNU_CENTER, 14);

  // Bản đồ nền CartoDB Dark Matter đẹp hiện đại
  L.tileLayer("https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png", {
    attribution: '&copy; <a href="https://carto.com/">CARTO</a> | ĐHQG-HCM Smart Mobility',
    maxZoom: 19
  }).addTo(map);
}

function updateMapMarkers(hubs) {
  if (!map) return;

  hubs.forEach(hub => {
    const isOverloaded = hub.alerts && hub.alerts.length > 0;
    const markerColor = isOverloaded ? "#f43f5e" : "#06b6d4";

    const customIcon = L.divIcon({
      className: "custom-hub-pin",
      html: `
        <div style="background: ${markerColor}; color: white; width: 34px; height: 34px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 11px; box-shadow: 0 0 15px ${markerColor}; border: 2px solid white;">
          ${hub.available_vehicles_count}
        </div>
      `,
      iconSize: [34, 34],
      iconAnchor: [17, 17]
    });

    const popupContent = `
      <div style="min-width: 220px; font-family: 'Outfit', sans-serif;">
        <h4 style="margin: 0 0 6px 0; color: #38bdf8; font-size: 14px;">${hub.name}</h4>
        <p style="margin: 0 0 8px 0; font-size: 11px; color: #94a3b8;">${hub.description}</p>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px; font-size: 11px;">
          <div>🚲 Xe sẵn sàng: <strong>${hub.available_vehicles_count}</strong></div>
          <div>🅿️ Chỗ đỗ trống: <strong>${hub.available_slots_count}</strong></div>
          <div>⚡ Cổng sạc rảnh: <strong>${hub.available_ports_count}</strong></div>
          <div>🔌 Phụ tải: <strong>${hub.current_power_draw_kw} kW</strong></div>
        </div>
        ${isOverloaded ? `<div style="margin-top: 8px; color: #fb7185; font-size: 11px; font-weight: 600;">⚠️ ${hub.alerts[0]}</div>` : ''}
        <button onclick="selectHubForRent('${hub.id}')" style="margin-top: 10px; width: 100%; padding: 6px; background: #0284c7; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 11px; font-weight: 600;">
          Lấy xe tại Hub này
        </button>
      </div>
    `;

    if (markers[hub.id]) {
      markers[hub.id].setLatLng([hub.latitude, hub.longitude]);
      markers[hub.id].setIcon(customIcon);
      markers[hub.id].setPopupContent(popupContent);
    } else {
      const marker = L.marker([hub.latitude, hub.longitude], { icon: customIcon }).addTo(map);
      marker.bindPopup(popupContent);
      markers[hub.id] = marker;
    }
  });
}

function selectHubForRent(hubId) {
  switchTab("student");
  const origSelect = document.getElementById("rent-origin-hub");
  if (origSelect) origSelect.value = hubId;
  showToast("info", `Đã chọn điểm lấy xe: ${hubId}`);
}

// ==========================================
// ĐIỀU HƯỚNG TABS
// ==========================================
function switchTab(tabId) {
  document.querySelectorAll(".tab-content").forEach(el => el.style.display = "none");
  document.querySelectorAll(".nav-tab-btn").forEach(el => el.classList.remove("active"));

  const targetTab = document.getElementById(`tab-${tabId}`);
  const targetBtn = document.getElementById(`tab-btn-${tabId}`);

  if (targetTab) targetTab.style.display = "block";
  if (targetBtn) targetBtn.classList.add("active");

  if (tabId === "operator") {
    loadRebalancePlans();
    loadSchedulerStatus();
    loadIncidents();
  }
}

// ==========================================
// DỮ LIỆU TỔNG QUAN MẠNG LƯỚI
// ==========================================
async function loadNetworkData() {
  try {
    const res = await fetch("/api/network/overview");
    const data = await res.json();

    document.getElementById("stat-available-vehicles").innerText = data.vehicles.available;
    document.getElementById("stat-total-vehicles").innerText = `Tổng ${data.vehicles.total} xe (${data.vehicles.in_use} đang chạy)`;

    document.getElementById("stat-available-slots").innerText = data.slots.available;
    document.getElementById("stat-total-slots").innerText = `Tổng ${data.slots.total} vị trí đỗ`;

    document.getElementById("stat-available-ports").innerText = data.ports.available;
    document.getElementById("stat-charging-ports").innerText = `Đang sạc ${data.ports.charging} cổng`;

    document.getElementById("stat-grid-power").innerText = `${data.grid.total_current_power_kw} kW`;
    document.getElementById("stat-grid-ratio").innerText = `Tải trọng ${data.grid.grid_load_ratio}% giới hạn`;

    // Cập nhật danh sách Cảnh Báo
    const alertsContainer = document.getElementById("alerts-container");
    if (alertsContainer) {
      if (data.alerts.length === 0) {
        alertsContainer.innerHTML = `
          <div style="text-align: center; color: var(--accent-emerald); padding: 30px; font-size: 0.9rem;">
            <i class="fa-solid fa-circle-check" style="font-size: 2rem; margin-bottom: 8px;"></i>
            <div>Mạng lưới hoạt động tối ưu. Không có cảnh báo.</div>
          </div>
        `;
      } else {
        alertsContainer.innerHTML = data.alerts.map(a => `
          <div style="background: rgba(244, 63, 94, 0.12); border-left: 3px solid var(--accent-rose); padding: 10px 14px; border-radius: var(--radius-sm); font-size: 0.825rem; color: #fecdd3;">
            <i class="fa-solid fa-triangle-exclamation" style="margin-right: 6px; color: var(--accent-rose);"></i>
            ${a}
          </div>
        `).join("");
      }
    }
  } catch (err) {
    console.error("Lỗi tải tổng quan mạng lưới:", err);
  }
}

// ==========================================
// TẢI DANH SÁCH VÀ CHI TIẾT CÁC HUBS
// ==========================================
async function loadHubs(populateSelects = true) {
  try {
    const res = await fetch("/api/hubs");
    const hubs = await res.json();

    updateMapMarkers(hubs);

    if (populateSelects) {
      const optionsHtml = hubs.map(h => `<option value="${h.id}">${h.name} (${h.available_vehicles_count} xe khả dụng)</option>`).join("");
      const destOptionsHtml = hubs.map(h => `<option value="${h.id}">${h.name} (${h.available_slots_count} chỗ đỗ trống)</option>`).join("");

      ["rent-origin-hub", "park-hub-select", "inc-hub-select"].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.innerHTML = optionsHtml;
      });

      ["rent-destination-hub", "return-destination-select"].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.innerHTML = destOptionsHtml;
      });

      if (document.getElementById("rent-destination-hub")) {
        document.getElementById("rent-destination-hub").selectedIndex = 1;
      }
    }

    // Hiển thị danh sách Hub trong Operator Dashboard
    const cardsContainer = document.getElementById("hub-cards-container");
    if (cardsContainer) {
      cardsContainer.innerHTML = hubs.map(h => `
        <div class="glass-panel" style="padding: 18px; position: relative;">
          <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
            <div>
              <span class="badge badge-cyan" style="font-size: 0.65rem;">${h.category}</span>
              <h4 style="font-size: 1rem; font-weight: 700; color: white; margin-top: 4px;">${h.name}</h4>
            </div>
            <div style="text-align: right;">
              <span style="font-size: 0.75rem; color: var(--text-dim);">${h.code}</span>
            </div>
          </div>

          <p style="font-size: 0.775rem; color: var(--text-muted); margin-bottom: 12px; height: 32px; overflow: hidden;">${h.description}</p>

          <!-- Capacity Bars -->
          <div style="margin-bottom: 8px;">
            <div style="display: flex; justify-content: space-between; font-size: 0.75rem; margin-bottom: 3px;">
              <span>Vị trí đỗ (Slots):</span>
              <span style="font-weight: 600; color: white;">${h.slots_summary.occupied} / ${h.capacity_slots} (${h.slot_utilization_percent}%)</span>
            </div>
            <div style="width: 100%; height: 6px; background: rgba(255,255,255,0.1); border-radius: 3px; overflow: hidden;">
              <div style="width: ${h.slot_utilization_percent}%; height: 100%; background: ${h.slot_utilization_percent > 85 ? 'var(--accent-rose)' : 'var(--accent-emerald)'};"></div>
            </div>
          </div>

          <div style="margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; font-size: 0.75rem; margin-bottom: 3px;">
              <span>Công suất sạc trạm:</span>
              <span style="font-weight: 600; color: white;">${h.current_power_draw_kw} / ${h.grid_power_limit_kw} kW</span>
            </div>
            <div style="width: 100%; height: 6px; background: rgba(255,255,255,0.1); border-radius: 3px; overflow: hidden;">
              <div style="width: ${(h.current_power_draw_kw / h.grid_power_limit_kw) * 100}%; height: 100%; background: var(--accent-cyan);"></div>
            </div>
          </div>

          <!-- Chi tiết nhanh -->
          <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; text-align: center; background: rgba(0,0,0,0.25); padding: 8px; border-radius: var(--radius-sm); font-size: 0.75rem;">
            <div>
              <div style="color: var(--text-dim);">E-Bikes</div>
              <div style="font-weight: 700; color: white;">${h.available_ebikes_count}</div>
            </div>
            <div>
              <div style="color: var(--text-dim);">E-Scooters</div>
              <div style="font-weight: 700; color: white;">${h.available_escooters_count}</div>
            </div>
            <div>
              <div style="color: var(--text-dim);">Cổng sạc rảnh</div>
              <div style="font-weight: 700; color: white;">${h.available_ports_count}</div>
            </div>
          </div>
        </div>
      `).join("");
    }
  } catch (err) {
    console.error("Lỗi tải danh sách Hubs:", err);
  }
}

// ==========================================
// PHÂN HỆ SINH VIÊN (STUDENT ACTIONS)
// ==========================================
async function submitRentVehicle() {
  const userId = document.getElementById("rent-user-id").value;
  const userName = document.getElementById("rent-user-name").value;
  const originHub = document.getElementById("rent-origin-hub").value;
  const vehicleType = document.getElementById("rent-vehicle-type").value;
  const destHub = document.getElementById("rent-destination-hub").value;

  try {
    const res = await fetch("/api/student/rent", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: userId,
        user_name: userName,
        origin_hub_id: originHub,
        vehicle_type: vehicleType,
        destination_hub_id: destHub
      })
    });
    const result = await res.json();

    if (result.success) {
      showToast("success", result.message);
      currentActiveTrip = result.trip;

      // Hiển thị active banner
      document.getElementById("active-trip-banner").style.display = "block";
      document.getElementById("active-trip-vehicle-info").innerText = `${result.vehicle.model_name} (${result.vehicle.plate_number})`;
      document.getElementById("active-trip-origin").innerText = originHub;
      document.getElementById("active-trip-battery").innerText = `${result.vehicle.battery_soc}%`;

      if (destHub) {
        document.getElementById("return-destination-select").value = destHub;
      }

      document.getElementById("rent-fallback-box").style.display = "none";
      loadNetworkData();
      loadHubs(false);
      loadUserTrips();
    } else {
      showToast("error", result.message);
      if (result.fallback_suggestion) {
        const fb = result.fallback_suggestion;
        const fbBox = document.getElementById("rent-fallback-box");
        fbBox.style.display = "block";
        fbBox.innerHTML = `
          <strong>Gợi ý Hub lân cận:</strong> ${fb.message}<br>
          <button class="btn-secondary" onclick="selectHubForRent('${fb.fallback_hub_id}')" style="margin-top: 6px; padding: 4px 10px; font-size: 0.75rem;">
            Chuyển sang ${fb.fallback_hub_name}
          </button>
        `;
      }
    }
  } catch (err) {
    showToast("error", "Lỗi kết nối máy chủ");
  }
}

async function submitReturnVehicle() {
  if (!currentActiveTrip) {
    showToast("warning", "Không có chuyến đi nào đang hoạt động");
    return;
  }

  const destHub = document.getElementById("return-destination-select").value;

  try {
    const res = await fetch("/api/student/return", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        trip_id: currentActiveTrip.id,
        destination_hub_id: destHub,
        duration_minutes: 15.0
      })
    });
    const result = await res.json();

    if (result.success) {
      showToast("success", result.message);
      currentActiveTrip = null;
      document.getElementById("active-trip-banner").style.display = "none";
      loadNetworkData();
      loadHubs(false);
      loadUserTrips();
    } else {
      showToast("error", result.message);
      if (result.fallback_hub) {
        showToast("info", result.fallback_hub.message);
      }
    }
  } catch (err) {
    showToast("error", "Lỗi trả xe");
  }
}

async function submitReserveParking() {
  const plate = document.getElementById("park-plate").value;
  const hubId = document.getElementById("park-hub-select").value;
  const hours = parseFloat(document.getElementById("park-hours").value);
  const needCharge = document.getElementById("park-need-charge").checked;

  try {
    const res = await fetch("/api/student/reserve-parking", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: "SV_PARK_USER",
        user_name: "Sinh viên gửi xe",
        hub_id: hubId,
        vehicle_plate: plate,
        estimated_hours: hours
      })
    });
    const result = await res.json();

    if (result.success) {
      showToast("success", result.message);

      if (needCharge) {
        // Tự động enqueue sạc thông minh
        await fetch("/api/operator/scheduler/enqueue", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            hub_id: hubId,
            vehicle_id: `PERS_${plate}`,
            user_id: "SV_PARK_USER",
            target_soc: 100.0,
            minutes_until_needed: hours * 60,
            is_personal: true
          })
        });
        showToast("info", "Đã thêm xe vào hàng đợi sạc thông minh theo giờ gửi xe.");
      }

      loadNetworkData();
      loadHubs(false);
    } else {
      showToast("error", result.message);
    }
  } catch (err) {
    showToast("error", "Lỗi đặt chỗ");
  }
}

async function loadUserTrips() {
  try {
    const res = await fetch("/api/trips");
    const trips = await res.json();
    const list = document.getElementById("trips-history-list");
    if (!list) return;

    if (trips.length === 0) {
      list.innerHTML = `<div style="text-align: center; color: var(--text-dim); padding: 20px; font-size: 0.85rem;">Chưa có chuyến đi nào hoàn tất.</div>`;
      return;
    }

    list.innerHTML = trips.slice().reverse().map(t => `
      <div style="background: rgba(255,255,255,0.03); border: 1px solid var(--border-color); padding: 10px 14px; border-radius: var(--radius-sm); font-size: 0.8rem;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
          <strong style="color: var(--accent-cyan);">${t.id}</strong>
          <span class="badge ${t.status === 'COMPLETED' ? 'badge-emerald' : 'badge-amber'}">${t.status}</span>
        </div>
        <div style="color: var(--text-muted);">
          Từ: <strong>${t.origin_hub_id}</strong> ➔ Đến: <strong>${t.destination_hub_id || 'Đang di chuyển'}</strong>
        </div>
        <div style="display: flex; justify-content: space-between; margin-top: 4px; color: var(--text-dim); font-size: 0.75rem;">
          <span>Quãng đường: ${t.distance_km} km</span>
          <span>Pin: ${t.start_soc}% ➔ ${t.end_soc}%</span>
          <span style="color: #34d399; font-weight: 600;">${t.fare.toLocaleString('vi-VN')} VNĐ</span>
        </div>
      </div>
    `).join("");
  } catch (err) {
    console.error("Lỗi tải lịch sử trips:", err);
  }
}

// ==========================================
// PHÂN HỆ VẬN HÀNH (OPERATOR ACTIONS)
// ==========================================
async function loadRebalancePlans() {
  try {
    const analysisRes = await fetch("/api/operator/rebalance/analysis");
    const analysis = await analysisRes.json();

    const plansRes = await fetch("/api/operator/rebalance/plans");
    const plans = await plansRes.json();

    const statusBox = document.getElementById("rebalance-status-box");
    if (statusBox) {
      const surplusNames = analysis.surplus_hubs.map(h => `${h.hub_name} (+${h.delta})`).join(", ") || "Không có";
      const deficitNames = analysis.deficit_hubs.map(h => `${h.hub_name} (${h.delta})`).join(", ") || "Không có";

      statusBox.innerHTML = `
        <div style="margin-bottom: 4px;">📈 <strong>Hub Dư Thừa:</strong> ${surplusNames}</div>
        <div>📉 <strong>Hub Thiếu Hụt:</strong> ${deficitNames}</div>
      `;
    }

    const plansList = document.getElementById("rebalance-plans-list");
    if (plansList) {
      if (plans.length === 0) {
        plansList.innerHTML = `<div style="color: var(--accent-emerald); padding: 12px; font-size: 0.85rem;">Mạng lưới hiện tại đang ở trạng thái cân bằng tốt.</div>`;
      } else {
        plansList.innerHTML = plans.map(p => `
          <div style="background: rgba(255,255,255,0.03); border: 1px solid var(--border-color); padding: 8px 12px; border-radius: var(--radius-sm); display: flex; justify-content: space-between; align-items: center;">
            <div>
              <div style="font-weight: 600; color: white;">${p.from_hub_name} ➔ ${p.to_hub_name}</div>
              <div style="font-size: 0.75rem; color: var(--text-dim);">${p.quantity} xe • ${p.distance_km} km (~${p.estimated_minutes} phút)</div>
            </div>
            <button class="btn-secondary" onclick="executeSingleRebalance('${p.from_hub_id}', '${p.to_hub_id}', ${p.quantity})" style="padding: 4px 8px; font-size: 0.75rem;">
              Thực thi
            </button>
          </div>
        `).join("");
      }
    }
  } catch (err) {
    console.error("Lỗi tải kế hoạch rebalance:", err);
  }
}

async function executeSingleRebalance(fromHub, toHub, qty) {
  try {
    const res = await fetch("/api/operator/rebalance/execute", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ from_hub_id: fromHub, to_hub_id: toHub, quantity: qty })
    });
    const result = await res.json();
    if (result.success) {
      showToast("success", result.message);
      loadRebalancePlans();
      loadHubs(false);
      loadNetworkData();
    }
  } catch (err) {
    showToast("error", "Lỗi điều chuyển");
  }
}

async function executeAutoRebalance() {
  try {
    const res = await fetch("/api/operator/rebalance/execute-all", { method: "POST" });
    const result = await res.json();
    showToast("success", `Đã thực thi thành công ${result.executed_transfers_count} lệnh điều phối (${result.total_vehicles_moved} xe)!`);
    loadRebalancePlans();
    loadHubs(false);
    loadNetworkData();
  } catch (err) {
    showToast("error", "Lỗi thực thi điều phối tự động");
  }
}

async function loadSchedulerStatus() {
  try {
    const res = await fetch("/api/operator/scheduler/status");
    const data = await res.json();

    const statusBox = document.getElementById("scheduler-status-box");
    if (statusBox) {
      statusBox.innerHTML = `
        <span>Đang sạc tích cực: <strong>${data.active_charging_count} xe</strong></span> | 
        <span>Xe chờ xếp lịch: <strong>${data.total_vehicles_waiting} xe</strong></span>
      `;
    }

    const list = document.getElementById("scheduler-sessions-list");
    if (list) {
      if (data.active_sessions.length === 0) {
        list.innerHTML = `<div style="color: var(--text-dim); padding: 12px; font-size: 0.85rem;">Không có phiên sạc nào đang chạy.</div>`;
      } else {
        list.innerHTML = data.active_sessions.map(s => `
          <div style="background: rgba(16, 185, 129, 0.08); border-left: 3px solid var(--accent-emerald); padding: 8px 12px; border-radius: var(--radius-sm); font-size: 0.8rem; display: flex; justify-content: space-between;">
            <div>
              <strong>Xe ${s.vehicle_id}</strong> (${s.power_kw} kW tại ${s.hub_id})
              <div style="color: var(--text-dim); font-size: 0.75rem;">Điểm ưu tiên: ${s.priority_score} • Điện nạp: ${s.energy_consumed_kwh} kWh</div>
            </div>
            <div style="text-align: right;">
              <span style="color: #34d399; font-weight: 700;">${s.current_soc}%</span> / ${s.target_soc}%
            </div>
          </div>
        `).join("");
      }
    }
  } catch (err) {
    console.error("Lỗi tải scheduler status:", err);
  }
}

async function stepChargingScheduler() {
  try {
    const res = await fetch("/api/operator/scheduler/step?minutes=15", { method: "POST" });
    const result = await res.json();
    showToast("info", `Đã mô phỏng tiến trình sạc +15 phút. Số xe sạc đầy: ${result.completed_count}`);
    loadSchedulerStatus();
    loadHubs(false);
    loadNetworkData();
  } catch (err) {
    showToast("error", "Lỗi mô phỏng bước sạc");
  }
}

async function loadIncidents() {
  try {
    const res = await fetch("/api/incidents");
    const incidents = await res.json();

    const list = document.getElementById("incidents-list-container");
    if (!list) return;

    if (incidents.length === 0) {
      list.innerHTML = `<div style="text-align: center; color: var(--accent-emerald); padding: 20px; font-size: 0.85rem;">Không có sự cố nào được ghi nhận. Hệ thống an toàn!</div>`;
      return;
    }

    list.innerHTML = incidents.slice().reverse().map(inc => `
      <div style="background: rgba(255,255,255,0.03); border: 1px solid var(--border-color); padding: 12px; border-radius: var(--radius-sm); font-size: 0.825rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
          <div>
            <span class="badge ${inc.severity === 'CRITICAL' ? 'badge-rose' : 'badge-amber'}">${inc.severity}</span>
            <strong style="color: white; margin-left: 6px;">${inc.entity_type}: ${inc.entity_id}</strong>
          </div>
          <span class="badge ${inc.status === 'ACTIVE' ? 'badge-rose' : 'badge-emerald'}">${inc.status}</span>
        </div>
        <p style="color: var(--text-muted); margin: 4px 0;">${inc.description}</p>
        <div style="font-size: 0.75rem; color: var(--accent-cyan); margin-bottom: 6px;">
          <i class="fa-solid fa-shield-halved"></i> ${inc.action_taken}
        </div>
        ${inc.status === 'ACTIVE' ? `
          <button class="btn-secondary" onclick="resolveIncident('${inc.id}')" style="padding: 4px 8px; font-size: 0.75rem; border-color: #10b981; color: #10b981;">
            <i class="fa-solid fa-check"></i> Đánh dấu đã sửa xong
          </button>
        ` : ''}
      </div>
    `).join("");
  } catch (err) {
    console.error("Lỗi tải incidents:", err);
  }
}

async function submitIncidentReport() {
  const hubId = document.getElementById("inc-hub-select").value;
  const entityType = document.getElementById("inc-entity-type").value;
  const entityId = document.getElementById("inc-entity-id").value;
  const severity = document.getElementById("inc-severity").value;

  try {
    const res = await fetch("/api/incidents/report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        hub_id: hubId,
        entity_type: entityType,
        entity_id: entityId,
        severity: severity,
        description: `Báo cáo kỹ thuật sự cố ${entityType} tại ${hubId}`
      })
    });
    const result = await res.json();
    if (result.success) {
      showToast("warning", result.message);
      loadIncidents();
      loadHubs(false);
      loadNetworkData();
    }
  } catch (err) {
    showToast("error", "Lỗi báo cáo sự cố");
  }
}

async function resolveIncident(incidentId) {
  try {
    const res = await fetch(`/api/incidents/${incidentId}/resolve`, { method: "POST" });
    const result = await res.json();
    if (result.success) {
      showToast("success", result.message);
      loadIncidents();
      loadHubs(false);
      loadNetworkData();
    }
  } catch (err) {
    showToast("error", "Lỗi giải quyết sự cố");
  }
}

// ==========================================
// PHÂN HỆ MÔ PHỎNG WHAT-IF (SIMULATION LAB)
// ==========================================
function onScenarioChange() {
  const select = document.getElementById("sim-scenario-select");
  const descEl = document.getElementById("sim-scenario-desc");
  if (select && descEl) {
    descEl.innerText = SCENARIO_DESCS[select.value] || "";
  }
}

async function runWhatIfSimulation() {
  const scenarioType = document.getElementById("sim-scenario-select").value;
  const multiplier = parseFloat(document.getElementById("sim-multiplier").value);
  const autoRebalance = document.getElementById("sim-toggle-rebalance").checked;
  const smartCharging = document.getElementById("sim-toggle-smartcharging").checked;

  showToast("info", "Đang chạy mô phỏng kịch bản What-if. Vui lòng chờ...");

  try {
    const res = await fetch("/api/simulation/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        scenario_type: scenarioType,
        duration_ticks: 12,
        student_demand_multiplier: multiplier,
        auto_rebalance: autoRebalance,
        smart_charging: smartCharging
      })
    });
    const summary = await res.json();

    renderSimulationResults(summary);
    showToast("success", `Mô phỏng hoàn tất! Tỷ lệ phục vụ: ${summary.service_level_percent}%`);
  } catch (err) {
    showToast("error", "Lỗi chạy mô phỏng");
  }
}

function renderSimulationResults(summary) {
  document.getElementById("sim-results-wrapper").style.display = "block";

  // Cập nhật KPIs
  document.getElementById("sim-kpi-service-level").innerText = `${summary.service_level_percent}%`;
  document.getElementById("sim-kpi-reqs-sub").innerText = `Đáp ứng ${summary.fulfilled_requests} / ${summary.total_student_requests} yêu cầu`;

  document.getElementById("sim-kpi-wait-time").innerText = `${summary.average_wait_time_minutes} phút`;
  document.getElementById("sim-kpi-rebalanced").innerText = `${summary.total_rebalanced_vehicles} xe`;
  document.getElementById("sim-kpi-peak-grid").innerText = `${summary.peak_grid_load_kw} kW`;

  // Khuyến nghị điều phối AI
  const recList = document.getElementById("sim-recommendations-list");
  if (recList) {
    recList.innerHTML = summary.recommendations.map(r => `
      <div style="background: rgba(6, 182, 212, 0.08); border-left: 3px solid var(--accent-cyan); padding: 10px 14px; border-radius: var(--radius-sm); color: #e0f2fe;">
        <i class="fa-solid fa-lightbulb" style="color: var(--accent-amber); margin-right: 6px;"></i>
        ${r}
      </div>
    `).join("");
  }

  // Bảng diễn tiến Step-by-Step
  const tbody = document.getElementById("sim-steps-tbody");
  if (tbody) {
    tbody.innerHTML = summary.steps.map(s => `
      <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
        <td style="padding: 8px 12px; font-weight: 600; color: white;">${s.time_label}</td>
        <td style="padding: 8px 12px;">${s.requests_generated}</td>
        <td style="padding: 8px 12px; color: #10b981; font-weight: 600;">${s.requests_fulfilled}</td>
        <td style="padding: 8px 12px; color: ${s.requests_unmet > 0 ? '#f43f5e' : 'var(--text-dim)'}; font-weight: 600;">${s.requests_unmet}</td>
        <td style="padding: 8px 12px;">${s.active_trips}</td>
        <td style="padding: 8px 12px;">${s.active_charging_sessions}</td>
        <td style="padding: 8px 12px; color: #818cf8; font-weight: 600;">${s.grid_total_power_kw}</td>
        <td style="padding: 8px 12px; font-size: 0.75rem; color: var(--text-muted);">
          ${s.rebalance_actions.length > 0 ? `Điều phối ${s.rebalance_actions[0].quantity} xe sang ${s.rebalance_actions[0].to_hub_name}` : 'Bình thường'}
        </td>
      </tr>
    `).join("");
  }

  // Vẽ biểu đồ Chart.js
  renderSimulationChart(summary.steps);
}

function renderSimulationChart(steps) {
  const ctx = document.getElementById("simChart").getContext("2d");

  const labels = steps.map(s => s.time_label);
  const requestsData = steps.map(s => s.requests_generated);
  const fulfilledData = steps.map(s => s.requests_fulfilled);
  const gridPowerData = steps.map(s => s.grid_total_power_kw);

  if (simChart) {
    simChart.destroy();
  }

  simChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Nhu cầu Sinh viên",
          data: requestsData,
          borderColor: "#f59e0b",
          backgroundColor: "rgba(245, 158, 11, 0.1)",
          tension: 0.3,
          yAxisID: "y"
        },
        {
          label: "Số yêu cầu đáp ứng",
          data: fulfilledData,
          borderColor: "#10b981",
          backgroundColor: "rgba(16, 185, 129, 0.1)",
          tension: 0.3,
          yAxisID: "y"
        },
        {
          label: "Phụ tải trạm sạc (kW)",
          data: gridPowerData,
          borderColor: "#06b6d4",
          backgroundColor: "rgba(6, 182, 212, 0.1)",
          borderDash: [5, 5],
          tension: 0.3,
          yAxisID: "y1"
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: "index",
        intersect: false
      },
      scales: {
        x: {
          grid: { color: "rgba(255,255,255,0.05)" },
          ticks: { color: "#9ca3af" }
        },
        y: {
          type: "linear",
          display: true,
          position: "left",
          grid: { color: "rgba(255,255,255,0.05)" },
          ticks: { color: "#9ca3af" },
          title: { display: true, text: "Lượng Sinh viên / Lượt thuê", color: "#9ca3af" }
        },
        y1: {
          type: "linear",
          display: true,
          position: "right",
          grid: { drawOnChartArea: false },
          ticks: { color: "#06b6d4" },
          title: { display: true, text: "Công suất lưới điện (kW)", color: "#06b6d4" }
        }
      },
      plugins: {
        legend: {
          labels: { color: "#f3f4f6" }
        }
      }
    }
  });
}

async function resetFullSystem() {
  try {
    const res = await fetch("/api/simulation/reset", { method: "POST" });
    const result = await res.json();
    showToast("info", result.message);
    document.getElementById("sim-results-wrapper").style.display = "none";
    loadNetworkData();
    loadHubs();
    loadUserTrips();
  } catch (err) {
    showToast("error", "Lỗi đặt lại hệ thống");
  }
}

// ==========================================
// TOAST NOTIFICATIONS HELPER
// ==========================================
function showToast(type, message) {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const colors = {
    success: { bg: "#065f46", border: "#10b981", icon: "fa-circle-check" },
    error: { bg: "#881337", border: "#f43f5e", icon: "fa-circle-xmark" },
    warning: { bg: "#78350f", border: "#f59e0b", icon: "fa-triangle-exclamation" },
    info: { bg: "#1e3a8a", border: "#3b82f6", icon: "fa-circle-info" }
  };

  const style = colors[type] || colors.info;

  const toast = document.createElement("div");
  toast.style.cssText = `
    background: ${style.bg};
    border-left: 4px solid ${style.border};
    color: white;
    padding: 12px 18px;
    border-radius: var(--radius-md);
    box-shadow: 0 10px 25px rgba(0,0,0,0.5);
    font-size: 0.85rem;
    display: flex;
    align-items: center;
    gap: 10px;
    min-width: 280px;
    max-width: 400px;
    animation: fadeIn 0.3s ease;
  `;

  toast.innerHTML = `<i class="fa-solid ${style.icon}"></i> <span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(20px)";
    toast.style.transition = "all 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}
