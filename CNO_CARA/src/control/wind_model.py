"""
src/control/wind_model.py

builds a wind disturbance vector for the MPC controller

"""

import numpy as np


def build_wind_disturbance(
    wind_x,
    wind_y,
    state_vars):

    w = np.zeros(len(state_vars))

    if "x_speed" in state_vars:
        w[state_vars.index("x_speed")] = wind_x

    if "y_speed" in state_vars:
        w[state_vars.index("y_speed")] = wind_y

    return w