"""
src/control/edge_runner.py
"""

import numpy as np

from src.planning.mission         import Mission


class EdgeRunner:

    def __init__(self, controller, planner, battery, weather):
        self.controller = controller
        self.planner = planner
        self.battery = battery
        self.weather = weather


    # def evaluate_edge_under_wind(self, origin, destination, month, wind_case_vector):
    #     """
    #     runs the MPC simulation over a specific graph edge under a wind vector
    #     """
    #     mission = Mission(
    #         origin=origin,
    #         destination=destination,
    #     )

    #     mission.current_weather = wind_case_vector

    #     mission = self.planner.plan(mission)

    #     result = self.controller.run(
    #         mission.reference_trajectory
    #     )

    #     return result


def aggregate(metrics_list):
    """
    aggregates a list of dictionaries or objects containing mission metrics.
    """
    if not metrics_list:
        return {}

    # convert objects to dictionaries
    normalized = [
        m.__dict__ if hasattr(m, "__dict__") else m 
        for m in metrics_list
    ]
    
    aggregated = {}
    # use the keys from the first entry as the template
    all_keys = normalized[0].keys()

    for key in all_keys:
        # extract all values for this specific metric key across all cases
        values = [run[key] for run in normalized if key in run]
        
        if not values:
            continue

        # process numerical fields
        if isinstance(values[0], (int, float)):
            aggregated[key] = {
                "avg": float(np.mean(values)),
                "min": float(np.min(values)),
                "max": float(np.max(values)),
                "std": float(np.std(values))
            }
        # process structural fields
        elif isinstance(values[0], (list, np.ndarray)) and isinstance(values[0][0], (int, float)):
            aggregated[key] = {
                "mean_profile": np.mean(values, axis=0).tolist(),
                "p95_profile": np.percentile(values, 95, axis=0).tolist()
            }
        # process metadata fields
        else:
            unique_vals = list(set(values))
            aggregated[key] = unique_vals[0] if len(unique_vals) == 1 else unique_vals

    return aggregated