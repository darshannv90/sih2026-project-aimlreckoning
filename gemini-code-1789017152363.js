const map = L.map('map').setView([12.9716, 77.5946], 15);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 }).addTo(map);

let outageActive = false;
let marker = L.marker([12.9716, 77.5946]).addTo(map);

// Polyline tracking setup
let pathCoordinates = [];
let trajectoryLine = L.polyline([], { color: '#58a6ff', weight: 4 }).addTo(map);

// Smartphone sensor input handling
let livePhoneHeading = null;
window.addEventListener('deviceorientation', (event) => {
    if (event.alpha !== null) {
        livePhoneHeading = event.alpha;
    }
});

function toggleOutage() {
    outageActive = !outageActive;
    const btn = document.getElementById('toggle-outage');
    const badge = document.getElementById('status-badge');
    
    if (outageActive) {
        btn.innerText = "Restore GNSS Signal";
        btn.className = "normal";
        badge.innerText = "GNSS SIGNAL LOST - AI EKF ACTIVE";
        badge.className = "badge lost";
    } else {
        btn.innerText = "Simulate GNSS Outage";
        btn.className = "";
        badge.innerText = "GNSS ACTIVE";
        badge.className = "badge active";
    }
}

async function fetchTelemetry() {
    try {
        let url = `http://127.0.0.1:8000/api/telemetry?outage=${outageActive}`;
        if (!outageActive) {
            url += `&lat=12.9716&lon=77.5946`;
        }
        if (livePhoneHeading !== null) {
            url += `&heading=${livePhoneHeading}`;
        }

        const response = await fetch(url);
        const data = await response.json();
        
        document.getElementById('speed').innerText = `${data.speed_kmh} km/h`;
        document.getElementById('heading').innerText = `${data.heading}°`;
        document.getElementById('confidence').innerText = `${data.confidence_score}%`;
        document.getElementById('nav-error').innerText = `${data.navisense_error_m} m`;
        document.getElementById('cls-error').innerText = `${data.classical_error_m} m`;
        
        const newLatLng = [data.latitude, data.longitude];
        marker.setLatLng(newLatLng);

        pathCoordinates.push(newLatLng);
        trajectoryLine.setLatLngs(pathCoordinates);

    } catch (e) {
        console.error("Backend offline:", e);
    }
}

setInterval(fetchTelemetry, 1000);