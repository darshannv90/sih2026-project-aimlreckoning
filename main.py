from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from ekf_engine import SimulationEngine
import time

app = FastAPI(title="Navisense Backend API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sim = SimulationEngine()
start_time = time.time()
cutoff_started_at = None


@app.get("/")
def index():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>NAVISENSE Live Control Room</title>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <link rel="stylesheet" href="/style.css?v=3" />
    </head>
    <body>
        <header class="header">
            <h1>NAVISENSE <span class="sub">AI-ML Dead Reckoning & EKF Sensor Fusion</span></h1>
            <div class="header-controls">
                <div id="network-status" class="network-status online">LIVE NETWORK</div>
                <div id="status-badge" class="badge active">GNSS ACTIVE</div>
            </div>
        </header>

        <div class="main-container">
            <div id="map"></div>
            <div class="sidebar">
                <div class="card">
                    <h3>Live Kinematic Telemetry</h3>
                    <p>Speed: <span id="speed">2.5 km/h</span></p>
                    <p>Heading: <span id="heading">0°</span></p>
                    <p>Confidence Score: <span id="confidence">94%</span></p>
                </div>

                <div class="card error-box">
                    <h3>Comparative Position Error</h3>
                    <p class="nav-err">Navisense Error: <span id="nav-error">0 m</span></p>
                    <p class="cls-err">Classical DR Error: <span id="cls-error">0 m</span></p>
                </div>

                <div class="card">
                    <h3>GNSS & Dead Reckoning Status</h3>
                    <p>Signal Cutoff: <span id="cutoff-status">No</span></p>
                    <p>Cutoff Time: <span id="cutoff-time">—</span></p>
                    <p>Dead Reckoning: <span id="dead-reckoning-status">Standby</span></p>
                </div>

                <div class="card controls">
                    <h3>Simulation Controls</h3>
                    <button id="toggle-outage" onclick="toggleOutage()">Simulate GNSS Outage</button>
                </div>
            </div>
        </div>

        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script src="/script.js?v=3"></script>
        <script>
            if ('serviceWorker' in navigator) {
                            navigator.serviceWorker.register('/sw.js?v=4').catch((error) => {
                    console.warn('Offline cache unavailable:', error);
                });
            }
        </script>
    </body>
    </html>
    """)


@app.get("/script.js")
def script_js():
    return HTMLResponse("""
    const map = L.map('map', { zoomControl: true, zoomSnap: 0.25 }).setView([12.9716, 77.5946], 15);
    const streetMap = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap contributors'
    });
    const satelliteMap = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        maxZoom: 19,
        attribution: '&copy; Esri'
    });
    const terrainMap = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
        maxZoom: 17,
        attribution: '&copy; OpenTopoMap contributors'
    });
    streetMap.addTo(map);
    L.control.layers({
        'Street': streetMap,
        'Satellite': satelliteMap,
        'Terrain': terrainMap
    }, null, { collapsed: false, position: 'topleft' }).addTo(map);

    setTimeout(() => map.invalidateSize(), 400);

    let outageActive = false;
    let autoOutageTimer = 0;
    let livePhoneHeading = null;
    let networkOnline = navigator.onLine !== false;
    let lastKnownPosition = [12.9716, 77.5946];
    let lastHeading = 0;

    const marker = L.marker([12.9716, 77.5946]).addTo(map);
    const cutoffCircle = L.circle([12.9716, 77.5946], {
        radius: 45,
        color: '#ff4d4d',
        fillColor: '#ff4d4d',
        fillOpacity: 0.18,
        opacity: 0.9
    }).addTo(map);
    const normalTrack = L.polyline([], { color: '#5eead4', weight: 4 }).addTo(map);
    const deadReckoningTrack = L.polyline([], { color: '#fbbf24', weight: 4, dashArray: '8 10' }).addTo(map);

    function setStatusBadge(active) {
        const badge = document.getElementById('status-badge');
        const btn = document.getElementById('toggle-outage');
        if (!badge || !btn) return;

        if (active) {
            badge.innerText = 'GNSS SIGNAL LOST - AI EKF ACTIVE';
            badge.className = 'badge lost';
            btn.innerText = 'Restore GNSS Signal';
        } else {
            badge.innerText = 'GNSS ACTIVE';
            badge.className = 'badge active';
            btn.innerText = 'Simulate GNSS Outage';
        }
    }

    function setNetworkStatus(isOnline) {
        const el = document.getElementById('network-status');
        if (!el) return;

        el.className = isOnline ? 'network-status online' : 'network-status offline';
        el.innerText = isOnline ? 'LIVE NETWORK' : 'OFFLINE MODE';
    }

    function buildOfflineTelemetry() {
        const nextHeading = (lastHeading + 1.8 + Math.random() * 4) % 360;

        lastHeading = nextHeading;

        return {
            latitude: lastKnownPosition[0],
            longitude: lastKnownPosition[1],
            heading: Number(nextHeading.toFixed(2)),
            speed_kmh: Number((2.8 + Math.random() * 1.3).toFixed(1)),
            confidence_score: 86,
            navisense_error_m: Number((0.8 + Math.random() * 1.9).toFixed(2)),
            classical_error_m: Number((14 + Math.random() * 18).toFixed(2)),
            signal_cutoff: true,
            signal_cutoff_time: '00:12',
            dead_reckoning_active: true,
            dead_reckoning_mode: 'AUTO',
            gnss_lost: true
        };
    }

    function applyTelemetry(data) {
        const cutoff = Boolean(data.signal_cutoff || outageActive || !networkOnline);

        document.getElementById('speed').innerText = `${data.speed_kmh} km/h`;
        document.getElementById('heading').innerText = `${data.heading}°`;
        document.getElementById('confidence').innerText = `${data.confidence_score}%`;
        document.getElementById('nav-error').innerText = `${data.navisense_error_m} m`;
        document.getElementById('cls-error').innerText = `${data.classical_error_m} m`;
        document.getElementById('cutoff-status').innerText = cutoff ? 'Yes' : 'No';
        document.getElementById('cutoff-time').innerText = data.signal_cutoff_time || '—';
        document.getElementById('dead-reckoning-status').innerText = cutoff ? 'Active' : 'Standby';

        if (data && data.latitude && data.longitude) {
            lastKnownPosition = [data.latitude, data.longitude];
        }
        if (data && data.heading !== undefined) {
            lastHeading = Number(data.heading);
        }

        setStatusBadge(cutoff);

        const newLatLng = [data.latitude, data.longitude];
        marker.setLatLng(newLatLng);
        cutoffCircle.setLatLng(newLatLng);
        cutoffCircle.setRadius(Math.max(35, data.navisense_error_m * 8 || 40));
        cutoffCircle.setStyle({
            opacity: cutoff ? 0.9 : 0.12,
            fillOpacity: cutoff ? 0.18 : 0.04
        });

        if (cutoff) {
            deadReckoningTrack.addLatLng(newLatLng);
            if (deadReckoningTrack.getLatLngs().length > 60) {
                deadReckoningTrack.setLatLngs(deadReckoningTrack.getLatLngs().slice(-60));
            }
        } else {
            normalTrack.addLatLng(newLatLng);
            if (normalTrack.getLatLngs().length > 60) {
                normalTrack.setLatLngs(normalTrack.getLatLngs().slice(-60));
            }
        }

        map.setView(newLatLng, map.getZoom());
    }

    function toggleOutage() {
        outageActive = !outageActive;
        setStatusBadge(outageActive);
        fetchTelemetry();
    }

    async function fetchTelemetry() {
        const params = new URLSearchParams();
        params.set('outage', String(outageActive));
        if (livePhoneHeading !== null) {
            params.set('heading', String(livePhoneHeading));
        }

        try {
            const response = await fetch(`/api/telemetry?${params.toString()}`);
            if (!response.ok) throw new Error('Telemetry request failed');
            const data = await response.json();
            networkOnline = true;
            setNetworkStatus(true);
            applyTelemetry(data);
        } catch (error) {
            console.warn('Using AI dead-reckoning fallback:', error);
            networkOnline = false;
            setNetworkStatus(false);
            applyTelemetry(buildOfflineTelemetry());
        }
    }

    window.addEventListener('deviceorientation', (event) => {
        if (event.alpha !== null) {
            livePhoneHeading = event.alpha;
            lastHeading = Number(event.alpha);
        }
    });

    window.addEventListener('online', () => {
        networkOnline = true;
        setNetworkStatus(true);
        fetchTelemetry();
    });

    window.addEventListener('offline', () => {
        networkOnline = false;
        setNetworkStatus(false);
        applyTelemetry(buildOfflineTelemetry());
    });

    setNetworkStatus(networkOnline);

    setInterval(() => {
        autoOutageTimer += 1;
        if (autoOutageTimer >= 8 && autoOutageTimer <= 18) {
            outageActive = true;
        } else {
            outageActive = false;
        }

        if (networkOnline) {
            fetchTelemetry();
        } else {
            applyTelemetry(buildOfflineTelemetry());
        }
    }, 500);

    fetchTelemetry();
    """, media_type="application/javascript")


@app.get("/sw.js")
def service_worker():
    return HTMLResponse("""
    const CACHE_NAME = 'navisense-offline-v4';
    const APP_SHELL = ['/', '/style.css?v=3', '/script.js?v=3'];

    self.addEventListener('install', (event) => {
        event.waitUntil(
            caches.open(CACHE_NAME)
                .then((cache) => cache.addAll(APP_SHELL))
                .then(() => self.skipWaiting())
        );
    });

    self.addEventListener('activate', (event) => {
        event.waitUntil(self.clients.claim());
    });

    self.addEventListener('fetch', (event) => {
        const request = event.request;
        const url = new URL(request.url);
        const isMapAsset = url.hostname.includes('basemaps.cartocdn.com') ||
            url.hostname.includes('unpkg.com') ||
            url.hostname.includes('tile.openstreetmap.org') ||
            url.hostname.includes('arcgisonline.com') ||
            url.hostname.includes('opentopomap.org');

        if (request.method !== 'GET' || (!isMapAsset && url.origin !== self.location.origin)) {
            return;
        }

        event.respondWith(
            caches.match(request).then((cached) => {
                const networkRequest = fetch(request).then((response) => {
                    if (response.ok || response.type === 'opaque') {
                        const copy = response.clone();
                        caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
                    }
                    return response;
                }).catch(() => cached || Response.error());

                return cached || networkRequest;
            })
        );
    });
    """, media_type="application/javascript")


@app.get("/style.css")
def style_css():
    return HTMLResponse("""
    html, body {
        margin: 0;
        height: 100%;
        background: #eef2f7;
        color: #e5e7eb;
        font-family: Arial, sans-serif;
    }

    .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: rgba(15, 23, 42, 0.95);
        padding: 15px 25px;
        border-bottom: 1px solid rgba(148, 163, 184, 0.25);
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
    }

    .header h1 {
        margin: 0;
        font-size: 20px;
        color: #7dd3fc;
    }

    .header .sub {
        font-size: 12px;
        color: #94a3b8;
    }

    .header-controls {
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .network-status {
        padding: 6px 10px;
        border-radius: 999px;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.08em;
    }

    .network-status.online {
        background: rgba(16, 185, 129, 0.16);
        color: #6ee7b7;
        border: 1px solid rgba(16, 185, 129, 0.45);
    }

    .network-status.offline {
        background: rgba(239, 68, 68, 0.12);
        color: #fca5a5;
        border: 1px solid rgba(239, 68, 68, 0.5);
    }

    .badge {
        padding: 6px 12px;
        font-weight: bold;
        border-radius: 999px;
        font-size: 12px;
        letter-spacing: 0.04em;
    }

    .badge.active {
        background: rgba(34, 197, 94, 0.18);
        color: #bbf7d0;
        border: 1px solid rgba(34, 197, 94, 0.5);
    }

    .badge.lost {
        background: rgba(239, 68, 68, 0.15);
        color: #fecaca;
        border: 1px solid rgba(239, 68, 68, 0.5);
    }

    .main-container {
        position: relative;
        height: calc(100vh - 60px);
        min-height: 480px;
        overflow: hidden;
    }

    #map {
        position: absolute;
        inset: 0;
        width: 100%;
        height: 100%;
        min-height: 480px;
        background: #dbe4ee;
        overflow: hidden;
        box-shadow: inset 0 0 25px rgba(0, 0, 0, 0.3);
    }

    .leaflet-container {
        width: 100%;
        height: 100%;
        background: #dbe4ee;
        filter: saturate(1.08) contrast(1.01);
    }

    .sidebar {
        position: absolute;
        z-index: 1000;
        top: 18px;
        right: 18px;
        width: min(360px, calc(100% - 36px));
        max-height: calc(100% - 36px);
        overflow-y: auto;
        background: rgba(17, 24, 39, 0.92);
        padding: 14px;
        display: flex;
        flex-direction: column;
        gap: 15px;
        border: 1px solid rgba(148, 163, 184, 0.28);
        border-radius: 12px;
        backdrop-filter: blur(12px);
        box-shadow: 0 18px 40px rgba(0, 0, 0, 0.35);
    }

    .card {
        background: rgba(31, 41, 55, 0.9);
        padding: 15px;
        border-radius: 10px;
        border: 1px solid rgba(148, 163, 184, 0.2);
        box-shadow: 0 10px 20px rgba(0, 0, 0, 0.12);
    }

    .card h3 {
        margin-top: 0;
        font-size: 14px;
        color: #cbd5e1;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }

    .error-box {
        border-color: rgba(248, 113, 113, 0.6);
    }

    .nav-err {
        color: #86efac;
        font-weight: bold;
    }

    .cls-err {
        color: #fca5a5;
        font-weight: bold;
    }

    button {
        width: 100%;
        padding: 10px;
        background: linear-gradient(135deg, #ef4444, #b91c1c);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: bold;
        cursor: pointer;
        box-shadow: 0 12px 18px rgba(239, 68, 68, 0.25);
    }

    @media (max-width: 720px) {
        .header {
            padding: 12px 14px;
        }

        .header h1 {
            font-size: 15px;
        }

        .header .sub {
            display: none;
        }

        .header-controls {
            gap: 6px;
            flex-direction: column;
            align-items: flex-end;
        }

        .main-container {
            min-height: calc(100vh - 82px);
            height: calc(100vh - 82px);
        }

        .sidebar {
            top: auto;
            right: 10px;
            bottom: 10px;
            left: 10px;
            width: auto;
            max-height: 46%;
            padding: 10px;
            gap: 8px;
        }

        .card {
            padding: 10px;
        }

        .card h3 {
            margin-bottom: 8px;
        }

        .card p {
            margin: 5px 0;
        }
    }
    """, media_type="text/css")


@app.get("/api/telemetry")
def get_telemetry(outage: bool = False, lat: float = Query(None), lon: float = Query(None), heading: float = Query(None)):
    global cutoff_started_at

    elapsed = int(time.time() - start_time) % 60
    auto_cutoff = (elapsed >= 8 and elapsed <= 18)
    outage_active = bool(outage) or auto_cutoff

    if outage_active and cutoff_started_at is None:
        cutoff_started_at = elapsed
    elif not outage_active:
        cutoff_started_at = None

    incoming_gps = (lat, lon) if lat is not None and lon is not None else None
    data = sim.run_simulation_step(elapsed, outage_active=outage_active, incoming_gps=incoming_gps, phone_heading=heading)

    data["signal_cutoff"] = outage_active
    data["signal_cutoff_time"] = f"00:{cutoff_started_at:02d}" if outage_active and cutoff_started_at is not None else None
    data["dead_reckoning_active"] = outage_active
    data["dead_reckoning_mode"] = "AUTO" if outage_active else "STANDBY"
    data["gnss_lost"] = outage_active

    return data