class SimulationEngine:
    def __init__(self):
        pass

    def run_simulation_step(self, elapsed, outage_active, incoming_gps):
        # Return a sample dictionary or data structure for your telemetry
        return {
            "elapsed": elapsed,
            "outage_active": outage_active,
            "gps": incoming_gps,
            "status": "Simulation step running successfully"
        }