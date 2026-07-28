"""
src/control/mpc_train.py
fits a linear A, B state-space model from flight data via least squares:
    Δx ≈ A x + B u

bundles A, B, scalers, constraints, and initial conditions into
a single .pkl file consumed by MPC controller

called by: DATUM.py
"""

import numpy    as np
import pandas   as pd

from types                  import SimpleNamespace
from pathlib                import Path
from prepare                import prepare_mpc_data
from utils.io               import save_model
from .battery               import estimate_w_diag
from sklearn.linear_model   import Ridge


def estimate_linear_model(
    df: pd.DataFrame,
    sysid_state_vars: list[str],
    input_vars: list[str],
    cfg,
    Phi: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """
    estimates A, B via Ridge regression on:
        Δx ≈ A x + B u   →   Y ≈ Φ Θ

    parameters
    ----------
    phi : (N, n_x + n_u)  pre-built design matrix — caller owns alignment

    returns
    -------
    A : (n_x, n_x)  state transition matrix
    B : (n_x, n_u)  input matrix
    """
    next_cols = [f"{s}_next" for s in sysid_state_vars]

    if all(c in df.columns for c in next_cols):
        X_state = df[sysid_state_vars].values
        Y       = df[next_cols].values - X_state      # Δx = x_{k+1} - x_k
    else:
        # fallback: shift — produces N-1 rows; Phi trimmed to match
        X_state = df[sysid_state_vars].values[:-1]
        X_next  = df[sysid_state_vars].shift(-1).dropna().values
        Y       = X_next - X_state
        Phi     = Phi[:-1]                            # align rows

    if Y.shape[0] < 2:
        raise ValueError("Not enough samples to estimate linear model.")

    if Phi.shape[0] != Y.shape[0]:
        raise ValueError(
            f"Phi rows ({Phi.shape[0]}) != Y rows ({Y.shape[0]}). "
            "Check data alignment."
        )

    ridge_alpha = float(getattr(cfg.mpc, "ridge_alpha", 1.0))
    ridge       = Ridge(alpha=ridge_alpha, fit_intercept=False)
    ridge.fit(Phi, Y)

    Theta       = ridge.coef_.T    # shape: (len(sysid_state_vars) + len(input_vars), len(sysid_state_vars))
    n_x_sysid   = len(sysid_state_vars)

    A = Theta[:n_x_sysid, :].T     # (n_x_sysid, n_x_sysid)
    B = Theta[n_x_sysid:, :].T     # (n_x_sysid, n_u)

    return A.astype(float), B.astype(float)


def build_mpc_bundle(
    df: pd.DataFrame,
    state_vars: list[str],
    input_vars: list[str],
    cfg,
    residual_model=None,
) -> dict:
    """
    builds the full MPC bundle dict
    control limits come from configs/cfg.mpc.yaml
    """
    df, _, _, _ = prepare_mpc_data(df, cfg)
    
    # 1. isolate and combine tracking states and inputs
    clean_sysid_vars = state_vars + input_vars

    # 2. extract raw matrix data
    raw_phi_data = df[clean_sysid_vars].values

    # 3. Z-Score scaling to crush Cond(Phi) down from 28,000+
    phi_mean   = np.mean(raw_phi_data, axis=0)
    phi_std    = np.std(raw_phi_data, axis=0) + 1e-6
    Phi_scaled = (raw_phi_data - phi_mean) / phi_std
    
    print("\n[SysID Diagnostic]")
    print(f"  Condition Number (Raw)   : {np.linalg.cond(raw_phi_data):.2f}")
    print(f"  Condition Number (Scaled): {np.linalg.cond(Phi_scaled):.2f}")

    # 4. fit Ridge on SCALED Phi so conditioning is actually improved.
    #    estimate_linear_model returns A_s, B_s in the scaled coordinate system.
    #    We then recover A, B in physical units via the chain-rule transform:
    #
    #      Δx ≈ A_s·x_s + B_s·u_s       (scaled space)
    #      x_s = (x - μ_x)/σ_x,  u_s = (u - μ_u)/σ_u
    #
    #    Substituting back:
    #      Δx = A_s·diag(1/σ_x)·x + B_s·diag(1/σ_u)·u  + const
    #    so  A_phys = A_s · diag(1/σ_x),   B_phys = B_s · diag(1/σ_u)
    #    (the constant absorbed into the affine part, ignored in LTI model)
    n_x      = len(state_vars)
    n_u      = len(input_vars)
    sigma_x  = phi_std[:n_x]
    sigma_u  = phi_std[n_x:]
 
    A_s, B_s = estimate_linear_model(df, state_vars, input_vars, cfg, Phi_scaled)
 
    # recover physical-unit matrices
    A        = A_s * (1.0 / sigma_x)[np.newaxis, :]   # (n_x, n_x)
    B        = B_s * (1.0 / sigma_u)[np.newaxis, :]   # (n_x, n_u)

    # 5. calculate health diagnostics on the scaled system matrix
    I_A      = np.eye(A.shape[0]) + A
    eigvals  = np.linalg.eigvals(I_A)

    print("\n[SysID]")
    print(f"  Max |eig(I+A)| : {np.max(np.abs(eigvals)):.6f}")
    print(f"  Cond(Phi)      : {np.linalg.cond(Phi_scaled):.2f}")

    # 6. estimate energy weights for MPC
    W_diag = estimate_w_diag(df, input_vars)

    # 7. generate reference trajectory 
    ref_cols = [f"{s}_next" for s in state_vars]
    if all(c in df.columns for c in ref_cols):
        ref_traj = df[ref_cols].values
    else:
        ref_traj = df[state_vars].shift(-1).ffill().values

    bundle = {
        "A":          A,      
        "B":          B,      
        "x0":         df[state_vars].iloc[0].values.astype(float),
        "ref_traj":   ref_traj.astype(float),
        "u_min":      np.array(cfg.mpc.u_min, dtype=float),
        "u_max":      np.array(cfg.mpc.u_max, dtype=float),
        "dT":         float(df["dT"].mean()),
        "state_vars": state_vars,
        "input_vars": input_vars,
        "W_diag":     W_diag,
        "phi_mean":   phi_mean,
        "phi_std":    phi_std,
        "residual_model_path": str(Path(cfg.paths.models) / "residual_model.pkl"),
    }

    if residual_model is not None:
        bundle["residual_model"] = residual_model

    print(f"[mpc_train] A: {A.shape}  B: {B.shape}")
    print(f"[mpc_train] u_min: {bundle['u_min']}  u_max: {bundle['u_max']}")
    print(f"[mpc_train] W_diag: {bundle['W_diag']}")
    return bundle


def run_mpc_train(
    df: pd.DataFrame,
    state_vars: list[str],
    input_vars: list[str],
    cfg: SimpleNamespace,
) -> dict:
    
    """called by DATUM.py."""
    bundle = build_mpc_bundle(df, state_vars, input_vars, cfg)
    save_model(bundle, cfg.paths.mpc_bundle)
    return bundle