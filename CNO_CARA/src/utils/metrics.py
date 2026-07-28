"""
utils/metrics.py

function metric helpers. has no side effects, no I/O

used by: src/evaluate.py
"""

from pathlib import Path
import numpy as np
from sklearn.metrics import mean_squared_error, r2_score


# --------------------------------------------------
# ── helpers ───────────────────────────────────────
# --------------------------------------------------

def wrap_yaw_errors(errors: np.ndarray) -> np.ndarray:
    """wrap yaw errors into (−180, +180]"""
    return (errors + 180) % 360 - 180



# --------------------------------------------------
# ── thresholds ────────────────────────────────────
# --------------------------------------------------

STATE_THRESHOLDS = {
    "bar_alt": 1.0,
    "bar_cr": 0.5,
    "x_speed": 1.0,
    "y_speed": 1.0,
    "z_speed": 5.0,
    "att_act_roll": 5.0,
    "att_act_pitch": 5.0,
    "yaw_sin": 0.2,
    "yaw_cos": 0.2,
}

   

# --------------------------------------------------
# ── per-state regression metrics ──────────────────
# --------------------------------------------------

def per_state_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    state_name: str,
    thresholds: dict | None = None,
) -> dict:
    """
    compute rmse, R², and violation percentage for one state
    """

    errors = y_pred - y_true

    if "yaw" in state_name.lower():
        errors = wrap_yaw_errors(errors)

    # fixed, interpretable threshold
    if thresholds is not None:
        threshold = thresholds.get(state_name, 2.0 * np.std(y_true))
    else:
        threshold = 2.0 * np.std(y_true)

    # safety evaluation
    is_safe = np.abs(errors) <= threshold
    violation_pct = 100.0 * np.mean(~is_safe)

    return {
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "R2": float(r2_score(y_true, y_pred)),
        "Violation_%": float(violation_pct),
    }



# --------------------------------------------------
# ── overall metrics ───────────────────────────────
# --------------------------------------------------

def overall_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """
    multi-output overall rmse and R² (uniform average across outputs)
    """
    return {
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "R2": float(r2_score(y_true, y_pred)),
    }


def overall_r2_per_state(y_true: np.ndarray, y_pred: np.ndarray):
    """
    returns:
        mean R² across states
        list of per-state R² values
    """
    r2s = [r2_score(y_true[:, i], y_pred[:, i]) for i in range(y_true.shape[1])]
    return float(np.mean(r2s)), r2s