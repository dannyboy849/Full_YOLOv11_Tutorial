"""
src/evaluation/edge_evaluator.py
"""

import numpy        as np

from edge_metrics   import EdgeMetrics


class EdgeEvaluator:

    def __init__(
        self,
        controller,
        battery,
        interpolator,
        sampler
    ):

        self.controller     = controller
        self.battery        = battery
        self.interpolator   = interpolator
        self.sampler        = sampler


    def evaluate(
        self,
        origin,
        destination,
        weather
    ):

        cases = self.sampler.sample(weather)
        reports = []

        for case in cases:
            wind = self.interpolator.interpolate(
                (origin, destination),
                case
            )
            report = self.controller.simulate(
                origin,
                destination,
                wind
            )
            reports.append(report)

        if hasattr(self.sampler, "probabilities"):
            probabilities = self.sampler.probabilities
        elif hasattr(self.sampler, "get_probabilities"):
            probabilities = self.sampler.get_probabilities(cases)
        else:
            probabilities = [1.0 / len(reports)] * len(reports)
        return self.aggregate(reports)
    

def aggregate(self, reports, probabilities) -> EdgeMetrics:

    if not reports:
        # unfeasible fallback
        return EdgeMetrics(
            energy=float('inf'), flight_time=float('inf'), risk=1.0, 
            stability=0.0, control_effort=float('inf'), battery_margin=0.0, feasible=False
        )

    # normalize probability weights arrays to guarantee a cumulative sum of exactly 1.0
    weights = np.array(probabilities, dtype=float)
    weights /= weights.sum()

    # extract and compile parameters across all 10 wind rose tracking runs
    avg_energy         = float(np.sum([r.energy * w for r, w in zip(reports, weights)]))
    avg_flight_time    = float(np.sum([r.flight_time * w for r, w in zip(reports, weights)]))
    avg_risk           = float(np.sum([r.risk * w for r, w in zip(reports, weights)]))
    avg_stability      = float(np.sum([r.stability * w for r, w in zip(reports, weights)]))
    avg_control_effort = float(np.sum([r.control_effort * w for r, w in zip(reports, weights)]))
    avg_bat_margin     = float(np.sum([r.battery_margin * w for r, w in zip(reports, weights)]))
    
    global_feasibility = all([r.feasible for r in reports])

    return EdgeMetrics(
        energy         = avg_energy,
        flight_time    = avg_flight_time,
        risk           = avg_risk,
        stability      = avg_stability,
        control_effort = avg_control_effort,
        battery_margin = avg_bat_margin,
        feasible       = global_feasibility
    )

# def aggregate(

#     self,

#     reports,

#     probabilities

# ):

#     total = 0

#     for p, report in zip(

#         probabilities,

#         reports

#     ):

#         total += p * report.energy

#     return total