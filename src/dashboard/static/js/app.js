/**
 * Traffic Violation Guard - Frontend Application Script
 */

let currentTab = "monitor";
let currentReviewId = null;
let roiConfig = null;

// Initialize on page load
document.addEventListener("DOMContentLoaded", () => {
    fetchStats();
    fetchViolations();
    loadRoiConfig();
    startCanvasSimulation();
    initWebSocket();
});

// Tab Switching
function switchTab(tab) {
    currentTab = tab;
    document.querySelectorAll(".nav-tab").forEach(btn => btn.classList.remove("active"));
    document.getElementById(`tab-${tab}`).classList.add("active");

    document.getElementById("view-monitor").classList.toggle("hidden", tab !== "monitor");
    document.getElementById("view-violations").classList.toggle("hidden", tab !== "violations");
    document.getElementById("view-roi").classList.toggle("hidden", tab !== "roi");

    if (tab === "roi") {
        renderRoiEditor();
    }
}

// Fetch Violation Stats
async function fetchStats() {
    try {
        const res = await fetch("/api/violations/stats/summary");
        if (res.ok) {
            const data = await res.json();
            document.getElementById("stat-total").innerText = data.total_violations || 0;
            document.getElementById("stat-approved").innerText = data.approved || 0;
            document.getElementById("badge-pending").innerText = data.pending_review || 0;
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
        let typeBadge = `<span class="bg-rose-500/20 text-rose-300 border border-rose-500/30 px-2 py-0.5 rounded text-xs font-semibold">${v.violation_type}</span>`;
        if (v.violation_type === "WRONG_WAY_DRIVING") {
            typeBadge = `<span class="bg-amber-500/20 text-amber-300 border border-amber-500/30 px-2 py-0.5 rounded text-xs font-semibold">NGƯỢC CHIỀU</span>`;
        } else if (v.violation_type === "RED_LIGHT_RUNNING") {
            typeBadge = `<span class="bg-red-500/20 text-red-300 border border-red-500/30 px-2 py-0.5 rounded text-xs font-semibold">VƯỢT ĐÈN ĐỎ</span>`;
        } else if (v.violation_type === "ILLEGAL_TURN") {
            typeBadge = `<span class="bg-purple-500/20 text-purple-300 border border-purple-500/30 px-2 py-0.5 rounded text-xs font-semibold">CẤM RẼ / SAI LÀN</span>`;
        }

        let statusBadge = `<span class="text-amber-400 font-semibold text-xs"><i class="fa-solid fa-clock"></i> Chờ duyệt</span>`;
        if (v.status === "APPROVED") {
            statusBadge = `<span class="text-emerald-400 font-semibold text-xs"><i class="fa-solid fa-check"></i> Đã duyệt</span>`;
        } else if (v.status === "REJECTED") {
            statusBadge = `<span class="text-slate-500 font-semibold text-xs"><i class="fa-solid fa-xmark"></i> Đã hủy</span>`;
        }

        const dateStr = v.timestamp ? new Date(v.timestamp * 1000).toLocaleString("vi-VN") : "N/A";

        return `
            <tr class="hover:bg-slate-800/40 transition">
                <td class="px-5 py-4 font-mono text-xs text-blue-400 font-bold">${v.event_id}</td>
                <td class="px-5 py-4">${typeBadge}</td>
                <td class="px-5 py-4 font-mono font-bold text-white tracking-wide">${v.license_plate || '<span class="text-slate-500">Chưa nhận diện</span>'}</td>
                <td class="px-5 py-4 uppercase text-xs font-medium text-slate-300">${v.vehicle_type}</td>
                <td class="px-5 py-4 text-xs text-slate-400">${dateStr}</td>
                <td class="px-5 py-4">${statusBadge}</td>
                <td class="px-5 py-4 text-right">
                    <button onclick="openReviewModal(${v.id})" class="bg-blue-600/20 hover:bg-blue-600/40 text-blue-300 border border-blue-500/30 px-3 py-1 rounded-lg text-xs font-semibold transition">
                        Chi tiết / Thẩm định
                    </button>
                </td>
            </tr>
        `;
    }).join("");
}

// Review Modal
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
                    <label class="text-xs text-slate-400 block mb-1">Ảnh Snapshot Bằng Chứng</label>
                    <div class="aspect-video bg-black rounded-lg overflow-hidden border border-slate-700 flex items-center justify-center">
                        ${v.snapshot_path ? `<img src="/${v.snapshot_path}" class="w-full h-full object-cover">` : '<span class="text-slate-500 text-xs">Không có ảnh</span>'}
                    </div>
                </div>
                <div>
                    <label class="text-xs text-slate-400 block mb-1">Ảnh Cận Cảnh Biển Số</label>
                    <div class="h-28 bg-black rounded-lg overflow-hidden border border-slate-700 flex items-center justify-center mb-3">
                        ${v.plate_crop_path ? `<img src="/${v.plate_crop_path}" class="max-h-full object-contain">` : '<span class="text-slate-500 text-xs">Biển số OCR: ' + (v.license_plate || 'N/A') + '</span>'}
                    </div>
                    <div class="text-xs space-y-1 text-slate-300">
                        <div><strong>Biển số:</strong> <span class="text-amber-400 font-mono text-sm">${v.license_plate || 'Chưa rõ'}</span></div>
                        <div><strong>Loại lỗi:</strong> ${v.violation_type}</div>
                        <div><strong>Phương tiện:</strong> ${v.vehicle_type}</div>
                    </div>
                </div>
            </div>
            <div>
                <label class="text-xs text-slate-400 block mb-1">Ghi Chú Cán Bộ Thẩm Định</label>
                <textarea id="reviewNotes" placeholder="Nhập lý do duyệt hoặc bỏ qua..." class="w-full bg-slate-800 border border-slate-700 text-sm p-2.5 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 h-20">${v.reviewer_notes || ''}</textarea>
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
        console.warn("WebSocket connection skipped in offline mode:", err);
    }
}

