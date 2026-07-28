"""
utils/plots.py

every function takes data + a save_dir, saves both PDF and PNG, then shows it

used by: src/plot.py
"""

import numpy             as np
import pandas            as pd
import matplotlib.pyplot as plt

from pathlib                 import Path
from sklearn.metrics         import mean_squared_error
from sklearn.model_selection import TimeSeriesSplit, learning_curve


# colors
CONTROLLER_COLORS = {
    'DATUM (full)': 'black',
    'MLP+Residual': 'black',
}

def _color(name):
    return CONTROLLER_COLORS.get(name, 'steelblue')


# save helper
def _save(fig, save_dir: Path, stem: str, dpi: int = 300) -> None:
    for sub, ext in [("model_pdf", "pdf"), ("model_png", "png")]:
        d = save_dir / sub
        d.mkdir(parents=True, exist_ok=True)
        fig.savefig(d / f"{stem}.{ext}", dpi=dpi, bbox_inches="tight")
    plt.close(fig)


def _idx(state_vars, name):
    try:
        return state_vars.index(name)
    except ValueError:
        return None


def _yaw_from_sincos(arr, state_vars):
    si = _idx(state_vars, "yaw_sin")
    ci = _idx(state_vars, "yaw_cos")
    if si is None or ci is None:
        return None
    return np.degrees(np.arctan2(arr[:, si], arr[:, ci]))


# GPS projection
def project_lat_long_to_meters(df: pd.DataFrame):
    lat0 = np.radians(df['lat'].iloc[0])
    lon0 = np.radians(df['long'].iloc[0])
    lat  = np.radians(df['lat'].values)
    lon  = np.radians(df['long'].values)
    R    = 6_378_137.0
    pos_north = (lat - lat0) * R
    pos_east  = (lon - lon0) * R * np.cos(lat0)
    return pos_east, pos_north



# ------------------------------------------------------------------------------
# ── tracking comparison ───────────────────────────────────────────────────────
# ------------------------------------------------------------------------------

def plot_tracking(x_hist: np.ndarray,
                  ref_traj: np.ndarray,
                  state_vars: list,
                  save_dir=None,
                  name: str = "model",
                  results: dict | None = None):
    """
    overlay model states against the TRUE reference trajectory.

    x_hist   : (T, n_x)  — model or controller output states
    ref_traj : (T, n_x)  — reference trajectory from mpc_bundle (or actual next)
    state_vars: list of state names in column order

    """
    n    = min(len(x_hist), len(ref_traj))
    t    = np.arange(n)
    n_st = len(state_vars)

    # ── choose which panels to show ──
    priority = ['bar_alt', 'bar_cr', 'x_speed', 'y_speed', 'z_speed',
                'att_act_pitch', 'att_act_roll']
    show = [s for s in priority if _idx(state_vars, s) is not None]
    if not show:
        show = state_vars[:6]

    n_show = len(show)
    fig, axes = plt.subplots(n_show, 1, figsize=(12, n_show * 2.2), sharex=True)
    if n_show == 1:
        axes = [axes]

    for ax, sname in zip(axes, show):
        i = _idx(state_vars, sname)
        ax.plot(t, ref_traj[:n, i], 'r--', lw=1.5, alpha=0.8, label='Reference')
        ax.plot(t, x_hist[:n,  i], color=_color(name), lw=1.2, alpha=0.85, label=name)
        ax.set_ylabel(sname, fontsize=9)
        ax.grid(True, alpha=0.35)
        ax.legend(fontsize=8, loc='upper right')

    axes[-1].set_xlabel('Time step')
    plt.suptitle(f'Trajectory Tracking — {name}', fontsize=12)
    plt.tight_layout()

    if save_dir:
        Path(save_dir).mkdir(parents=True, exist_ok=True)
        fig.savefig(Path(save_dir) / f'tracking_{name.replace(" ", "_")}.png',
                    dpi=300, bbox_inches='tight')
    plt.close(fig)



# ------------------------------------------------------------------------------
# ── transition-period comparison ──────────────────────────────────────────────
# ------------------------------------------------------------------------------

