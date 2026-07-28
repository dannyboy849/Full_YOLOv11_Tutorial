"""
src/evaluate.py
runs the trained model over the test set, inverse-transforms predictions,
computes per-state and overall metrics, and returns the results

called by: run_pipeline.py
"""

import numpy as np

from utils.metrics              import overall_metrics, per_state_metrics
from sklearn.metrics            import mean_squared_error
from sklearn.inspection         import permutation_importance
from sklearn.preprocessing      import StandardScaler
from sklearn.model_selection    import TimeSeriesSplit


def evaluate_model(
    model,
    X_test_scaled: np.ndarray,
    y_test_scaled: np.ndarray,
    scaler_y: StandardScaler,
    states_test_raw: np.ndarray,
    state_vars: list[str],
    thresholds=None,
) -> tuple[dict, np.ndarray, np.ndarray]:
    
    """
    parameters
    ----------
    model           : trained sklearn / keras model
    X_test_scaled   : scaled feature matrix (n_samples, n_features)
    y_test_scaled   : scaled delta targets  (n_samples, n_outputs)
    scaler_y        : fitted target scaler
    states_test_raw : raw current states x_k  (n_samples, n_outputs)
    state_vars      : ordered list of state names matching columns

    this returns:
    -------
    results   : {"overall": {...}, "per_state": {name: {...}}}
    y_pred    : reconstructed next states (n_samples, n_outputs)
    y_actual  : reconstructed actual next states (n_samples, n_outputs)
    """



    # --------------------------------------------------
    # ── predict and inverse-transform ─────────────────
    # --------------------------------------------------

    delta_pred_scaled = model.predict(X_test_scaled)
    if delta_pred_scaled.ndim == 1:
        delta_pred_scaled = delta_pred_scaled.reshape(-1, 1)

    delta_pred   = scaler_y.inverse_transform(delta_pred_scaled)
    delta_actual = scaler_y.inverse_transform(y_test_scaled)

    # Δx = x_{k+1} - x_k 
    y_pred   = states_test_raw + delta_pred
    y_actual = states_test_raw + delta_actual



    # --------------------------------------------------
    # ── metrics ───────────────────────────────────────
    # --------------------------------------------------

    results = {
        "overall":   overall_metrics(y_actual, y_pred),
        "per_state": {},
    }

    print("\n" + "─" * 95)
    print(f"{'Variable':<45} {'rmse':>7} {'R²':>7} " # {'Acc':>7}
          f"{'Viol%':>7}") # {'Prec':>7} {'F1':>7} 
    print("─" * 95)

    for i, name in enumerate(state_vars):
        m = per_state_metrics(
            y_actual[:, i],
            y_pred[:, i],
            name,
            thresholds=thresholds,
        )
        results["per_state"][name] = m
        print(
            f"{name:<45} {m['rmse']:>7.4f} {m['R2']:>7.4f} "
            # f"{m['Accuracy']:>7.4f} {m['Precision']:>7.4f} "
            f"{m['Violation_%']:>6.2f}%" #{m['F1']:>7.4f}
        )

    ov = results["overall"]
    print("─" * 95)
    print(f"\n[evaluate] Overall rmse : {ov['rmse']:.4f}")
    print(f"[evaluate] Overall R²   : {ov['R2']:.4f}")

    return results, y_pred, y_actual


def time_series_cv_score(model, X, y, scaler_y, splits=3):
    tscv  = TimeSeriesSplit(n_splits=splits)
    rmses = []

    for tr_idx, val_idx in tscv.split(X):
        model.fit(X[tr_idx], y[tr_idx])

        pred = scaler_y.inverse_transform(model.predict(X[val_idx]))
        true = scaler_y.inverse_transform(y[val_idx])

        rmse = np.sqrt(mean_squared_error(
                            true, 
                            pred)
                        )
        rmses.append(rmse)

    return float(np.mean(rmses))


def compute_permutation_importance(model, X, y, feature_names):
    r     = permutation_importance(model, X, y, n_repeats=5, random_state=42)

    pairs = sorted(
        zip(feature_names, r.importances_mean),
        key=lambda x: -x[1]
    )
    print("\n[features] Permutation importance:")
    for f, v in pairs[:10]:
        print(f"{f:<25} {v:.4f}")

    return pairs