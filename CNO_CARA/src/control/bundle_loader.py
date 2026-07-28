"""
src/control/bundle_loader.py

loads the MPC bundle (A, B, scalers, constraints, initial conditions)

called by: run_mpc_comparison.py

"""


import numpy    as np
import joblib
import casadi   as ca

from casadi                 import SX, vertcat, Function
from pathlib                import Path
from sklearn.multioutput    import MultiOutputRegressor
from sklearn.linear_model   import LinearRegression, Ridge, BayesianRidge
from sklearn.neural_network import MLPRegressor


# --------------------------------------------------
# ── checkpoint ────────────────────────────────────
# --------------------------------------------------

def check_bundle_exists(path):

    try:
        data = joblib.load(path)

        print(
            "Bundle found!",
            data.keys()
        )

        return True

    except FileNotFoundError:
        print(
            "Bundle file missing."
        )

        return False



#--------------------------------------------------
# ── load bundle ──────────────────────────────────
#--------------------------------------------------

def _load_bundle(path: str | Path) -> tuple:
    d           = joblib.load(path)

    A           = np.asarray(d['A'])
    B           = np.asarray(d['B'])
    x0          = np.asarray(d['x0']).flatten()
    ref_traj    = np.asarray(d['ref_traj'])
    u_min       = np.array(d['u_min'], dtype=float)
    u_max       = np.array(d['u_max'], dtype=float)
    dT          = float(d['dT'])
    sv          = d['state_vars']
    iv          = d['input_vars']
    W_diag      = d.get('W_diag', np.array([5.0] * len(iv))) 

    # length of clean sysid vars = n_x + n_u
    total_vars_len  = len(sv) + len(iv)
    phi_mean        = d.get('phi_mean', np.zeros(total_vars_len))
    phi_std         = d.get('phi_std',  np.ones(total_vars_len))


    residual_model_path = d.get("residual_model_path", None)
    residual_model      = None

    if residual_model_path:
        try:
            residual_model = joblib.load(residual_model_path)
        except Exception:
            pass

    return (
        A,
        B,
        x0,
        ref_traj,
        u_min,
        u_max,
        dT,
        sv,
        iv,
        W_diag,
        phi_mean,
        phi_std,
        residual_model
    )



# --------------------------------------------------
# ── CasADi MLP export ─────────────────────────────
# --------------------------------------------------

print("Script started...")

def mlp_to_casadi(obj, name="mlp_residual"):
    """
    convert a fitted sklearn model into a CasADi symbolic Function
    used to embed g_θ inside the MPC's CasADi optimization graph

    handles:
      MLPRegressor                 → direct weight export
      MultiOutputRegressor(MLP)    → per-output stacked export
      MultiOutputRegressor(Linear) → returns None (no residual needed)
      anything else                → returns None
    """
    if isinstance(obj, MLPRegressor):
        return _mlp_weights_to_casadi(obj, name)

    if isinstance(obj, MultiOutputRegressor):
        if not hasattr(obj, "estimators_"):
            return None

        inner = obj.estimators_[0]

        if isinstance(inner, MLPRegressor):
            return _multi_mlp_to_casadi(obj, name)

        if isinstance(inner, (LinearRegression, Ridge, BayesianRidge)):
            return None
    return None


def _mlp_weights_to_casadi(mlp: MLPRegressor, name: str) -> Function:
    n_in  = mlp.coefs_[0].shape[0]
    x_sym = SX.sym('x', n_in)
    out   = x_sym

    for i, (W, b) in enumerate(zip(mlp.coefs_, mlp.intercepts_)):
        out = SX(W).T @ out + SX(b).reshape((-1, 1))
        if i < len(mlp.coefs_) - 1:          # hidden layer activation
            if mlp.activation == 'relu':
                out = ca.fmax(SX(0), out)
            elif mlp.activation == 'tanh':
                out = ca.tanh(out)
            # 'identity' / 'logistic' 
    return Function(name, [x_sym], [out])


def _multi_mlp_to_casadi(mor: MultiOutputRegressor, name: str) -> Function:
    """stack per-output MLPs into one CasADi function."""
    n_in  = mor.estimators_[0].coefs_[0].shape[0]
    x_sym = SX.sym('x', n_in)
    outs  = [_mlp_weights_to_casadi(est, f"sub{name}{i}")(x_sym)
             for i, est in enumerate(mor.estimators_)]
    return Function(name, [x_sym], [vertcat(*outs)])