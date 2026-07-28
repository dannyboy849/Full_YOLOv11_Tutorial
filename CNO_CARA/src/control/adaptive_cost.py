"""
src/control/adaptive_cost.py
"""

import numpy    as np

from casadi     import SX, vertcat, diag


def get_adaptive_vtol_weights(phase_sym: SX):
    """
    generates dynamic state tracking penalties (Q) and control effort penalties (R)
    inside the symbolic CasADi graph based on the integer flight phase
    
    0 = Ground | 1 = Takeoff | 2 = Cruise | 3 = Fixed-Wing | 4 = Landing
    """
    # baseline diagonal vectors for tracking states 

    ####### temporarily removed IMU bc of intense noise; TBD later #######
    # [alt, cr, x_speed, y_speed, z_speed, pitch, roll, yaw_sin, yaw_cos, imu_x, imu_y, imu_z] 
    q_base      = [20.0, 15.0, 10.0, 10.0, 15.0, 10.0, 10.0, 1.0, 1.0]#, 0.1, 0.1, 0.1]
    
    # baseline input vectors [RCOU_1, RCOU_2, RCOU_3, RCOU_4, RCOU_5]
    r_base      = [0.1, 0.1, 0.1, 0.1, 0.1]

    # conditional scaling rules using CasADi symbolic if_else statements
    # strict ground behavior to penalize all movements to keep vehicle flat on the pad
    is_ground   = (phase_sym == 0)
    q_ground    = [50.0, 20.0, 50.0, 50.0, 50.0, 100.0, 100.0, 10.0, 10.0]

    # critical vertical transitions: heavily penalize tracking drift and attitude tilt
    is_critical = (phase_sym == 1) | (phase_sym == 4)
    q_critical  = [100.0, 50.0, 20.0, 20.0, 40.0, 80.0, 80.0, 5.0, 5.0]
    r_critical  = [0.5, 0.5, 0.5, 0.5, 0.5] # Dampen actuator spikes near the ground

    # assemble vectors conditionally inside the symbolic graph
    q_adapted   = q_base
    r_adapted   = r_base

    # layer conditions
    for idx in range(len(q_base)):
        q_adapted[idx] = SX.if_else(is_ground, q_ground[idx], 
                                   SX.if_else(is_critical, q_critical[idx], q_base[idx]))
        
    for idx in range(len(r_base)):
        r_adapted[idx] = SX.if_else(is_critical, r_critical[idx], r_base[idx])

    # convert arrays to explicit symbolic diagonal matrices
    Q = diag(vertcat(*q_adapted))
    R = diag(vertcat(*r_adapted))
    
    return Q, R


def adaptive_cost_weights(
    residual,
    flight_phase = None
):
    """
    dynamically update MPC penalties
    using residual magnitude
    """

    r = float(
        np.linalg.norm(residual)
    )

    # starting value weights
    beta        = 1.0
    gamma       = 2.0

    if r < 0.03:
        beta   *= 0.5
        gamma  *= 2.0

    elif r < 0.10:
        beta   *= 1.0
        gamma  *= 1.5

    else:
        beta   *= 3.0
        gamma  *= 0.5

    if flight_phase == 1:
        beta   *= 2.0

    if flight_phase == 4:
        beta   *= 3.0

    return beta, gamma


def select_horizon(
    residual
):

    r = float(
        np.linalg.norm(residual)
    )

    if r < 0.03:
        return 5

    elif r < 0.10:
        return 10

    return 20


def soc_risk_penalty(soc: float, soc_risk: float = 0.35) -> float:
    """quadratic penalty activating below soc_risk threshold."""
    return max(0.0, soc_risk - soc) ** 2


def state_risk_penalty(x: np.ndarray, x_ref: np.ndarray,
                       c: np.ndarray, sigma: np.ndarray,
                       alpha: float = 2.0) -> float:
    """sum of quadratic penalties for tightened constraint violations."""
    tightened  = c - alpha * sigma
    violations = np.maximum(0.0, np.abs(x - x_ref) - tightened)
    clipped_violations = np.clip(violations, -1e5, 1e5)

    return float(np.sum(clipped_violations ** 2))