function addLiveAlertCard(data) {
    const list = document.getElementById("liveAlertsList");
    if (!list) return;

    const card = document.createElement("div");
    card.className = "bg-slate-800/80 border border-rose-500/30 rounded-xl p-3 shadow flex items-center justify-between animate-pulse";
    card.innerHTML = `
        <div class="flex items-center gap-3">
            <div class="w-9 h-9 rounded-lg bg-rose-500/20 text-rose-400 flex items-center justify-center font-bold text-sm">
                <i class="fa-solid fa-triangle-exclamation"></i>
            </div>
            <div>
                <div class="text-xs font-bold text-white">${data.violation_type || 'VI PHẠM MỚI'}</div>
                <div class="text-xs text-amber-400 font-mono font-semibold">${data.license_plate || '29A-***.**'} | ID: ${data.track_id}</div>
            </div>
        </div>
        <span class="text-xs text-slate-400">Vừa xong</span>
    `;

    list.insertBefore(card, list.firstChild);
    if (list.children.length > 10) {
        list.removeChild(list.lastChild);
    }
}

// Canvas Simulation
function startCanvasSimulation() {
    const canvas = document.getElementById("liveCanvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    let cars = [
        { x: 250, y: 380, speed: 2.2, color: "#38bdf8", plate: "30F-999.99", trackId: 101 },
        { x: 480, y: 340, speed: 2.8, color: "#f59e0b", plate: "29A-123.45", trackId: 102 },
        { x: 720, y: 400, speed: 1.9, color: "#10b981", plate: "51G-888.88", trackId: 103 },
    ];

    let lightState = "RED";
    let lightTimer = 0;

    function renderLoop() {
        // Clear background
        ctx.fillStyle = "#1e293b";
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Draw Road Markings
        ctx.fillStyle = "#334155";
        ctx.beginPath();
        ctx.moveTo(150, 260);
        ctx.lineTo(810, 260);
        ctx.lineTo(910, 540);
        ctx.lineTo(50, 540);
        ctx.closePath();
        ctx.fill();

        // White Stop Line
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 6;
        ctx.beginPath();
        ctx.moveTo(200, 360);
        ctx.lineTo(760, 360);
        ctx.stroke();

        // Draw Traffic Light on side
        ctx.fillStyle = "#0f172a";
        ctx.fillRect(800, 40, 40, 110);
        ctx.strokeStyle = "#64748b";
        ctx.lineWidth = 2;
        ctx.strokeRect(800, 40, 40, 110);

        // Light circles
        ctx.fillStyle = (lightState === "RED") ? "#ef4444" : "#450a0a";
        ctx.beginPath(); ctx.arc(820, 60, 12, 0, Math.PI * 2); ctx.fill();

        ctx.fillStyle = (lightState === "YELLOW") ? "#eab308" : "#422006";
        ctx.beginPath(); ctx.arc(820, 95, 12, 0, Math.PI * 2); ctx.fill();

        ctx.fillStyle = (lightState === "GREEN") ? "#22c55e" : "#052e16";
        ctx.beginPath(); ctx.arc(820, 130, 12, 0, Math.PI * 2); ctx.fill();

        // Animate Cars
        cars.forEach(car => {
            car.y += car.speed;
            if (car.y > 540) car.y = 260;

            // Draw Car BBox
            ctx.strokeStyle = (car.y > 360 && lightState === "RED") ? "#ef4444" : car.color;
            ctx.lineWidth = 3;
            ctx.strokeRect(car.x, car.y, 60, 90);

            // Label
            ctx.fillStyle = "rgba(15, 23, 42, 0.8)";
            ctx.fillRect(car.x, car.y - 18, 90, 16);
            ctx.fillStyle = "#ffffff";
            ctx.font = "10px monospace";
            ctx.fillText(`ID:${car.trackId} ${car.plate}`, car.x + 2, car.y - 6);
        });

        // Toggle light periodically
        lightTimer++;
        if (lightTimer % 240 === 0) {
            lightState = (lightState === "RED") ? "GREEN" : (lightState === "GREEN") ? "YELLOW" : "RED";
            const ind = document.getElementById("light-indicator");
            if (ind) {
                ind.innerHTML = `<span class="w-2 h-2 rounded-full ${lightState === 'RED' ? 'bg-rose-500' : lightState === 'YELLOW' ? 'bg-amber-500' : 'bg-emerald-500'}"></span> ĐÈN ${lightState}`;
            }
        }

        requestAnimationFrame(renderLoop);
    }

    renderLoop();
}

// ROI Config
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

    ctx.fillStyle = "#0f172a";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.strokeStyle = "#38bdf8";
    ctx.lineWidth = 3;

    if (roiConfig.stop_line) {
        ctx.beginPath();
        ctx.moveTo(roiConfig.stop_line[0][0] / 2, roiConfig.stop_line[0][1] / 2);
        ctx.lineTo(roiConfig.stop_line[1][0] / 2, roiConfig.stop_line[1][1] / 2);
        ctx.stroke();

        ctx.fillStyle = "#38bdf8";
        ctx.font = "12px sans-serif";
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
        if (res.ok) alert("Đã cập nhật cấu hình ROI thành công!");
    } catch (err) {
        alert("Lỗi khi lưu cấu hình ROI: " + err);
    }
}
