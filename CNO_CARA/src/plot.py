"""
src/plot.py
organizes data into the shapes utils/plots.py expects,
then calls each plot function in sequence

called by: DATUM.py  (after evaluate_model)
"""

import numpy as np
import plotly.graph_objects as go

from types        import SimpleNamespace
from pathlib      import Path
from utils.plots  import (
    plot_3d_flight_paths,
    plot_model_comparison,
    plot_rmse_comparison,
    plot_control_inputs,
    plot_attitude_tracking,
    plot_prediction_errors,
    plot_learning_curve,
    plot_gru_loss,
    plot_uncertainty_bands,
    plot_tracking,
)
from plotly.subplots import make_subplots


COLORS = {'HPO': 'orange', 'Linear': 'blue', 'Baseline': 'gray'}

# --------------------------------------------------
# ── helpers ───────────────────────────────────────
# --------------------------------------------------

def _inject_yaw_col(
    arr: np.ndarray,
    state_vars: list[str],
) -> tuple[np.ndarray, list[str]]:
    """
    ensures 'att_act_yaw' exists as a column so utils/plots.py
    line 441 (.index('att_act_yaw')) never raises ValueError

    Priority:
      1. att_act_yaw already present → return as-is
      2. yaw_sin + yaw_cos present  → reconstruct via arctan2
      3. neither                    → append zeros (silent fallback)
    """
    names = [s.lower() for s in state_vars]

    if "att_act_yaw" in names:
        return arr, state_vars

    if "yaw_sin" in names and "yaw_cos" in names:
        si      = names.index("yaw_sin")
        ci      = names.index("yaw_cos")
        yaw_deg = np.degrees(np.arctan2(arr[:, si], arr[:, ci]))
    else:
        yaw_deg = np.zeros(arr.shape[0])

    arr_out = np.concatenate([arr, yaw_deg[:, None]], axis=1)
    sv_out  = list(state_vars) + ["att_act_yaw"]
    return arr_out, sv_out



# --------------------------------------------------
# ── MPC tracking plots ────────────────────────────
# --------------------------------------------------

def run_mpc_tracking_plots(mpc_results, ref_traj, state_vars, save_dir):
    save_dir = Path(save_dir)
    if not mpc_results:
        print("[plot] No MPC results — skipping MPC tracking plots.")
        return
    for name, results in mpc_results.items():
        try:
            plot_tracking(
                results    = results,
                ref_traj   = ref_traj,
                state_vars = state_vars,
                name       = name,
                save_dir   = save_dir,
            )
        except Exception as e:
            print(f"[plot] Warning: plot_tracking failed for '{name}': {e}")



# --------------------------------------------------
# ── main plot runner ──────────────────────────────
# --------------------------------------------------

