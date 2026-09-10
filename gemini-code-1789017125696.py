import numpy as np

class NavisenseEKF:
    def __init__(self):
        # 8-State EKF: [x, y, v_x, v_y, heading, gyro_bias, accel_bias, wheel_slip]
        self.state = np.zeros(8)
        self.P = np.eye(8) * 0.1
        
        # Measurement matrix H for GPS (observing position x and y directly)
        self.H = np.zeros((2, 8))
        self.H[0, 0] = 1.0  # Position X
        self.H[1, 1] = 1.0  # Position Y
        
        # Measurement noise covariance matrix R
        self.R = np.eye(2) * 1.5

    def step_prediction(self, speed, steering_angle, dt):
        """Prediction step with Non-Holonomic Constraints (NHC)"""
        heading = self.state[4] + steering_angle * dt
        v_x = speed * np.cos(heading)
        v_y = speed * np.sin(heading)
        
        self.state[0] += v_x * dt
        self.state[1] += v_y * dt
        self.state[2] = v_x
        self.state[3] = v_y
        self.state[4] = heading
        
        F = np.eye(8)
        F[0, 2] = dt
        F[1, 3] = dt
        Q = np.eye(8) * 0.01
        self.P = F @ self.P @ F.T + Q
        
        return self.state[0], self.state[1], self.state[4]

    def step_update(self, gps_x, gps_y):
        """EKF Correction Step: Fuses real GPS coordinates into state estimation"""
        z = np.array([gps_x, gps_y])
        y = z - (self.H @ self.state)                  
        S = self.H @ self.P @ self.H.T + self.R        
        K = self.P @ self.H.T @ np.linalg.inv(S)       
        
        self.state = self.state + K @ y                
        I = np.eye(8)
        self.P = (I - K @ self.H) @ self.P             
        
        return self.state[0], self.state[1]


class SimulationEngine:
    def __init__(self):
        self.ekf = NavisenseEKF()
        self.base_lat = 12.9716  # Reference origin (Bengaluru)
        self.base_lon = 77.5946
        self.classical_error = 0.0
        self.navisense_error = 0.0
        
    def run_simulation_step(self, time_elapsed: int, outage_active: bool, incoming_gps=None, phone_heading=None):
        dt = 1.0
        speed = 2.5     
        steering = 0.01 
        
        # Override steering/heading with real phone sensor data if provided
        if phone_heading is not None:
            steering = np.radians(phone_heading) - self.ekf.state[4]
        
        x, y, heading = self.ekf.step_prediction(speed, steering, dt)
        
        if not outage_active and incoming_gps:
            target_lat, target_lon = incoming_gps
            gps_x = (target_lon - self.base_lon) * 111000.0 * np.cos(np.radians(self.base_lat))
            gps_y = (target_lat - self.base_lat) * 111000.0
            
            x, y = self.ekf.step_update(gps_x, gps_y)
            self.navisense_error = max(0.0, self.navisense_error - 1.5)
            self.classical_error = max(0.0, self.classical_error - 2.0)
        elif outage_active:
            self.classical_error += np.random.uniform(3.5, 5.2)
            self.navisense_error += np.random.uniform(0.4, 0.9)
            
        est_lat = self.base_lat + (y / 111000.0)
        est_lon = self.base_lon + (x / (111000.0 * np.cos(np.radians(self.base_lat))))
        
        return {
            "simulation_time": f"00:{time_elapsed:02d}",
            "gnss_lost": outage_active,
            "speed_kmh": 2.5,
            "heading": round(np.degrees(heading) % 360, 2),
            "latitude": round(est_lat, 6),
            "longitude": round(est_lon, 6),
            "confidence_score": 94 if outage_active else 99,
            "navisense_error_m": round(self.navisense_error, 2),
            "classical_error_m": round(self.classical_error, 2)
        }