// AegisGuard Real-Time SOC Command Center Controller

let rpsChart = null;
let statusChart = null;
let ws = null;
const rpsHistory = Array(20).fill(0);
const rpsLabels = Array(20).fill('');

document.addEventListener('DOMContentLoaded', () => {
    initClock();
    initCharts();
    initWebSocket();
    fetchStats();
    fetchAlerts();
    fetchLogs();

    // Periodic poll for stats and logs (every 3 seconds)
    setInterval(fetchStats, 3000);
    setInterval(fetchLogs, 4000);
});

// Live UTC Clock
function initClock() {
    const clockEl = document.getElementById('live-clock');
    const update = () => {
        const now = new Date();
        clockEl.textContent = now.toISOString().substring(11, 19) + ' UTC';
    };
    update();
    setInterval(update, 1000);
}

// Chart.js Setup
function initCharts() {
    const ctxRps = document.getElementById('rpsChart').getContext('2d');
    const gradient = ctxRps.createLinearGradient(0, 0, 0, 250);
    gradient.addColorStop(0, 'rgba(0, 242, 254, 0.35)');
    gradient.addColorStop(1, 'rgba(0, 242, 254, 0.0)');

    rpsChart = new Chart(ctxRps, {
        type: 'line',
        data: {
            labels: rpsLabels,
            datasets: [{
                label: 'Requests / Sec',
                data: rpsHistory,
                borderColor: '#00f2fe',
                backgroundColor: gradient,
                borderWidth: 2.5,
                fill: true,
                tension: 0.35,
                pointRadius: 2,
                pointBackgroundColor: '#00f2fe'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            scales: {
                x: { display: false },
                y: {
                    beginAtZero: true,
                    suggestedMax: 15,
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#64748b', font: { family: 'JetBrains Mono', size: 11 } }
                }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });

    const ctxStatus = document.getElementById('statusChart').getContext('2d');
    statusChart = new Chart(ctxStatus, {
        type: 'doughnut',
        data: {
            labels: ['200 OK', '429 Rate Limited', '4xx Errors', '5xx Server'],
            datasets: [{
                data: [1, 0, 0, 0],
                backgroundColor: ['#10b981', '#ef4444', '#f59e0b', '#8b5cf6'],
                borderColor: '#0f172a',
                borderWidth: 3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '70%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#94a3b8', font: { family: 'Inter', size: 11 }, boxWidth: 12 }
                }
            }
        }
    });
}

// WebSocket Connection Management
function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/telemetry`;
    const pulseDot = document.getElementById('ws-pulse');
    const wsStatus = document.getElementById('ws-status-text');

    try {
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            pulseDot.style.backgroundColor = '#10b981';
            wsStatus.textContent = 'Telemetry Stream: Connected';
        };

        ws.onmessage = (event) => {
            const payload = JSON.parse(event.data);
            if (payload.event === 'telemetry_pulse') {
                handleTelemetryPulse(payload.data);
            } else if (payload.event === 'anomaly_detected') {
                handleAnomalyDetected(payload.data);
            }
        };

        ws.onclose = () => {
            pulseDot.style.backgroundColor = '#f59e0b';
            wsStatus.textContent = 'Telemetry Stream: Reconnecting...';
            setTimeout(initWebSocket, 2500);
        };

        ws.onerror = () => {
            pulseDot.style.backgroundColor = '#ef4444';
            wsStatus.textContent = 'Telemetry Stream: Offline';
            ws.close();
        };
    } catch (e) {
        console.warn("WebSocket init error:", e);
    }
}

function handleTelemetryPulse(data) {
    // Update live throughput graph
    rpsHistory.shift();
    rpsHistory.push(data.rps || 0);
    if (rpsChart) {
        rpsChart.update();
    }

    document.getElementById('val-current-rps').textContent = (data.rps || 0).toFixed(1);
    document.getElementById('val-p95-latency').textContent = `${data.p95_latency || 0} ms`;
    document.getElementById('val-avg-latency').textContent = `${data.avg_latency || 0} ms`;
}

function handleAnomalyDetected(alert) {
    // Increment threat counter
    const threatsEl = document.getElementById('val-active-threats');
    threatsEl.textContent = parseInt(threatsEl.textContent || '0') + 1;

    // Prepend to alerts table
    const tbody = document.getElementById('alerts-body');
    const emptyRow = tbody.querySelector('.empty-row');
    if (emptyRow) emptyRow.remove();

    const tr = document.createElement('tr');
    tr.style.animation = 'highlight 1.5s ease';

    const nowStr = new Date().toISOString().substring(11, 19);
    const scoreBadge = alert.threat_score >= 0.85 
        ? `<span class="badge-threat-critical">${alert.threat_score} (CRITICAL)</span>` 
        : `<span class="badge-threat-high">${alert.threat_score} (HIGH)</span>`;
    
    const mitigationBadge = alert.mitigation.includes('Blocked')
        ? `<span class="badge-mitigation-blocked">${alert.mitigation}</span>`
        : `<span class="badge-mitigation-throttled">${alert.mitigation}</span>`;

    tr.innerHTML = `
        <td style="font-family: var(--font-mono); color: var(--accent-cyan);">${nowStr}</td>
        <td style="font-family: var(--font-mono); font-weight: 600;">${alert.ip}</td>
        <td>${scoreBadge}</td>
        <td><strong style="color: #f8fafc;">${alert.anomaly_type}</strong></td>
        <td><span style="color: var(--text-secondary);">${alert.reason}</span></td>
        <td>${mitigationBadge}</td>
    `;
    tbody.insertBefore(tr, tbody.firstChild);
}

// REST Data Fetching
async function fetchStats() {
    try {
        const res = await fetch('/api/stats');
        if (!res.ok) return;
        const stats = await res.json();

        document.getElementById('val-total-reqs').textContent = stats.total_requests.toLocaleString();
        document.getElementById('val-blocked-reqs').textContent = stats.total_blocked.toLocaleString();
        document.getElementById('val-active-threats').textContent = stats.active_threats;
        
        const blockRate = stats.total_requests > 0 
            ? ((stats.total_blocked / stats.total_requests) * 100).toFixed(1) 
            : '0.0';
        document.getElementById('val-block-rate').textContent = `${blockRate}% Mitigated`;

        // Update status chart
        const dist = stats.status_code_distribution || {};
        const c200 = dist['200'] || 0;
        const c429 = dist['429'] || 0;
        const c4xx = (dist['401'] || 0) + (dist['403'] || 0) + (dist['404'] || 0);
        const c5xx = dist['500'] || 0;

        if (statusChart && (c200 + c429 + c4xx + c5xx > 0)) {
            statusChart.data.datasets[0].data = [c200, c429, c4xx, c5xx];
            statusChart.update();
        }
    } catch (err) {
        console.debug("Failed to fetch stats:", err);
    }
}

async function fetchAlerts() {
    try {
        const res = await fetch('/api/alerts?limit=15');
        if (!res.ok) return;
        const alerts = await res.json();
        const tbody = document.getElementById('alerts-body');

        if (alerts.length === 0) {
            tbody.innerHTML = '<tr class="empty-row"><td colspan="6">No security anomalies detected yet. Launch a simulation above to test!</td></tr>';
            return;
        }

        tbody.innerHTML = alerts.map(a => {
            const timeStr = new Date(a.timestamp).toISOString().substring(11, 19);
            const scoreBadge = a.threat_score >= 0.85 
                ? `<span class="badge-threat-critical">${a.threat_score} (CRITICAL)</span>` 
                : `<span class="badge-threat-high">${a.threat_score} (HIGH)</span>`;
            
            const mitBadge = (a.mitigation_status || '').includes('Blocked')
                ? `<span class="badge-mitigation-blocked">${a.mitigation_status}</span>`
                : `<span class="badge-mitigation-throttled">${a.mitigation_status}</span>`;

            return `
                <tr>
                    <td style="font-family: var(--font-mono); color: var(--accent-cyan);">${timeStr}</td>
                    <td style="font-family: var(--font-mono); font-weight: 600;">${a.ip_address}</td>
                    <td>${scoreBadge}</td>
                    <td><strong style="color: #f8fafc;">${a.anomaly_type}</strong></td>
                    <td><span style="color: var(--text-secondary);">${a.reason}</span></td>
                    <td>${mitBadge}</td>
                </tr>
            `;
        }).join('');
    } catch (err) {
        console.debug("Failed to fetch alerts:", err);
    }
}

async function fetchLogs() {
    try {
        const res = await fetch('/api/logs?limit=15');
        if (!res.ok) return;
        const logs = await res.json();
        const tbody = document.getElementById('logs-body');
        document.getElementById('log-count').textContent = `${logs.length} recent`;

        if (logs.length === 0) {
            tbody.innerHTML = '<tr class="empty-row"><td colspan="7">Awaiting traffic ingestion...</td></tr>';
            return;
        }

        tbody.innerHTML = logs.map(log => {
            const timeStr = new Date(log.timestamp).toISOString().substring(11, 19);
            const statusClass = log.status_code === 200 ? 'pill-status-200' : (log.status_code === 429 ? 'pill-status-429' : 'pill-status-401');
            const methodClass = log.method === 'GET' ? 'pill-method-get' : 'pill-method-post';

            return `
                <tr>
                    <td style="font-family: var(--font-mono); font-size: 0.8rem;">${timeStr}</td>
                    <td style="font-family: var(--font-mono);">${log.ip_address}</td>
                    <td><span class="pill-method ${methodClass}">${log.method}</span></td>
                    <td style="font-family: var(--font-mono); font-size: 0.82rem; color: #cbd5e1;">${log.endpoint}</td>
                    <td><span class="${statusClass}">${log.status_code}</span></td>
                    <td style="font-family: var(--font-mono); font-size: 0.8rem;">${log.response_time_ms} ms</td>
                    <td style="font-size: 0.75rem; color: var(--text-muted); max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${log.user_agent || '-'}</td>
                </tr>
            `;
        }).join('');
    } catch (err) {
        console.debug("Failed to fetch logs:", err);
    }
}

// Attack Simulation Action
async function triggerSimulation(scenario) {
    const statusPill = document.getElementById('sim-status');
    const buttons = document.querySelectorAll('.sim-btn');

    buttons.forEach(b => b.disabled = true);
    statusPill.className = 'sim-status-running';
    statusPill.textContent = `Injecting '${scenario.toUpperCase()}' Traffic...`;

    try {
        const count = scenario === 'ddos' ? 60 : (scenario === 'scraper' ? 40 : 20);
        const res = await fetch('/api/simulate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ scenario: scenario, requests_count: count, concurrency: 6 })
        });
        const data = await res.json();
        
        statusPill.textContent = `Completed: ${data.total_sent} reqs (${data.blocked} 429 blocked)`;
        setTimeout(() => {
            statusPill.className = 'sim-status-idle';
            statusPill.textContent = 'Simulator Idle';
        }, 4000);

        // Immediate refresh
        fetchStats();
        fetchAlerts();
        fetchLogs();
    } catch (err) {
        statusPill.textContent = 'Simulation Error';
        console.error("Simulation failed:", err);
    } finally {
        buttons.forEach(b => b.disabled = false);
    }
}