def plot_transition_comparison(results: dict,
                                ref_traj: np.ndarray,
                                state_vars: list,
                                df_test: pd.DataFrame,
                                dT: float,
                                save_dir: Path):
    """
    zooms into the VTOL hover→cruise and cruise→hover transition windows and
    overlays all controllers.  transition epochs are detected from the
    'flight_phase' column if present; otherwise uses a climb-rate threshold.

    shows: altitude, climb rate, pitch, roll during each transition.
    """
    save_dir = Path(save_dir)
    n_pts    = min(len(ref_traj), min(len(r['x_hist']) for r in results.values()))
    time_s   = np.arange(n_pts) * dT

    # ── detect transition epochs ──────────────────────────────────────────────
    if 'flight_phase' in df_test.columns:
        phases     = df_test['flight_phase'].values[:n_pts]
        phase_enc  = {'ground': 0, 'takeoff': 1, 'cruise': 2,
                      'fixed_wing': 3, 'landing': 4}
        phase_num  = np.array([phase_enc.get(str(p).lower(), -1) for p in phases])
        # transition = step change in phase
        trans_mask = np.diff(phase_num, prepend=phase_num[0]) != 0
        trans_idx  = np.where(trans_mask)[0]
    else:
        # fallback: large |climb rate| changes
        cr_idx = _idx(state_vars, 'bar_cr')
        if cr_idx is not None:
            cr = ref_traj[:n_pts, cr_idx]
            trans_mask = np.abs(np.diff(cr, prepend=cr[0])) > 1.0
            trans_idx  = np.where(trans_mask)[0]
        else:
            print("[plot] No flight_phase or bar_cr for transition detection — skipping.")
            return

    if len(trans_idx) == 0:
        print("[plot] No transitions detected — skipping transition plot.")
        return

    # build ±15 s windows around each transition
    window_s = 20.0
    half     = int(window_s / dT / 2)
    windows  = []
    prev_end = -1
    for ti in trans_idx:
        lo = max(0, ti - half)
        hi = min(n_pts - 1, ti + half)
        if lo > prev_end:
            windows.append((lo, hi, ti))
            prev_end = hi

    # limit to first 3 transitions to keep the figure readable
    windows = windows[:3]

    panel_states = ['bar_alt', 'bar_cr', 'att_act_pitch', 'att_act_roll']
    show_states  = [s for s in panel_states if _idx(state_vars, s) is not None]
    n_panels     = len(show_states)

    for w_idx, (lo, hi, ti) in enumerate(windows):
        fig, axes = plt.subplots(n_panels, 1,
                                 figsize=(11, n_panels * 2.5), sharex=True)
        if n_panels == 1:
            axes = [axes]

        t_win = time_s[lo:hi]

        # shade the transition instant
        t_trans = time_s[ti]

        for ax, sname in zip(axes, show_states):
            si = _idx(state_vars, sname)
            ax.axvspan(t_trans - dT, t_trans + dT,
                       color='gold', alpha=0.4, label='Transition')
            ax.plot(t_win, ref_traj[lo:hi, si],
                    'r--', lw=1.8, alpha=0.8, label='Reference')

            for ctrl_name, res in results.items():
                xh = res['x_hist']
                ax.plot(t_win, xh[lo:hi, si],
                        color=_color(ctrl_name), lw=1.2,
                        alpha=0.85, label=ctrl_name)

            ax.set_ylabel(sname, fontsize=9)
            ax.grid(True, alpha=0.35)

        axes[0].legend(fontsize=7, loc='upper right', ncol=3)
        axes[-1].set_xlabel('Time (s)')

        # annotate flight phase if available
        if 'flight_phase' in df_test.columns:
            phase_at_trans = str(df_test['flight_phase'].iloc[ti]).capitalize()
            plt.suptitle(f'VTOL Transition Window {w_idx+1} — {phase_at_trans}',
                         fontsize=12)
        else:
            plt.suptitle(f'VTOL Transition Window {w_idx+1}', fontsize=12)

        plt.tight_layout()
        _save(fig, save_dir, f'transition_window_{w_idx+1}')
        plt.savefig(save_dir / '15I_Transition_Phase_Comparison.png', dpi=300, bbox_inches='tight')


    print(f"[plot] Transition comparison saved ({len(windows)} windows).")



