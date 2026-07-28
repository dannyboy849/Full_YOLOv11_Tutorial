"""
src/train.py
builds and trains the model specified in cfg.active.
includes all sklearn baselines, GRU, and Optuna tuning.

called by DATUM.py
returns: fitted model object
"""

import numpy        as np
import optuna
import tensorflow   as tf

from types                      import SimpleNamespace
from sklearn.metrics            import mean_squared_error
from sklearn.multioutput        import MultiOutputRegressor
from sklearn.linear_model       import LinearRegression
from sklearn.neural_network     import MLPRegressor
from sklearn.model_selection    import KFold
from sklearn.model_selection    import LeaveOneGroupOut  # specialized for flight logs


# --------------------------------------------------
# ── sklearn baselines ─────────────────────────────
# --------------------------------------------------

def build_linear() -> MultiOutputRegressor:
    return MultiOutputRegressor(LinearRegression())



# --------------------------------------------------
# ── optuna MLP tuning ─────────────────────────────
# --------------------------------------------------

def build_mlp_optuna(X_train, y_train, scaler_y, cfg, groups=None, seed: int = 42):

    optuna.logging.set_verbosity(optuna.logging.WARNING)

    study = optuna.create_study(
        direction=cfg.optuna.direction,
        sampler=optuna.samplers.TPESampler(seed=seed),
    )
    
    """previously diverged due to second layer n2 allowing 0 (topology error causes divergence). Optuna TPE w/ MLP architecture for best model. """

    def objective(trial):
        # 1. enforce strict, smooth geometric scaling for a fast control loop
        n1         = trial.suggest_int("n1", 32, 128, step = 32)  
        n2         = trial.suggest_int("n2", 16, 64,  step = 16)
        n3         = trial.suggest_int("n3", 8,  32,  step = 8)   
        hidden     = (n1, n2, n3)
   
        # 2. focus on regularization to prevent overfitting to wind gusts
        alpha      = trial.suggest_float("alpha", 1e-6, 1e-2, log=True)
        batch      = trial.suggest_categorical("batch_size", [32, 64, 128])
        activation = trial.suggest_categorical("activation", ["tanh", "relu"])

        clf = MLPRegressor(
            hidden_layer_sizes  = hidden,
            alpha               = alpha,
            batch_size          = batch,
            activation          = activation,
            learning_rate       = "adaptive",
            solver              = "adam",
            max_iter            = 300,
            random_state        = seed,
        )

        # 3. structural validation splits
        if groups is not None:
            cv          = LeaveOneGroupOut()
            cv_splits   = cv.split(X_train, y_train, groups=groups)
        else:
            cv          = KFold(n_splits=2, shuffle=False) # higher n_splits -> longer training 
            cv_splits   = cv.split(X_train)

        rmses = []
        for tr_idx, val_idx in cv_splits:
            clf.fit(X_train[tr_idx], y_train[tr_idx])
            
            p_val = clf.predict(X_train[val_idx])
            t_val = y_train[val_idx]

            # reshape logic to guarantee inverse_transform never crashes
            if p_val.ndim == 1: p_val = p_val.reshape(-1, 1)
            if t_val.ndim == 1: t_val = t_val.reshape(-1, 1)
                
            pred = scaler_y.inverse_transform(p_val)
            true = scaler_y.inverse_transform(t_val)
            rmses.append(np.sqrt(mean_squared_error(true, pred)))
            
        return float(np.mean(rmses))


    study.optimize(objective, n_trials=cfg.optuna.n_trials, n_jobs=-1, show_progress_bar=True)
    p = study.best_params
    print(f"[train] Optuna best params: {p}")

    # reconstruct optimized structure
    best_hidden = (p["n1"], p["n2"], p["n3"])
    best_model = MLPRegressor(
        hidden_layer_sizes  = best_hidden,
        alpha               = p["alpha"],
        batch_size          = p["batch_size"],
        activation          = p["activation"],
        learning_rate       = "adaptive",
        solver              = "adam",
        max_iter            = 500,       
        early_stopping      = True, 
        n_iter_no_change    = 20,
        validation_fraction = 0.1,
        random_state        = seed,
    )
    best_model.fit(X_train, y_train)
    return best_model


# --------------------------------------------------
# ── training ──────────────────────────────────────
# --------------------------------------------------

def build_and_train(
    X_train: np.ndarray,
    y_train: np.ndarray,
    cfg: SimpleNamespace,
    scaler_y=None,
):
    """
    trains the correct model builder based on cfg.active
    for GRU, use X_train_seq / y_train_seq (the shaped sequences) instead of X_train / y_train 
    """
    active = cfg.active.lower()
    print(f"[train] Training linear model: {active}")
    linear_model = build_linear()
    linear_model.fit(X_train, y_train)

    print("[train] Training MLP (residual)...")
    if scaler_y is None:
        raise ValueError("scaler_y required for MLP")

    mlp_model = build_mlp_optuna(X_train, y_train, scaler_y, cfg)

    return {
        "linear": linear_model,
        "mlp": mlp_model
    }