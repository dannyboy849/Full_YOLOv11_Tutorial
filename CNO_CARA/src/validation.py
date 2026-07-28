"""
src/validation.py
pre-flight check: setup validation, leak guard, data-quality.

called by: DATUM.py 
"""

import numpy    as np
import pandas   as pd

from types import SimpleNamespace


# --------------------------------------------------
# ── check columns ─────────────────────────────────
# --------------------------------------------------

def check_required_columns(
    df,
    cfg
):

    generated_cols = {
        "yaw_sin",
        "yaw_cos",
        "flight_phase",
        "power_w"
    }

    required = (
        cfg.input_vars +
        [
            c
            for c in cfg.output_vars
            if c not in generated_cols
        ] +
        [cfg.time_col]
    )

    missing = [
        c for c in required
        if c not in df.columns
    ]

    if missing:
        raise ValueError(
            f"[validation] Missing required columns: {missing}"
        )
    


# --------------------------------------------------
# ── leak guard ────────────────────────────────────
# --------------------------------------------------

def check_no_leakage(features: list[str]) -> None:
    leakers = [f for f in features if f.endswith("_next")]
    if leakers:
        raise ValueError(f"[validation] Data leakage detected — '_next' in features: {leakers}")
    print("[validation] Leakage: No leakage detected.")



# --------------------------------------------------
# ── normalised rmse per state ─────────────────────
# --------------------------------------------------

def normalized_rmse_report(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    state_vars: list[str],
    warn_threshold: float = 0.5,
) -> dict:
    
    """
    nrmse = rmse / std(y_true).
    values < 0.1  → warning (check for possible leak)
    values > warn_threshold → poor fit
    """

    report = {}
    print("\n[validation] Normalised rmse per state (rmse / σ):")
    for i, name in enumerate(state_vars):
        std  = np.std(y_true[:, i])
        rmse = float(np.sqrt(np.mean((y_true[:, i] - y_pred[:, i]) ** 2)))
        nrmse = rmse / (std if std > 0 else 1.0)
        flag  = " Dangerous" if nrmse > warn_threshold else (" Acceptable" if nrmse >= 0.15 else " Great")
        print(f"  {name:25s}: {nrmse:.4f}{flag}")
        report[name] = nrmse
    return report