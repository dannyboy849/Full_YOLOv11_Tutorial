"""
src/control/residual.py

defines ResidualGate, which uses residual magnitude to determine controller aggressiveness

"""

import numpy as np


class ResidualGate:
    """
    uses residual magnitude to determine
    controller aggressiveness

    steady     -> low computation
    normal     -> nominal MPC
    aggressive -> disturbance rejection
    """

    def __init__(
        self,
        low_thresh  = 0.03,
        med_thresh  = 0.10
    ):
        self.low = low_thresh
        self.med = med_thresh

    def get_mode(self, residual):

        r = float(
            np.linalg.norm(residual)
        )

        if r < self.low:
            return "steady"

        elif r < self.med:
            return "normal"

        return "aggressive"