def run_plotly_dashboard(results, ref_traj, state_vars, input_vars, dT, bat_mah, v_nominal, save_dir: Path):
    """
    generates a single unified interactive HTML file combining:
    1. 4-Panel Energy Performance
    2. State Space Tracking vs Reference Trajectory
    3. Motor PWM Control Signals
    """
    save_dir = Path(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)
    
    # extract primary keys for calculation
    primary_key = 'HPO' if 'HPO' in results else list(results.keys())[0]
    Tsim = len(results[primary_key]['x_hist'])
    time_seq = np.arange(Tsim) * dT

    # ──────────────────────────────────────────────────────────
    # PANEL 1: 4-PANEL ENERGY DASHBOARD
    # ──────────────────────────────────────────────────────────
    fig_energy = make_subplots(rows=2, cols=2, subplot_titles=(
        'Instantaneous Power (W)', 'State of Charge (%)', 
        'Cumulative Energy (Wh)', 'Est. Remaining Endurance (min)'
    ))
    
    keys = ['power_hist', 'soc_hist', 'energy_hist', 'endurance_hist']
    scales = [1.0, 100.0, 1/3600.0, 1/60.0]
    positions = [(1,1), (1,2), (2,1), (2,2)]
    
    for key, sc, (r, c) in zip(keys, scales, positions):
        for name, res in results.items():
            arr = res.get(key, np.zeros(Tsim)) * sc
            fig_energy.add_trace(go.Scatter(
                x=time_seq, y=arr[:Tsim], mode='lines',
                name=f"{name} ({key.split('_')[0]})",
                line=dict(color=COLORS.get(name, 'purple'), width=1.5)
            ), row=r, col=c)

    # theoretical maximum capacity horizon line
    capacity_wh = (bat_mah / 1000.0) * v_nominal
    estimated_nominal_cruise_power_w = 350.0
    theoretical_max_endurance_minutes = (capacity_wh / estimated_nominal_cruise_power_w) * 60.0

    fig_energy.add_shape(
        type="line", x0=0, x1=time_seq[-1], 
        y0=theoretical_max_endurance_minutes, y1=theoretical_max_endurance_minutes,
        line=dict(color="Red", width=1.2, dash="dash"), 
        row=2, col=2
    )

    fig_energy.update_layout(title_text=f"Energy Analysis — {bat_mah/1000:.1f}Ah / {v_nominal}V LiPo",
                             hovermode="x unified", plot_bgcolor="white")
    fig_energy.write_html(save_dir / "plotly_energy_analysis.html")

    # ──────────────────────────────────────────────────────────
    # panel 2: state tracking performance
    # ──────────────────────────────────────────────────────────
    n_states = len(state_vars)
    fig_track = make_subplots(rows=n_states, cols=1, shared_xaxes=True, subplot_titles=state_vars)
    
    for i in range(n_states):
        # red dashed baseline reference path
        fig_track.add_trace(go.Scatter(
            x=time_seq, y=ref_traj[:Tsim, i], mode='lines',
            name=f'Ref: {state_vars[i]}', line=dict(color='red', width=1.5, dash='dash')
        ), row=i+1, col=1)
        
        for name, res in results.items():
            xh = res['x_hist']
            if i < xh.shape[1]:
                fig_track.add_trace(go.Scatter(
                    x=time_seq, y=xh[:Tsim, i], mode='lines',
                    name=f'{name}: {state_vars[i]}', line=dict(color=COLORS.get(name, 'purple'), width=1.2)
                ), row=i+1, col=1)
                
    fig_track.update_layout(title_text="HPO State Tracking Comparison", hovermode="x unified", height=180*n_states, plot_bgcolor="white")
    fig_track.write_html(save_dir / "plotly_state_tracking.html")

    # ──────────────────────────────────────────────────────────
    # panel 3: motor command actuation signal
    # ──────────────────────────────────────────────────────────
    u_dat = results[primary_key]['u_hist']
    n_u = u_dat.shape[1]
    fig_motors = make_subplots(rows=int(np.ceil(n_u/2)), cols=2, shared_xaxes=True)
    
    for i in range(n_u):
        row_idx = (i // 2) + 1
        col_idx = (i % 2) + 1
        label = input_vars[i] if i < len(input_vars) else f'Motor {i+1}'
        
        fig_motors.add_trace(go.Scatter(
            x=time_seq, y=u_dat[:Tsim, i], mode='lines',
            name=label, line=dict(width=1.2)
        ), row=row_idx, col=col_idx)
        
        # upper & lower PWM boundaries
        fig_motors.add_shape(type="line", x0=0, x1=time_seq[-1], y0=1000, y1=1000, line=dict(color="gray", width=0.5, dash="dot"), row=row_idx, col=col_idx)
        fig_motors.add_shape(type="line", x0=0, x1=time_seq[-1], y0=2000, y1=2000, line=dict(color="gray", width=0.5, dash="dot"), row=row_idx, col=col_idx)

    fig_motors.update_layout(title_text="Motor PWM Commands", hovermode="x unified", plot_bgcolor="white")
    fig_motors.write_html(save_dir / "plotly_motor_actuation.html")
    
    print("[hub_placement] Plotly interactive playback assets exported and saved successfully.")


def run_plots(
    df_test,
    actual_next: np.ndarray,
    preds_dict:  dict,
    state_vars:  list[str],
    input_vars:  list[str],
    cfg:         SimpleNamespace,
    gru_history: dict | None = None,
    best_estimator           = None,
    X_train_scaled           = None,
    y_train_scaled           = None,
    stds_dict:   dict | None = None,
) -> None:

    save_dir = Path(cfg.paths.plots)
    save_dir.mkdir(parents=True, exist_ok=True)
    time_col = cfg.time_col

    t = df_test[time_col].values

    best_name = next(iter(preds_dict))
    min_len = min(len(t), len(actual_next), len(preds_dict[best_name]))
    
    # slice arrays symmetrically down to the exact valid operational data length
    t = t[:min_len]
    actual_next_clean = np.asarray(actual_next[:min_len], dtype=float)
    
    # reconstruct predictions map cleanly without modifying the dictionary outer reference
    cleaned_preds = {}
    for name, arr in preds_dict.items():
        cleaned_preds[name] = np.asarray(arr[:min_len], dtype=float)

    best_arr = cleaned_preds[best_name]
    print(f"[plot] Synchronized telemetry visualization window to: {min_len} aligned steps.")

    # yaw-safe versions for plot_tracking
    best_yaw,   sv_yaw = _inject_yaw_col(best_arr,   state_vars)
    actual_yaw, _      = _inject_yaw_col(actual_next_clean, state_vars)


    def _try(label, fn, *args, **kwargs):
        try:
            fn(*args, **kwargs)
            print(f"[plot] {label} saved.")
        except Exception as e:
            print(f"[plot] Warning: {label} failed — {e}")

    X_state = df_test[state_vars].values[:min_len] 

    # reconstruct predictions to absolute scale: x_{k+1} = x_k + Δx
    preds_absolute = {}
    for mname, preds in preds_dict.items():
        # if model outputs are raw deltas, add X_state
        preds_sliced = preds[:min_len]

        if np.max(np.abs(preds[:, state_vars.index('bar_alt')])) < 5.0: # Delta detection proxy
            preds_absolute[mname] = X_state + preds_sliced
        else:
            preds_absolute[mname] = preds_sliced
            
    _try("model comparison",
         plot_model_comparison, t, actual_next, preds_dict, state_vars, save_dir)

    _try("RMSE comparison",
         plot_rmse_comparison, actual_next, preds_dict, state_vars, save_dir)

    _try("control inputs",
         plot_control_inputs, df_test, input_vars, time_col, save_dir)

    _try("attitude tracking",
         plot_attitude_tracking, t, actual_next, best_arr, state_vars, save_dir)

    _try("prediction errors",
         plot_prediction_errors, t, actual_next, best_arr, state_vars, save_dir)

    _try("tracking (yaw-safe)",
         plot_tracking, best_yaw, actual_yaw, sv_yaw, save_dir)
    
    _try("3D spatial flight paths",
         plot_3d_flight_paths, df_test, actual_next, preds_absolute, state_vars, cfg)

    if best_estimator is not None and X_train_scaled is not None:
        _try("learning curve",
             plot_learning_curve, best_estimator, X_train_scaled,
             y_train_scaled, save_dir)

    if gru_history is not None:
        _try("GRU loss", plot_gru_loss, gru_history, save_dir)

    if stds_dict is not None:
        _try("uncertainty bands",
             plot_uncertainty_bands, t, actual_next, preds_dict,
             state_vars, stds_dict, save_dir)
    else:
        print("[plot] Skipping uncertainty bands — no stds_dict provided.")

    print("[plot] All figures done.")