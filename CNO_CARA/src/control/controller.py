"""
src/control/controller.py

build and save MPC bundle for later use in run_mpc_comparison.py

"""

import numpy    as np
import casadi   as ca
import do_mpc


def _build_mpc(model, A, B, dT, N_h, u_min, u_max,
            Q_diag, R_diag,
            beta=1.0, gamma=0.0,
            mu_bat=0.0, mu_state=0.0,
            u_hover=None):
    """
    nuild and configure the MPC controller

    cost (stage):
      ‖x - x_ref‖²_Q                  tracking
    + β ‖u - u_hover‖²_R              control effort / hover deviation
    + γ · P_ref                       energy penalty
    + μ_bat · ρ_bat(SoC)              TVP SoC
    + μ_state · ρ_state(x)            tightened Q

    control-rate constraint |Δu| ≤ Δu_max prevents current spikes
    """
    n_u = B.shape[1]
    if u_hover is None:
        u_hover = np.full(
            n_u,
            1500.0
        )

    mpc = do_mpc.controller.MPC(model)
    mpc.set_param(
        n_horizon=N_h, 
        t_step=dT, 
        store_full_solution=False,
        nlpsol_opts={
            'ipopt.max_iter': 500,
            'ipopt.tol': 1e-4,          # looser tolerance
            'ipopt.nlp_scaling_method': 'gradient-based',
            'ipopt.print_level': 0,     # suppress output
        }
    )

    x       = model.x['x']
    u       = model.u['u']
    xr      = model.tvp['xr']
    pw_ref  = model.tvp['power_ref']

    n_x     = A.shape[0]

    Q_diag  = np.asarray(Q_diag, dtype=float)

    if Q_diag.shape[0] != n_x:
        Q_diag = np.pad(Q_diag, (0, max(0, n_x - len(Q_diag))), constant_values=1.0)
        Q_diag = Q_diag[:n_x]

    Q       = np.diag(Q_diag)
    R       = np.diag(R_diag)

    u_hov   = ca.SX(u_hover.reshape(-1, 1))
    x_diff  = x - xr 
    u_diff  = u - u_hov 

    # input bounds
    for i in range(n_u):
        mpc.bounds['lower', '_u', 'u'][i] = u_min[i]
        mpc.bounds['upper', '_u', 'u'][i] = u_max[i]
        
    track_cost  = x_diff.T @ ca.SX(Q) @ x_diff
    effort_cost = beta  * (u_diff.T @ ca.SX(R) @ u_diff)
    energy_cost = (gamma * pw_ref) 

    # violations in CasADi
    x_err       = ca.fabs(model.x['x'] - model.tvp['xr'])
    violation   = ca.fmax(0.0, x_err - model.p['tightened_bounds'])

    # soft constraint penalty to lterm
    state_risk_cost = model.p['mu_state'] * ca.dot(violation, violation)

    lterm = track_cost + effort_cost + energy_cost + state_risk_cost
    mpc.set_objective(lterm=lterm, mterm=ca.SX(0))
    mpc.set_rterm(u=1e-4)  # soft rate penalty

    return mpc


def _make_tvp_fun(mpc: do_mpc.controller.MPC,
                  ref_traj: np.ndarray,
                  dT: float, N_h: int,
                  power_traj = None,
                  wind_traj  = None,
                  use_wind   = False) -> callable:
    """
    time-varying parameter function.
    maps elapsed time → correct reference row index.
    uses int(round(t_now/dT))
    """
    n_x = ref_traj.shape[1]


    def tvp_fun(t_now):
        tvp_arr = mpc.get_tvp_template()
        t_scaler = float(np.asarray(t_now).item())
        step = int(round(t_scaler / dT + 1e-9))

        for h in range(N_h + 1):
            idx = min(step + h, ref_traj.shape[0] - 1)

            # state reference (9, 1)
            tvp_arr['_tvp', h, 'xr'] = ref_traj[idx].reshape(-1, 1)

            # power reference (1, 1)
            pw = float(power_traj[min(idx, len(power_traj) - 1)]) \
                    if power_traj is not None else 0.0
            tvp_arr['_tvp', h, 'power_ref'] = np.array([[pw]])

            # wind disturbance profile (9, 1)
            if use_wind:
                wv = wind_traj[idx] if wind_traj is not None else np.zeros(n_x)
                tvp_arr['_tvp', h, 'wind'] = wv.flatten().reshape(-1,1)

        return tvp_arr
    return tvp_fun