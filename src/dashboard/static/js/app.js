/**
 * Smart Cockpit Traffic Guard - Frontend Controller
 */

let currentCategory = "monitor";
let currentReviewId = null;
let roiConfig = null;

// Initialize on load
document.addEventListener("DOMContentLoaded", () => {
    updateCockpitClock();
    setInterval(updateCockpitClock, 1000);

    fetchStats();
    fetchViolations();
    loadRoiConfig();
    startCockpitCanvasSimulation();
    initWebSocket();
});

// Digital Cockpit Clock
function updateCockpitClock() {
    const el = document.getElementById("cockpitClock");
    if (!el) return;
    const now = new Date();
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    el.innerText = `${hours}:${minutes}`;
}

// Navigation Category Switcher
function switchCategory(cat) {
    currentCategory = cat;

    // Update active sidebar state
    document.querySelectorAll(".menu-nav-item").forEach(btn => btn.classList.remove("active"));
    const activeBtn = document.getElementById(`menu-${cat}`);
    if (activeBtn) activeBtn.classList.add("active");

    // Hide all sections
    document.getElementById("view-settings").classList.toggle("hidden", cat !== "settings");
    document.getElementById("view-monitor").classList.toggle("hidden", cat !== "monitor");
    document.getElementById("view-violations").classList.toggle("hidden", cat !== "violations");
    document.getElementById("view-roi").classList.toggle("hidden", cat !== "roi");

    if (cat === "roi") {
        renderRoiEditor();
    }
}

// Stepper adjustment [- | 200 m | +]
function adjustStepper(elemId, delta) {
    const el = document.getElementById(elemId);
    if (!el) return;
    let val = parseInt(el.innerText) || 200;
    val = Math.max(50, Math.min(1000, val + delta));
    el.innerText = `${val} m`;
}

// Speed Limit Badge Selection
function selectSpeedBadge(badgeEl, speed) {
    document.querySelectorAll(".speed-badge").forEach(b => {
        b.classList.remove("active-red", "active-blue");
    });
    badgeEl.classList.add(speed <= 50 ? "active-red" : "active-blue");
}

// Fetch Violation Stats
async function fetchStats() {
    try {
        const res = await fetch("/api/violations/stats/summary");
        if (res.ok) {
            const data = await res.json();
            document.getElementById("stat-total").innerText = data.total_violations || 0;
            document.getElementById("stat-approved").innerText = data.approved || 0;
            document.getElementById("stat-pending").innerText = data.pending_review || 0;
            document.getElementById("badge-violations-count").innerText = data.pending_review || 0;
        }
    } catch (err) {
        console.warn("Could not fetch stats:", err);
    }
}

// Fetch and Render Violations Table
async function fetchViolations() {
    const plate = document.getElementById("filterPlate")?.value || "";
    const type = document.getElementById("filterType")?.value || "";
    const status = document.getElementById("filterStatus")?.value || "";

    const params = new URLSearchParams();
    if (plate) params.append("license_plate", plate);
    if (type) params.append("violation_type", type);
    if (status) params.append("status", status);

    try {
        const res = await fetch(`/api/violations?${params.toString()}`);
        if (!res.ok) return;
        const data = await res.json();
        renderViolationsTable(data.items || []);
    } catch (err) {
        console.error("Failed to load violations:", err);
    }
}

