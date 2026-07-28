"""
src/simulation/runner.py

runs the closed-loop simulation with the MPC controller and MLP residual,
then compares the results to the actual flight log

called by: run_pipeline.py

"""

import time
import numpy                as np
import do_mpc

from control.battery        import BatteryModel, estimate_power
from control.residual       import ResidualGate
from control.adaptive_cost  import state_risk_penalty, soc_risk_penalty, adaptive_cost_weights



# --------------------------------------------------
# ── closed-loop simulation loop ───────────────────
# --------------------------------------------------

print("Starting simulation loop...")

def _run_loop(mpc: do_mpc.controller.MPC,
              x0_init: np.ndarray,
              plant_fn: callable,
              A, B,
              solve_time_hist: list,
              Tsim: int, dT: float,
              wind_traj: np.ndarray | None,
              battery: BatteryModel,
              power_traj: np.ndarray | None,
              W_diag: np.ndarray | None,
              sigma_bounds: np.ndarray | None,
              ref_traj: np.ndarray,
              c_bounds: np.ndarray,
              residual_model = None,
              alpha: float = 2.0,
              mu_bat: float = 0.0,
              mu_state: float = 0.0) -> dict:
    """
    run the closed-loop simulation tracking energy, SoC, and risk profiles.
    """
    battery.reset()
    battery._elapsed = 0.0

    # initialize the tracking gate
    gate = ResidualGate(low_thresh=0.03, med_thresh=0.10)

    # array copy initialization
    x0 = np.asarray(x0_init, dtype=float).reshape(-1, 1).copy()
    mpc.x0 = x0
    mpc.set_initial_guess()

    x_hist          = []
    u_hist          = []
    power_hist      = []
    soc_hist        = []
    energy_hist     = []
    endurance_hist  = []
    risk_hist       = []
    mode_hist       = []  # track operational modes over the flight path
    cumulative_p    = 0.0

    p_template = mpc.get_p_template(1)

    for k in range(Tsim):

        # 1. MPC solver
        x0_numeric = np.asarray(x0, dtype=float).flatten()
        residual_est = np.zeros_like(x0_numeric)

        if residual_model is not None:
            try:
                # predict using the numeric flattened state vector
                pred = residual_model.predict(x0_numeric.reshape(1, -1))
                residual_est = np.asarray(pred, dtype=float).flatten()
            except Exception:
                pass

        # query the gate for controller aggressiveness mode
        current_mode = gate.get_mode(residual_est)
        mode_hist.append(current_mode)

        # adaptive parameter scaling based on gated mode
        if current_mode == "steady":
            # low computation / loose penalty: relax constraints to prevent solver hunting
            dynamic_mu_state = mu_state * 0.5
            envelope_scalar = 1.1
        elif current_mode == "normal":
            # nominal operational behavior
            dynamic_mu_state = mu_state
            envelope_scalar = 1.0
        else:  # "aggressive"
            # strong disturbance rejection: heavily penalize deviations, tighten bounds
            dynamic_mu_state = mu_state * 5.0
            envelope_scalar = 0.85

        # tightened flight envelope boundaries
        sigma = sigma_bounds if sigma_bounds is not None else np.zeros_like(c_bounds)
        current_tightened_envelopes = (c_bounds - (alpha * sigma)) * envelope_scalar

        # update do-mpc parametric templates natively
        p_template['_p', 0, 'tightened_bounds'] = current_tightened_envelopes.reshape(-1, 1)
        
        r_norm = float(np.linalg.norm(residual_est))
        p_template['_p', 0, 'mu_state']         = np.array([[dynamic_mu_state * (1.0 + 10.0 * r_norm)]])

        # overwrite parameter callback handle safely
        mpc.set_p_fun(lambda _: p_template)

        # trigger a single optimization loop check per step using clean numeric input
        t0 = time.perf_counter()
        u0 = mpc.make_step(x0_numeric.reshape(-1, 1))
        solve_ms = (time.perf_counter() - t0) * 1000
        solve_time_hist.append(solve_ms)
        

        # cast output back to a numeric flat NumPy vector
        u_flat = np.asarray(u0, dtype=float).flatten()

        # 2. plant step
        # pass arrays to the physics sim plant
        x_next_raw = plant_fn(x0_numeric, u_flat)
        x0 = np.asarray(x_next_raw, dtype=float).reshape(-1, 1)
        xk = x0.flatten()

        # 3. reference
        xr_k = ref_traj[min(k, len(ref_traj) - 1)]

        # 4. sigma
        sigma = sigma_bounds if sigma_bounds is not None else np.zeros_like(xr_k)

        # 5. align dimensions 
        n = min(len(c_bounds), len(sigma), len(xr_k), len(xk))

        # 6. state risk 
        r_state = mu_state * state_risk_penalty(
            xk[:n],
            xr_k[:n],
            c_bounds[:n],
            sigma[:n],
            alpha
        )

        #  7. wind risk 
        wind_safe_limit = 5.0
        wind_mag = np.linalg.norm(wind_traj[k])
        wind_risk = (max(0.0, wind_mag - wind_safe_limit) / wind_safe_limit) ** 2

        #  8. energy model 
        p_w, i_a = estimate_power(u_flat, power_traj, k, W_diag, battery.v_nominal)
        bat_state = battery.step(p_w, i_a, dT)
        battery._elapsed = (k + 1) * dT

        cumulative_p += p_w
        avg_p = cumulative_p / (k + 1)

        #  9. battery risk 
        r_bat = mu_bat * soc_risk_penalty(bat_state['soc'])

        #  10. logging 
        x_hist.append(xk)
        u_hist.append(u_flat)
        power_hist.append(p_w)
        soc_hist.append(bat_state['soc'])
        energy_hist.append(bat_state['energy_j'])
        endurance_hist.append(battery.endurance_remaining(avg_p))
        risk_hist.append(r_bat + r_state + 0.25 * wind_risk)

    return {
        'x_hist':          np.array(x_hist),
        'u_hist':          np.array(u_hist),
        'power_hist':      np.array(power_hist),
        'soc_hist':        np.array(soc_hist),
        'energy_hist':     np.array(energy_hist),
        'endurance_hist':  np.array(endurance_hist),
        'risk_hist':       np.array(risk_hist),
        'solve_time_hist': np.array(solve_time_hist),
        'mode_hist':       np.array(mode_hist) 
    }