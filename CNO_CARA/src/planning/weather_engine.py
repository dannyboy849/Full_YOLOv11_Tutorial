"""
src/planning/weather_engine.py
"""

import sys
import math
import numpy                    as np

from pathlib                    import Path
from rft_engine                 import (predict_power_for_ground_speed_w, predict_vtol_power_w)
from dataclasses                import dataclass
from control.adaptive_cost      import state_risk_penalty


# requirements for CARA
sys.path.insert(0, str(Path(__file__).parent / "src"))
assert sys.version_info >= (3, 12), "This script requires Python 3.12+"


@dataclass
class PhysicsInformedWeatherEngine:
    def __init__(self, mlp, linear, s_X, s_y, sigmas, aero_config):
        self.mlp = mlp
        self.linear = linear
        self.scaler_X = s_X
        self.scaler_y = s_y
        self.sigma_bounds = sigmas
        self.aero_config = aero_config
        
        # map standard wind rose alphanumeric bins directly to trigonometric angles (degrees)
        self.dir_map = {
            'N': 0.0,   'NNE': 22.5,  'NE': 45.0,  'ENE': 67.5,
            'E': 90.0,  'ESE': 112.5, 'SE': 135.0, 'SSE': 157.5,
            'S': 180.0, 'SSW': 202.5, 'SW': 225.0, 'WSW': 247.5,
            'W': 270.0, 'WNW': 292.5, 'NW': 315.0, 'NNW': 337.5, 'calm': 0.0
        }

    def representative_cases(self, position):
        """
        stochastically samples 10 distinct wind vector profiles [wind_x, wind_y]
        """
        # frequency distributions derived directly from table arrays
        # formatted as (Bin Name, Median Velocity Magnitude m/s, Normalized Probability Weight)
        scenarios = [
            ('calm', 0.0,  0.1339),
            ('ENE',  1.25, 0.0590), ('ENE', 3.75, 0.0062),
            ('E',    1.25, 0.0735), ('E',   3.75, 0.0179),
            ('ESE',  1.25, 0.0624), ('ESE', 3.75, 0.0213),
            ('SE',   1.25, 0.0507), ('SE',  3.75, 0.0164),
            ('NW',   1.25, 0.0558), ('NW',  3.75, 0.0121), ('NW', 6.25, 0.0010),
            ('NNW',  1.25, 0.0573), ('NNW', 3.75, 0.0109), ('NNW', 6.25, 0.0006),
            ('N',    1.25, 0.0437), ('N',   3.75, 0.0059)
        ]
        
        # extract attributes cleanly
        probs = np.array([s[2] for s in scenarios])
        probs /= probs.sum()
        
        # select 10 indices based on probability distributions
        selected_idx = np.random.choice(len(scenarios), size=10, p=probs)
        
        wind_vectors = []
        for idx in selected_idx:
            direction, velocity, _ = scenarios[idx]
            angle_rad = math.radians(self.dir_map[direction])
            
            # decompose the scalar wind velocity into orthogonal flight vectors
            wind_x = velocity * math.sin(angle_rad)
            wind_y = velocity * math.cos(angle_rad)
            wind_vectors.append(np.array([wind_x, wind_y]))
            
        return wind_vectors

    def evaluate_mpc_edge_cost(self, edge, wind_vector, phases):
        vec = np.asarray(wind_vector).flatten()
        wind_x, wind_y = float(vec[0]), float(vec[1])
        wind_speed_mps = float(np.linalg.norm(vec))
        wind_angle_deg = math.degrees(math.atan2(wind_y, wind_x))
        target_ground_speed = self.aero_config['rft_scenario']['target_ground_speed_mps']
        
        total_edge_energy_wh = 0.0

        for phase in phases:
            if phase in ["takeoff", "landing"]:
                p_vtol_w = predict_vtol_power_w(
                    lift_proxy=self.aero_config['rft_scenario']['vtol_lift_proxy'],
                    airspeed_mps=self.aero_config['rft_scenario']['vtol_airspeed_mps'],
                    params=self.aero_config,
                    pusher_proxy=self.aero_config['rft_scenario']['vtol_pusher_proxy']
                )
                phase_energy_wh = p_vtol_w * (60.0 / 3600.0)
            elif phase == "midflight":
                p_vtol_climb = predict_vtol_power_w(0.5, 12.0, self.aero_config, pusher_proxy=0.2)
                phase_energy_wh = p_vtol_climb * (90.0 / 3600.0)
            else:  # "cruise"
                p_fw_w = predict_power_for_ground_speed_w(target_ground_speed, wind_speed_mps, wind_angle_deg, self.aero_config)
                if not math.isfinite(p_fw_w):
                    return float("inf")
                cruise_distance_meters = 15.0 * 1609.34
                phase_energy_wh = p_fw_w * ((cruise_distance_meters / target_ground_speed) / 3600.0)

            # tracking_deviation_wh = ( 
            #     self.sigma_bounds *
            #     wind_speed_mps *
            #     state_risk_penalty
            # )
            tracking_deviation_wh = self.sigma_bounds * wind_speed_mps * 1.85 # if it doesn't work, use for temp

            total_edge_energy_wh += (phase_energy_wh + tracking_deviation_wh)

        return total_edge_energy_wh