function renderViolationsTable(items) {
    const tbody = document.getElementById("violationsTableBody");
    if (!tbody) return;

    if (items.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="px-5 py-8 text-center text-slate-500">Không có bản ghi vi phạm nào phù hợp bộ lọc.</td></tr>`;
        return;
    }

    tbody.innerHTML = items.map(v => {
        let typeBadge = `<span class="bg-rose-500/20 text-rose-300 border border-rose-500/30 px-2 py-0.5 rounded text-[11px] font-semibold">${v.violation_type}</span>`;
        if (v.violation_type === "WRONG_WAY_DRIVING") {
            typeBadge = `<span class="bg-orange-500/20 text-orange-300 border border-orange-500/30 px-2 py-0.5 rounded text-[11px] font-semibold">NGƯỢC CHIỀU</span>`;
        } else if (v.violation_type === "RED_LIGHT_RUNNING") {
            typeBadge = `<span class="bg-red-500/20 text-red-300 border border-red-500/30 px-2 py-0.5 rounded text-[11px] font-semibold">VƯỢT ĐÈN ĐỎ</span>`;
        } else if (v.violation_type === "ILLEGAL_TURN") {
            typeBadge = `<span class="bg-purple-500/20 text-purple-300 border border-purple-500/30 px-2 py-0.5 rounded text-[11px] font-semibold">CẤM RẼ / SAI LÀN</span>`;
        }

        let statusBadge = `<span class="text-orange-400 font-semibold text-[11px]"><i class="fa-solid fa-clock"></i> Chờ duyệt</span>`;
        if (v.status === "APPROVED") {
            statusBadge = `<span class="text-emerald-400 font-semibold text-[11px]"><i class="fa-solid fa-check"></i> Đã phạt</span>`;
        } else if (v.status === "REJECTED") {
            statusBadge = `<span class="text-slate-500 font-semibold text-[11px]"><i class="fa-solid fa-xmark"></i> Đã hủy</span>`;
        }

        const dateStr = v.timestamp ? new Date(v.timestamp * 1000).toLocaleString("vi-VN") : "N/A";

        return `
            <tr class="hover:bg-[#1a1e24] transition">
                <td class="px-5 py-3.5 font-mono text-[11px] text-orange-400 font-bold">${v.event_id}</td>
                <td class="px-5 py-3.5">${typeBadge}</td>
                <td class="px-5 py-3.5 font-mono font-bold text-white tracking-wide">${v.license_plate || '<span class="text-slate-500">Chưa nhận diện</span>'}</td>
                <td class="px-5 py-3.5 uppercase text-[11px] font-medium text-slate-300">${v.vehicle_type}</td>
                <td class="px-5 py-3.5 text-[11px] text-slate-400">${dateStr}</td>
                <td class="px-5 py-3.5">${statusBadge}</td>
                <td class="px-5 py-3.5 text-right">
                    <button onclick="openReviewModal(${v.id})" class="bg-orange-500/20 hover:bg-orange-500/30 text-orange-300 border border-orange-500/40 px-3 py-1 rounded-lg text-xs font-semibold transition">
                        Thẩm định
                    </button>
                </td>
            </tr>
        `;
    }).join("");
}

// Review Modal Dialog
async function openReviewModal(id) {
    currentReviewId = id;
    try {
        const res = await fetch(`/api/violations/${id}`);
        if (!res.ok) return;
        const v = await res.json();

        const modalContent = document.getElementById("modalContent");
        modalContent.innerHTML = `
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label class="text-[11px] text-slate-400 block mb-1">Ảnh Snapshot Bằng Chứng</label>
                    <div class="aspect-video bg-black rounded-xl overflow-hidden border border-[#272c33] flex items-center justify-center">
                        ${v.snapshot_path ? `<img src="/${v.snapshot_path}" class="w-full h-full object-cover">` : '<span class="text-slate-500 text-xs">Không có ảnh snapshot</span>'}
                    </div>
                </div>
                <div>
                    <label class="text-[11px] text-slate-400 block mb-1">Ảnh Cận Cảnh Biển Số</label>
                    <div class="h-28 bg-black rounded-xl overflow-hidden border border-[#272c33] flex items-center justify-center mb-3">
                        ${v.plate_crop_path ? `<img src="/${v.plate_crop_path}" class="max-h-full object-contain">` : '<span class="text-slate-500 text-xs">Biển số OCR: ' + (v.license_plate || 'N/A') + '</span>'}
                    </div>
                    <div class="text-xs space-y-1 text-slate-300 bg-[#121417] p-3 rounded-xl border border-[#272c33]">
                        <div><strong>Biển số:</strong> <span class="text-orange-400 font-mono text-sm">${v.license_plate || 'Chưa rõ'}</span></div>
                        <div><strong>Loại lỗi:</strong> ${v.violation_type}</div>
                        <div><strong>Phương tiện:</strong> ${v.vehicle_type}</div>
                    </div>
                </div>
            </div>
            <div>
                <label class="text-[11px] text-slate-400 block mb-1">Ghi Chú Cán Bộ CSGT</label>
                <textarea id="reviewNotes" placeholder="Nhập căn cứ xử phạt hoặc lý do hủy bỏ..." class="w-full bg-[#121417] border border-[#272c33] text-xs p-3 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-orange-500 h-20">${v.reviewer_notes || ''}</textarea>
            </div>
        `;

        document.getElementById("reviewModal").classList.remove("hidden");
    } catch (err) {
        console.error("Modal error:", err);
    }
}

function closeModal() {
    document.getElementById("reviewModal").classList.add("hidden");
    currentReviewId = null;
}

async function submitReview(status) {
    if (!currentReviewId) return;
    const notes = document.getElementById("reviewNotes")?.value || "";

    try {
        const res = await fetch(`/api/violations/${currentReviewId}/review`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status, notes })
        });
        if (res.ok) {
            closeModal();
            fetchStats();
            fetchViolations();
        }
    } catch (err) {
        alert("Lỗi khi gửi kết quả thẩm định: " + err);
    }
}

// WebSocket Live Alerts
function initWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/api/stream/ws/alerts`;

    try {
        const ws = new WebSocket(wsUrl);
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            addLiveAlertCard(data);
            fetchStats();
        };
        ws.onclose = () => {
            setTimeout(initWebSocket, 4000);
        };
    } catch (err) {
        console.warn("WebSocket offline fallback:", err);
    }
}

