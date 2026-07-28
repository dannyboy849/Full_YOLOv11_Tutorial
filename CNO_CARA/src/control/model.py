import numpy as np
import casadi as ca
import do_mpc



# --------------------------------------------------
# ── SECTION 5 — do-mpc model + controllers ────────
# --------------------------------------------------


def _make_do_mpc_model(A: np.ndarray, B: np.ndarray,
                       x_mean, x_std, u_mean, u_std,
                       casadi_residual=None,
                       feat_scaler_mean: np.ndarray | None = None,
                       feat_scaler_std:  np.ndarray | None = None,
                       use_wind: bool = True) -> do_mpc.model.Model:
    """
    build the do-mpc discrete-time model.

    scaling pipeline:
      1. x_scaled = (x - x_mean) / x_std          ← phi-normalised
      2. u_scaled = (u - u_mean) / u_std           ← phi-normalised
      3. nominal: rhs_scaled = (I+A)·x_s + B·u_s  ← scaled prediction
      4. rhs      = rhs_scaled * x_std + x_mean    ← back to physical
      5. residual (if present):
            feat = vertcat(x_scaled, u_scaled)      ← phi-normalised
            feat_sx = (feat - feat_mean) / feat_std ← scaler_X space
            g = casadi_residual(feat_sx)            ← MLP expects scaler_X
         rhs += g  (MLP output is raw-delta; scaler_y inversion done offline)
    """
    n_x, n_u    = A.shape[0], B.shape[1]

    model       = do_mpc.model.Model('discrete')

    x           = model.set_variable('_x',   'x',  shape=(n_x, 1))
    u           = model.set_variable('_u',   'u',  shape=(n_u, 1))
    xr          = model.set_variable('_tvp', 'xr', shape=(n_x, 1))
    pw          = model.set_variable('_tvp', 'power_ref', shape=(1, 1))

    tightened_bounds = model.set_variable(var_type='_p', var_name='tightened_bounds', shape=(n_x, 1))
    mu_state         = model.set_variable(var_type='_p', var_name='mu_state',         shape=(1,   1))

    if use_wind:
        wind = model.set_variable(var_type='_tvp', var_name='wind', shape=(n_x, 1))

    I_A     = np.eye(n_x) + A

    eigvals = np.linalg.eigvals(I_A)
    rho     = np.max(np.abs(eigvals))
    print(f"[hub_placement] max eig(I+A) = {rho:.4f}")

    if rho > 1.05:
        print(f"[hub_placement] Spectral-radius correction: rho={rho:.3f} → scaling A down.")
        A   = A / (rho * 1.1)
        I_A = np.eye(n_x) + A

    # phi-normalise x and u 
    ca_x_mean   = ca.DM(x_mean.reshape(-1, 1))
    ca_x_std    = ca.DM(x_std.reshape(-1, 1))
    ca_u_mean   = ca.DM(u_mean.reshape(-1, 1))
    ca_u_std    = ca.DM(u_std.reshape(-1, 1))

    x_scaled    = (x - ca_x_mean) / ca_x_std
    u_scaled    = (u - ca_u_mean) / ca_u_std

    #  nominal forward step 
    rhs_scaled  = ca.DM(I_A) @ x_scaled + ca.DM(B) @ u_scaled
    rhs         = rhs_scaled * ca_x_std + ca_x_mean

    #  neural residual in scaler_X space 
    if casadi_residual is not None:
        if feat_scaler_mean is not None and feat_scaler_std is not None:
            n_feat      = len(feat_scaler_mean)
            n_xu        = n_x + n_u
            # phi-normalised [x ; u] already computed above
            feat_phi_xu = ca.vertcat(x_scaled, u_scaled)     # (n_xu, 1)

            if n_feat > n_xu:
                # pad remaining columns with their scaler_X-normalised mean = 0
                pad      = ca.DM.zeros(n_feat - n_xu, 1)
                feat_phi = ca.vertcat(feat_phi_xu, pad)       # (n_feat, 1)

            else:
                feat_phi = feat_phi_xu[:n_feat]               # trim if somehow shorter

            # scaler_X: (feat_phi - sx_mean) / sx_std
            ca_fm   = ca.DM(feat_scaler_mean.reshape(-1, 1))
            ca_fs   = ca.DM(feat_scaler_std.reshape(-1, 1))
            feat_sx = (feat_phi - ca_fm) / ca_fs              # scaler_X space
            rhs     = rhs + casadi_residual(feat_sx)

        else:
            print("[hub_placement] WARNING: casadi_residual provided but feat_scaler_mean/std "
                  "are None — residual skipped. Pass scaler_X.mean_ / scaler_X.scale_.")

    if use_wind:
        rhs = rhs + wind

    model.set_rhs('x', rhs)
    model.setup()
    return model