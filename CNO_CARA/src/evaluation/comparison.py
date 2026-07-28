"""
src/control/comparison.py

builds and runs the MPC controller for a given linear model and MLP residual,
then compares the results to the actual flight log

called by: run_pipeline.py

"""

import numpy as np

from pathlib                import Path
from control.plant          import make_casadi_symbolic_plant
from control.model          import _make_do_mpc_model
from control.battery        import BatteryModel
from simulation.runner      import _run_loop
from control.controller     import _build_mpc, _make_tvp_fun
from control.wind_model     import build_wind_disturbance
from control.bundle_loader  import mlp_to_casadi, _load_bundle
from control.feature_mapper import FeatureMapper


def run_mpc_comparison(cfg, df_test,
                       state_vars: list, input_vars: list,
                       feature_spec: dict, mlp_model, scaler_X, scaler_y,
                       sigma_bounds: np.ndarray | None = None,
                       best_model_obj=None,
                       df_train=None, feature_list=None, residual_targets=None):

    save_dir = Path(cfg.paths.plots)
    (A, B,
    x0,
    ref_traj,
    u_min, u_max,
    dT,
    sv, iv,
    W_diag,
    phi_mean, phi_std,
    residual_model
    )           = _load_bundle(cfg.paths.mpc_bundle)

    spec = feature_spec if feature_spec is not None else {}
    mapper      = FeatureMapper(spec)
    n_x         = A.shape[0]
    x_mean      = phi_mean[:n_x]
    x_std       = phi_std[:n_x]
    u_mean      = phi_mean[n_x:]
    u_std       = phi_std[n_x:]

    x0          = np.array(x0, dtype=float)
    clip_limits = {

        "bar_alt":       (-10, 1000),
        "bar_cr":        (-20, 20),

        "x_speed":       (-50, 50),
        "y_speed":       (-50, 50),
        "z_speed":       (-20, 20),

        "att_act_roll":  (-60, 60),
        "att_act_pitch": (-60, 60),
        "att_act_yaw":   (-180, 180),

    }

    for i,name in enumerate(state_vars):
        if name in clip_limits:
            lo,hi = clip_limits[name]
            x0[i] = np.clip(x0[i], lo, hi)

    print(f"[hub_placement] x0 (clipped): {x0.round(3)}")

    # filter pre-arm rows from df_test
    motor_cols = [c for c in input_vars if c in df_test.columns]
    if motor_cols:
        pre_arm_mask    = df_test[motor_cols].max(axis=1) > 1050
        n_before        = len(df_test)
        df_test         = df_test[pre_arm_mask].reset_index(drop=True)
        print(f"[hub_placement] Pre-arm filter: {n_before - len(df_test)} rows removed, "
            f"{len(df_test)} remaining")
    
    Tsim         = min(len(ref_traj), getattr(cfg.mpc, 'n_sim_steps', 500))
    n_u          = B.shape[1]
    N_h          = getattr(cfg.mpc, 'horizon',      15)
    Q_diag       = list(getattr(cfg.mpc, 'Q_weights', [1.0]*n_x))
    R_diag       = [getattr(cfg.mpc, 'R_weight',    0.1)] * n_u
    alpha        = float(getattr(cfg.mpc, 'sigma_alpha', 2.0))
    beta_val     = float(getattr(cfg.mpc, 'beta',    1.0))
    gamma_val    = float(getattr(cfg.mpc, 'gamma',   0.0))
    mu_bat       = float(getattr(cfg.mpc, 'mu_bat',  10.0))
    mu_state     = float(getattr(cfg.mpc, 'mu_state', 1.0))

    # actual battery: 10000 mAh LiPo
    bat_capacity = float(getattr(cfg.mpc, 'battery_mah', 10000.0))
    v_nominal    = float(getattr(cfg.mpc, 'v_nominal',     22.2))
    battery      = BatteryModel(capacity_mah=bat_capacity, v_nominal=v_nominal)

    if 'bat_eng-t' in df_test.columns:
        energy_used_j   = float(df_test['bat_eng-t'].iloc[0])
        soc0            = max(0.0, 1.0 - (energy_used_j / battery.capacity_j))
        print(f"[hub_placement] Initial SoC from log: {soc0*100:.1f}%")
    else:
        soc0 = 1.0
    battery.reset(soc0=soc0)

    # power from telemetry 
    # priority 1: direct power column
    if 'power_w' in df_test.columns:
        power_traj = df_test['power_w'].values[:Tsim]

    # priority 2: compute from volt * current
    elif 'bat_volt' in df_test.columns and 'bat_cur' in df_test.columns:
        power_traj = (df_test['bat_volt'].values *
                    df_test['bat_cur'].values)[:Tsim]
        print(f"[hub_placement] Power from telemetry: {power_traj.mean():.1f}W avg")

    # priority 3: ESC-level
    elif all(c in df_test.columns for c in ['esc11_volt','esc11_cur']):
        p1 = df_test['esc11_volt'].values * df_test['esc11_cur'].values
        p2 = df_test['esc8_volt'].values  * df_test['esc8_cur'].values
        power_traj = (p1 + p2) * 2   # extrapolate 2 ESCs → 4 motors
        print(f"[hub_placement] Power from ESC telemetry: {power_traj.mean():.1f}W avg")

    else:
        print("[hub_placement] No battery telemetry found — using PWM proxy")
        power_traj = None
        
    # wind disturbance
    wind_traj = np.zeros((len(df_test), len(state_vars)))
    has_wind = "wind_x" in df_test.columns and "wind_y" in df_test.columns
    if has_wind:
        for k, row in enumerate(df_test.itertuples()):
            wind_traj[k] = build_wind_disturbance(
                wind_x=getattr(row, 'wind_x'), 
                wind_y=getattr(row, 'wind_y'), 
                state_vars=state_vars,
            )
    else:
        print("[hub_placement] No wind columns found — using zero wind disturbance.")
    print("wind_traj shape =", wind_traj.shape)

    casadi_residual_fn = mlp_to_casadi(best_model_obj, name="mlp_residual")

    # using the high-efficiency piecewise symbolic compiler template
    sim_plant = make_casadi_symbolic_plant(
        casadi_mlp_fn = casadi_residual_fn,
        mapper        = mapper, # provides structural map conversion to 28 variables
        A = A,      B = B,
        x_mean = x_mean, x_std = x_std,
        u_mean = u_mean, u_std = u_std,
        wind_traj     = wind_traj
    )

    # state constraint bounds
    u_hover = np.percentile(df_test[input_vars].values, 50, axis=0)
    c_bounds = np.array([1.2 * np.nanmax(np.abs(df_test[s].values)) for s in state_vars])

    # CasADi residual from MLP
    casadi_residual = None
    if best_model_obj is not None:
        casadi_residual = mlp_to_casadi(best_model_obj, "mlp_residual")
        if casadi_residual is None:
            print("[hub_placement] Linear model, so no CasADi residual. "
                  "HPO uses linear internal model + MLP plant.")

    # scaler_X statistics for CasADi MLP normalisation
    feat_sx_mean = scaler_X.mean_
    feat_sx_std  = scaler_X.scale_

    results = {}



    # --------------------------------------------------
    # ── hub placement optimization (HPO) ──────────────
    # --------------------------------------------------

    print("[hub_placement] ── Running HPO ──")
    full_bat    = BatteryModel(capacity_mah=bat_capacity, v_nominal=v_nominal)

    model_full = _make_do_mpc_model(
        A, B, x_mean=x_mean, x_std=x_std, u_mean=u_mean, u_std=u_std,
        casadi_residual=casadi_residual,
        feat_scaler_mean=feat_sx_mean,
        feat_scaler_std=feat_sx_std,
        use_wind=True
    )
    
    mpc_full = _build_mpc(
        model_full, A, B, dT, N_h, u_min, u_max,
        Q_diag, R_diag,
        beta=beta_val,
        gamma=gamma_val,
        mu_bat=mu_bat,
        mu_state=mu_state,
        u_hover=u_hover
    )

    mpc_full.set_tvp_fun(
        _make_tvp_fun(
            mpc_full, 
            ref_traj, 
            dT, 
            N_h, 
            power_traj=power_traj,
            wind_traj=wind_traj,
            use_wind=True
        )
    )

    p_template_full = mpc_full.get_p_template(1)


    def p_fun_full(_):
        p_template_full['_p', 0, 'tightened_bounds'] = np.full((n_x, 1), 10.0)
        p_template_full['_p', 0, 'mu_state']         = np.array([[mu_state]])
        return p_template_full
    mpc_full.set_p_fun(p_fun_full)
    mpc_full.setup()

    full_solve_times = []

    # execute the updated run loop tracking telemetry using the compiled fast plant
    results['HPO'] = _run_loop(
        mpc             = mpc_full, 
        x0_init         = x0, 
        plant_fn        = sim_plant,
        A    = A,    B  = B,
        solve_time_hist = full_solve_times,
        Tsim = Tsim, dT = dT,
        wind_traj       = wind_traj,
        battery         = battery,
        power_traj      = power_traj,
        W_diag          = W_diag,
        sigma_bounds    = sigma_bounds,
        ref_traj        = ref_traj,
        c_bounds        = c_bounds,
        residual_model  = best_model_obj,
        alpha           = alpha,
        mu_bat          = mu_bat,
        mu_state        = mu_state
    )

    return results