function addLiveAlertCard(data) {
    const list = document.getElementById("liveAlertsList");
    if (!list) return;

    const card = document.createElement("div");
    card.className = "bg-[#181c22] border border-orange-500/40 rounded-xl p-3 shadow-lg shadow-orange-500/10 flex items-center justify-between";
    card.innerHTML = `
        <div class="flex items-center gap-3">
            <div class="w-8 h-8 rounded-lg bg-orange-500/20 text-orange-400 flex items-center justify-center font-bold text-xs border border-orange-500/30">
                <i class="fa-solid fa-triangle-exclamation"></i>
            </div>
            <div>
                <div class="text-[11px] font-bold text-white uppercase">${data.violation_type || 'VI PHẠM MỚI'}</div>
                <div class="text-[11px] text-orange-400 font-mono font-bold">${data.license_plate || '30A-***.**'} • ID: ${data.track_id}</div>
            </div>
        </div>
        <span class="text-[10px] text-slate-400 font-mono">Vừa xong</span>
    `;

    list.insertBefore(card, list.firstChild);
    if (list.children.length > 8) {
        list.removeChild(list.lastChild);
    }
}

// Cockpit Canvas Simulation
function startCockpitCanvasSimulation() {
    const canvas = document.getElementById("liveCanvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    let cars = [
        { x: 260, y: 390, speed: 2.1, color: "#38bdf8", plate: "30F-999.99", trackId: 101 },
        { x: 480, y: 340, speed: 2.7, color: "#f97316", plate: "29A-123.45", trackId: 102 },
        { x: 700, y: 410, speed: 1.8, color: "#22c55e", plate: "51G-888.88", trackId: 103 },
    ];

    let lightState = "RED";
    let lightTimer = 0;

    function renderLoop() {
        // Dark background
        ctx.fillStyle = "#0c0d0e";
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Asphalt perspective road
        ctx.fillStyle = "#1e232a";
        ctx.beginPath();
        ctx.moveTo(150, 260);
        ctx.lineTo(810, 260);
        ctx.lineTo(920, 540);
        ctx.lineTo(40, 540);
        ctx.closePath();
        ctx.fill();

        // Stop Line (White neon)
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 5;
        ctx.beginPath();
        ctx.moveTo(210, 360);
        ctx.lineTo(750, 360);
        ctx.stroke();

        // Traffic Light Housing on the right
        ctx.fillStyle = "#121417";
        ctx.fillRect(800, 40, 38, 105);
        ctx.strokeStyle = "#2e3642";
        ctx.lineWidth = 2;
        ctx.strokeRect(800, 40, 38, 105);

        // Circles
        ctx.fillStyle = (lightState === "RED") ? "#ef4444" : "#450a0a";
        ctx.beginPath(); ctx.arc(819, 58, 11, 0, Math.PI * 2); ctx.fill();

        ctx.fillStyle = (lightState === "YELLOW") ? "#eab308" : "#422006";
        ctx.beginPath(); ctx.arc(819, 92, 11, 0, Math.PI * 2); ctx.fill();

        ctx.fillStyle = (lightState === "GREEN") ? "#22c55e" : "#052e16";
        ctx.beginPath(); ctx.arc(819, 126, 11, 0, Math.PI * 2); ctx.fill();

        // Animate Cars
        cars.forEach(car => {
            car.y += car.speed;
            if (car.y > 540) car.y = 260;

            const isViolating = (car.y > 360 && lightState === "RED");

            // Bounding box
            ctx.strokeStyle = isViolating ? "#ef4444" : car.color;
            ctx.lineWidth = 2.5;
            ctx.strokeRect(car.x, car.y, 60, 85);

            // Label tag
            ctx.fillStyle = "rgba(12, 13, 14, 0.85)";
            ctx.fillRect(car.x, car.y - 18, 96, 16);
            ctx.fillStyle = isViolating ? "#ef4444" : "#ffffff";
            ctx.font = "bold 9px monospace";
            ctx.fillText(`ID:${car.trackId} ${car.plate}`, car.x + 3, car.y - 6);
        });

        // Periodic light toggle
        lightTimer++;
        if (lightTimer % 240 === 0) {
            lightState = (lightState === "RED") ? "GREEN" : (lightState === "GREEN") ? "YELLOW" : "RED";
            const ind = document.getElementById("light-indicator");
            if (ind) {
                const colorClass = lightState === 'RED' ? 'bg-rose-500/20 text-rose-400 border-rose-500/40 shadow-[0_0_12px_rgba(239,68,68,0.4)]' :
                                   lightState === 'YELLOW' ? 'bg-amber-500/20 text-amber-400 border-amber-500/40 shadow-[0_0_12px_rgba(234,179,8,0.4)]' :
                                   'bg-emerald-500/20 text-emerald-400 border-emerald-500/40 shadow-[0_0_12px_rgba(34,197,94,0.4)]';
                ind.className = `flex items-center gap-2 text-xs font-bold px-3 py-1 rounded-full border transition-all ${colorClass}`;
                ind.innerHTML = `<span class="w-2.5 h-2.5 rounded-full ${lightState === 'RED' ? 'bg-rose-500' : lightState === 'YELLOW' ? 'bg-amber-500' : 'bg-emerald-500'}"></span> ĐÈN ${lightState}`;
            }
        }

        requestAnimationFrame(renderLoop);
    }

    renderLoop();
}