# ------------------------------------------------------------------------------
# ── 3D flight path ────────────────────────────────────────────────────────────
# ------------------------------------------------------------------------------

def plot_3d_flight_paths(df_test, actual_next, preds_dict: dict,
                          state_vars: list, cfg):
    """
    3D trajectory plot
    """
    save_dir = Path(cfg.paths.plots)
    n   = len(actual_next)
    dT  = float(df_test['dT'].mean()) if 'dT' in df_test.columns else 0.05

    if 'lat' not in df_test.columns or 'long' not in df_test.columns:
        print("[plot_3d] No lat/long columns — skipping 3D flight plot.")
        return

    pos_east, pos_north = project_lat_long_to_meters(df_test)
    pos_east  = pos_east[:n]
    pos_north = pos_north[:n]

    alt_idx   = _idx(state_vars, 'bar_alt')
    actual_up = actual_next[:, alt_idx] if alt_idx is not None else np.zeros(n)

    time_col    = getattr(cfg, 'time_col', 'time_ms')
    time_points = df_test[time_col].values[:n]
    if "ms" in time_col.lower():
        time_points = time_points / 1000.0

    # ── chart A: 60-second GPS + altitude clip ────────────────────────────
    t0   = time_points[0]
    mask = (time_points >= t0) & (time_points <= t0 + 60.0)

    fig1 = plt.figure(figsize=(10, 7))
    ax1  = fig1.add_subplot(111, projection='3d')
    ax1.plot(pos_east[mask], pos_north[mask], actual_up[mask],
             color='red', lw=2.5, alpha=0.9, label='True Path (GPS + baro)')

    # overlay model altitude along the true GPS track
    colors = ['green', 'black', 'purple', 'orange', 'cyan']
    for ci, (mname, preds) in enumerate(preds_dict.items()):
        pred_up = preds[:, alt_idx] if alt_idx is not None else np.zeros(n)
        ax1.plot(pos_east[mask], pos_north[mask], pred_up[mask],
                 color=colors[ci % len(colors)], lw=1.5, ls='--',
                 alpha=0.75, label=f'{mname} altitude')

    ax1.set_title('3D Flight Path — 60 s Window', fontsize=11, fontweight='bold')
    ax1.set_xlabel('East (m)'); ax1.set_ylabel('North (m)'); ax1.set_zlabel('Alt (m)')
    ax1.legend(fontsize=9)
    ax1.grid(True, ls='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig(save_dir / '15A_3d_flight_path_clip.png', dpi=300, bbox_inches='tight')
    plt.close()

    # ── chart B: full flight ──────────────────────────────────────────────
    fig2 = plt.figure(figsize=(11, 8))
    ax2  = fig2.add_subplot(111, projection='3d')
    ax2.plot(pos_east, pos_north, actual_up,
             color='red', lw=2.5, alpha=0.85, label='True Path (GPS + baro)')

    for ci, (mname, preds) in enumerate(preds_dict.items()):
        pred_up = preds[:, alt_idx] if alt_idx is not None else np.zeros(n)
        ax2.plot(pos_east, pos_north, pred_up,
                 color=colors[ci % len(colors)], lw=1.2, ls='--',
                 alpha=0.7, label=f'{mname} altitude')

    ax2.set_title('3D Flight Path — Full Trajectory', fontsize=11, fontweight='bold')
    ax2.set_xlabel('East (m)'); ax2.set_ylabel('North (m)'); ax2.set_zlabel('Alt (m)')
    ax2.legend(fontsize=8)
    ax2.grid(True, ls='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig(save_dir / '15B_3d_all_flight_paths.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("[plot] 3D spatial trajectory figures generated and exported successfully.")



# ------------------------------------------------------------------------------
# ── model comparison ──────────────────────────────────────────────────────────
# ------------------------------------------------------------------------------

def plot_model_comparison(time_points, actual_next, preds_dict: dict,
                           state_vars: list, save_dir: Path):
    """
    per-state overlay: actual vs each model
    expects preds_dict values to already be in absolute state units
    """
    unit_map = {
        'bar_alt': 'm', 'bar_cr': 'm/s',
        'x_speed': 'm/s', 'y_speed': 'm/s', 'z_speed': 'm/s',
        'att_act_pitch': 'deg', 'att_act_roll': 'deg',
        'yaw_sin': '—', 'yaw_cos': '—',
    }

    n_st  = len(state_vars)
    ncols = 2
    nrows = (n_st + 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(14, nrows * 3), sharex=True)
    axes = axes.flatten()

    for i, sname in enumerate(state_vars):
        ax   = axes[i]
        unit = unit_map.get(sname, '—')
        ax.plot(time_points, actual_next[:, i],
                color='red', lw=2, alpha=0.9, label='Actual')
        for mname, preds in preds_dict.items():
            ax.plot(time_points, preds[:, i],
                    color=_color(mname), lw=1.1, alpha=0.6, label=mname)
        ax.set_title(f'{sname}  [{unit}]', fontsize=10, fontweight='bold')
        ax.set_ylabel(f'[{unit}]', fontsize=9)
        ax.grid(True, ls='--', alpha=0.5)

    for j in range(n_st, len(axes)):
        axes[j].set_visible(False)
    for j in range(max(0, len(axes) - ncols), len(axes)):
        if axes[j].get_visible():
            axes[j].set_xlabel('Time (s)', fontsize=10)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='upper right', fontsize=9,
               bbox_to_anchor=(1.0, 1.0))
    plt.suptitle('State Predictions vs Actual', fontsize=12, y=1.01)
    plt.tight_layout()
    _save(fig, save_dir, '15A_model_comparison_all_states')



# ------------------------------------------------------------------------------
# ── rmse bar chart ────────────────────────────────────────────────────────────
# ------------------------------------------------------------------------------

def plot_rmse_comparison(actual_next, preds_dict: dict,
                          state_vars: list, save_dir: Path):
    model_names = list(preds_dict)
    x     = np.arange(len(state_vars))
    width = 0.8 / max(len(model_names), 1)

    fig, ax = plt.subplots(figsize=(14, 5))
    for i, mname in enumerate(model_names):
        rmses = [float(np.sqrt(mean_squared_error(
                     actual_next[:, j], preds_dict[mname][:, j])))
                 for j in range(len(state_vars))]
        ax.bar(x + i * width, rmses, width,
               label=mname, color=_color(mname), alpha=0.8)

    ax.set_xticks(x + width * (len(model_names) - 1) / 2)
    ax.set_xticklabels(state_vars, rotation=30, ha='right', fontsize=9)
    ax.set_ylabel('RMSE')
    ax.set_title('Per-State RMSE by Model')
    ax.legend(fontsize=9); ax.grid(True, axis='y')
    plt.tight_layout()
    _save(fig, save_dir, '15B_rmse_comparison')



# ------------------------------------------------------------------------------
# ── control inputs ────────────────────────────────────────────────────────────
# ------------------------------------------------------------------------------

def plot_control_inputs(df_test, input_vars: list,
                         time_col: str, save_dir: Path):
    n     = len(input_vars)
    ncols = 2
    nrows = (n + 1) // ncols
    colors = ['blue', 'green', 'red', 'purple', 'orange', 'brown']

    fig, axes = plt.subplots(nrows, ncols, figsize=(12, nrows * 3), sharex=True)
    axes = axes.flatten()

    for i, var in enumerate(input_vars):
        if var not in df_test.columns:
            continue
        label = f'Motor {i+1}' if 'RCOU' in var else var
        axes[i].plot(df_test[time_col].values, df_test[var].values,
                     color=colors[i % len(colors)], label=label)
        axes[i].set_title(label)
        axes[i].set_ylabel('PWM (μs)')
        axes[i].axhline(1500, color='gray', ls='--', lw=0.8, label='hover ~1500')
        axes[i].grid(True)

    for j in range(n, len(axes)):
        axes[j].set_visible(False)
    for j in range(max(0, len(axes) - ncols), len(axes)):
        if axes[j].get_visible():
            axes[j].set_xlabel('Time (s)')

    plt.suptitle('Motor PWM Commands over Time', fontsize=12)
    plt.tight_layout()
    _save(fig, save_dir, '15C_motor_inputs')



# ------------------------------------------------------------------------------
# ── attitude tracking ─────────────────────────────────────────────────────────
# ------------------------------------------------------------------------------

def plot_attitude_tracking(time_points, actual_next, best_preds,
                            state_vars: list, save_dir: Path):
    candidates = [
        ('bar_alt',       'Altitude (m)'),
        ('x_speed',       'X Speed (m/s)'),
        ('y_speed',       'Y Speed (m/s)'),
        ('z_speed',       'Z Speed (m/s)'),
        ('att_act_roll',  'Roll (deg)'),
        ('att_act_pitch', 'Pitch (deg)'),
    ]
    available = [(nm, lb) for nm, lb in candidates
                 if _idx(state_vars, nm) is not None]
    if not available:
        available = [(state_vars[i], state_vars[i])
                     for i in range(min(4, len(state_vars)))]

    n_p  = len(available)
    fig, axes = plt.subplots(n_p, 1, figsize=(12, n_p * 2.5), sharex=True)
    if n_p == 1:
        axes = [axes]

    for ax, (sname, ylabel) in zip(axes, available):
        i = _idx(state_vars, sname)
        ax.plot(time_points, actual_next[:, i],
                color='red',  lw=2, alpha=0.9, label='Actual')
        ax.plot(time_points, best_preds[:, i],
                color='steelblue', lw=1.5, alpha=0.7, label='Best Model')
        ax.set_title(sname, fontsize=11)
        ax.set_ylabel(ylabel, fontsize=10)
        ax.legend(fontsize=9); ax.grid(True)

    axes[-1].set_xlabel('Time (s)', fontsize=11)
    plt.suptitle('Attitude/State Tracking — Best Model', fontsize=12)
    plt.tight_layout()
    _save(fig, save_dir, '15D_attitude_tracking')



# ------------------------------------------------------------------------------
# ── prediciton errors ─────────────────────────────────────────────────────────
# ------------------------------------------------------------------------------

def plot_prediction_errors(time_points, actual_next, best_preds,
                            state_vars: list, save_dir: Path):
    n_st  = len(state_vars)
    ncols = 2
    nrows = (n_st + 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(14, nrows * 2.5), sharex=True)
    axes = axes.flatten()

    for i, sname in enumerate(state_vars):
        errors = best_preds[:, i] - actual_next[:, i]
        if 'yaw' in sname.lower():
            errors = (errors + 180) % 360 - 180
        rmse = float(np.sqrt(np.mean(errors ** 2)))
        axes[i].plot(time_points, errors, alpha=0.5, lw=0.8, color=_color('Linear'))
        axes[i].axhline(0,     color='gray',  lw=0.8)
        axes[i].axhline( rmse, color='black', lw=1, ls='--', label=f'±RMSE {rmse:.3f}')
        axes[i].axhline(-rmse, color='black', lw=1, ls='--')
        axes[i].set_title(sname, fontsize=9)
        axes[i].legend(fontsize=7); axes[i].grid(True)
        if i % ncols == 0:
            axes[i].set_ylabel('Error')

    for j in range(n_st, len(axes)):
        axes[j].set_visible(False)
    for j in range(max(0, len(axes) - ncols), len(axes)):
        if axes[j].get_visible():
            axes[j].set_xlabel('Time (s)')

    plt.suptitle('Prediction Errors over Time — Best Model', fontsize=12)
    plt.tight_layout()
    _save(fig, save_dir, '15E_prediction_errors')


# ------------------------------------------------------------------------------
# ── learning curve ────────────────────────────────────────────────────────────
# ------------------------------------------------------------------------------

def plot_learning_curve(estimator, X_train, y_train,
                         save_dir: Path, n_splits: int = 5):
    cv = TimeSeriesSplit(n_splits=n_splits)
    sizes, tr_sc, val_sc = learning_curve(
        estimator, X_train, y_train, cv=cv,
        scoring='neg_root_mean_squared_error',
        train_sizes=np.linspace(0.1, 1.0, 8), n_jobs=-1,
    )
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(sizes, -tr_sc.mean(axis=1),  'o-', label='Train RMSE')
    ax.plot(sizes, -val_sc.mean(axis=1), 'o-', label='Val RMSE')
    ax.fill_between(sizes,
                    -val_sc.mean(axis=1) - val_sc.std(axis=1),
                    -val_sc.mean(axis=1) + val_sc.std(axis=1),
                    alpha=0.15)
    ax.set_xlabel('Training set size'); ax.set_ylabel('RMSE')
    ax.set_title('Learning Curve'); ax.legend(); ax.grid(True)
    plt.tight_layout()
    _save(fig, save_dir, '15F_learning_curve')


# ------------------------------------------------------------------------------
# ── GRU loss ──────────────────────────────────────────────────────────────────
# ------------------------------------------------------------------------------

def plot_gru_loss(history: dict, save_dir: Path):
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(history['loss'],     label='Train')
    ax.plot(history['val_loss'], label='Validation')
    ax.set_yscale('log')
    ax.set_title('GRU Learning Curve')
    ax.set_xlabel('Epochs'); ax.set_ylabel('MSE Loss (log)')
    ax.legend(); ax.grid(True)
    plt.tight_layout()
    _save(fig, save_dir, '15G_gru_learning_curve')


# ------------------------------------------------------------------------------
# ── uncertainty bands ─────────────────────────────────────────────────────────
# ------------------------------------------------------------------------------

def plot_uncertainty_bands(time_points, actual_next, preds_dict: dict,
                            state_vars: list, stds_dict: dict | None,
                            save_dir: Path, n_panels: int = 4):
    preferred    = ['bar_alt', 'att_act_roll', 'att_act_pitch', 'bar_cr']
    panel_states = [s for s in preferred if _idx(state_vars, s) is not None]
    if len(panel_states) < n_panels:
        extras = [s for s in state_vars if s not in panel_states]
        panel_states += extras[:n_panels - len(panel_states)]
    panel_states = panel_states[:n_panels]

    ncols = 2
    nrows = (len(panel_states) + 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(13, nrows * 3.5), sharex=True)
    axes = axes.flatten()

    for panel_i, sname in enumerate(panel_states):
        ax  = axes[panel_i]
        idx = _idx(state_vars, sname)
        ax.plot(time_points, actual_next[:, idx],
                color='red', lw=2.5, alpha=0.7, label='Actual')
        for mname, preds in preds_dict.items():
            c = _color(mname)
            ax.plot(time_points, preds[:, idx],
                    color=c, alpha=0.7, lw=1.2, label=mname)
            if stds_dict and mname in stds_dict:
                std = stds_dict[mname][:, idx]
                ax.fill_between(time_points,
                                preds[:, idx] - std,
                                preds[:, idx] + std,
                                color=c, alpha=0.2, label=f'{mname} ±1σ')
        ax.set_title(sname, fontsize=10)
        ax.set_ylabel('Value', fontsize=9)
        ax.grid(True); ax.legend(fontsize=7)

    for j in range(len(panel_states), len(axes)):
        axes[j].set_visible(False)
    for j in range(max(0, len(axes) - ncols), len(axes)):
        if axes[j].get_visible():
            axes[j].set_xlabel('Time (s)')

    plt.suptitle('State Predictions with Uncertainty Bands', fontsize=12)
    plt.tight_layout()
    _save(fig, save_dir, '15H_uncertainty_bands')