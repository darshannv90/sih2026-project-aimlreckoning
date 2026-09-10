from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
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

@app.get("/api/telemetry")
def get_telemetry(outage: bool = True, lat: float = Query(None), lon: float = Query(None), heading: float = Query(None)):
    elapsed = int(time.time() - start_time) % 60
    incoming_gps = (lat, lon) if lat and lon else None
    data = sim.run_simulation_step(elapsed, outage_active=outage, incoming_gps=incoming_gps, phone_heading=heading)
    return data