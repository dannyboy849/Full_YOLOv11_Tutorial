"""
utils/splits.py
time-series–safe train/test splitting and GRU sequence builder

used by: src/train.py
"""

import numpy as np

from sklearn.model_selection import TimeSeriesSplit


def time_series_split(
    X: np.ndarray,
    y: np.ndarray,
    test_fraction: float = 0.2,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    
    """
    chronological split
    returns X_train, X_test, y_train, y_test
    """

    split_idx = int(len(X) * (1 - test_fraction))
    return X[:split_idx], X[split_idx:], y[:split_idx], y[split_idx:]


def create_sequences(
    X: np.ndarray,
    y: np.ndarray,
    time_steps: int = 5,
) -> tuple[np.ndarray, np.ndarray]:
    
    """
    build overlapping windows for GRU input

    this returns:
    -------
    Xs : (n_samples, time_steps, n_features)
    ys : (n_samples, n_outputs)
    """

    Xs, ys = [], []
    for i in range(len(X) - time_steps):
        Xs.append(X[i : i + time_steps])
        ys.append(y[i + time_steps])
    return np.array(Xs), np.array(ys)


def get_tscv(n_splits: int = 5) -> TimeSeriesSplit:

    """returns a configured TimeSeriesSplit object for cross-validation."""

    return TimeSeriesSplit(n_splits=n_splits)