// ROI Editor Canvas
async function loadRoiConfig() {
    try {
        const res = await fetch("/api/config/camera");
        if (res.ok) {
            roiConfig = await res.json();
        }
    } catch (err) {
        console.warn("Could not load ROI config:", err);
    }
}

function renderRoiEditor() {
    const canvas = document.getElementById("roiCanvas");
    if (!canvas || !roiConfig) return;
    const ctx = canvas.getContext("2d");

    ctx.fillStyle = "#0c0d0e";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.strokeStyle = "#f97316";
    ctx.lineWidth = 3;

    if (roiConfig.stop_line) {
        ctx.beginPath();
        ctx.moveTo(roiConfig.stop_line[0][0] / 2, roiConfig.stop_line[0][1] / 2);
        ctx.lineTo(roiConfig.stop_line[1][0] / 2, roiConfig.stop_line[1][1] / 2);
        ctx.stroke();

        ctx.fillStyle = "#f97316";
        ctx.font = "bold 11px sans-serif";
        ctx.fillText("Vạch Dừng (Stop Line)", roiConfig.stop_line[0][0] / 2, roiConfig.stop_line[0][1] / 2 - 10);
    }
}

function resetRoiDraft() {
    loadRoiConfig().then(renderRoiEditor);
}

async function saveRoiConfig() {
    if (!roiConfig) return;
    try {
        const res = await fetch("/api/config/camera", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ config: roiConfig })
        });
        if (res.ok) alert("Đã lưu cấu hình ROI thành công!");
    } catch (err) {
        alert("Lỗi khi lưu cấu hình ROI: " + err);
    }
}
