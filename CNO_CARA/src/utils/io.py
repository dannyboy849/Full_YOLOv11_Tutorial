"""
utils/io.py
all of the file I/O: CSV loading, model/scaler persistence, metrics JSON
outputs: 
joblib (.pkl), ONNX (.onnx), MATLAB (.mat), TensorFlow SavedModel
"""

import json
import joblib
import scipy.io
import numpy        as np
import pandas       as pd
import tensorflow   as tf

from pathlib                    import Path
from skl2onnx                   import to_onnx
from sklearn.neural_network     import MLPRegressor
from sklearn.multioutput        import MultiOutputRegressor


# --------------------------------------------------
# ── CSV ───────────────────────────────────────────
# --------------------------------------------------

def load_csv(path: str | Path) -> pd.DataFrame:
    print(f"[io] Reading data source from: {path}")
    df = pd.read_csv(path, low_memory=False)
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")
    # df = pd.read_csv(path)
    print(f"[io] Loaded {len(df):,} rows from {path.name}")
    return df



# --------------------------------------------------
# ── simulink instructions ─────────────────────────
# --------------------------------------------------

def _print_simulink_instructions(mat_path: Path, mlp: MLPRegressor):
    """prints the MATLAB reconstruction code the user needs"""
    n_hidden = len(mlp.coefs_) - 1
    print(f"""
[io] ── simulink / MATLAB import instructions ──────────────────
Load weights in MATLAB:
  data = load('{mat_path.name}');

reconstruct network (Neural Network Toolbox):
  net = feedforwardnet({[mlp.coefs_[i].shape[1] for i in range(n_hidden)]});
  net = configure(net, zeros(data.n_inputs,1), zeros(data.n_outputs,1));
  for i = 1:data.n_layers
    net.IW{{i,1}} = data.weights(i).W;   % or LW for later layers
    net.b{{i}}    = data.biases(i).b;
  end

or, use the ONNX importer:
  net = importNetworkFromONNX('{mat_path.with_suffix(".onnx").name}');
  dlnet = dlnetwork(net);

or the MPC bundle (A, B matrices):
  bundle = load('{mat_path.stem.replace("mlp_best_model","dynamics_best_model")}.mat');
  A = bundle.A;  B = bundle.B;
────────────────────────────────────────────────────────────────
""")



# --------------------------------------------------
# ── saves models and scalers ──────────────────────
# --------------------------------------------------

def save_model(obj, path: str | Path, X_sample=None) -> None:
    """
    save a trained model or scaler

    saves a .pkl (joblib)
    if obj is sklearn MLPRegressor and X_sample is
    available, also saves:
      - .onnx   for Simulink / ONNX Runtime
      - .mat    for MATLAB / Simulink direct import

    parameters
    ----------
    obj      : fitted sklearn model or scaler
    path     : output path (.pkl extension)
    X_sample : float32 numpy array; one rep. input row
               for ONNX/MAT export. pass X_tr_s[:1]
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # save joblib 
    joblib.dump(obj, path)
    print(f"[io] Saved pkl  → {path}")

    #  ONNX export (MLP only) 
    if X_sample is not None:
        _try_save_onnx(obj, path, X_sample)
        _try_save_mat(obj, path, X_sample)


def _unwrap_mlp(obj):
    """
    returns the MLPRegressor whether obj is:
      - MLPRegressor directly
      - MultiOutputRegressor wrapping an MLPRegressor
      - anything else → returns None
    """
    if isinstance(obj, MLPRegressor):
        return obj
    if isinstance(obj, MultiOutputRegressor):
        # MultiOutputRegressor.estimators_ is a list of fitted estimators
        if hasattr(obj, 'estimators_') and obj.estimators_:
            inner = obj.estimators_[0]
            if isinstance(inner, MLPRegressor):
                return inner   # NOTE: single-output MLP — see MAT export note
    return None


def _try_save_onnx(obj, pkl_path: Path, X_sample: np.ndarray) -> None:
    """export sklearn model to ONNX. skips if not supported."""
    try:
        onnx_path = pkl_path.with_suffix('.onnx')
        X32 = X_sample[:1].astype(np.float32)

        # MultiOutputRegressor wrapping a linear model gives export wrapper
        # MLPRegressor will export directly
        mlp = _unwrap_mlp(obj)
        target = mlp if mlp is not None else obj

        onx = to_onnx(target, X32, target_opset=17)
        with open(onnx_path, "wb") as f:
            f.write(onx.SerializeToString())
        print(f"[io] Saved onnx → {onnx_path}")

    except Exception as e:
        print(f"[io] ONNX export skipped for {pkl_path.name}: {e}")


def _try_save_mat(obj, pkl_path: Path, X_sample: np.ndarray) -> None:
    """
    export MLP weights/biases to .mat for Simulink Neural Network block.

    MATLAB Neural Network Predictive Controller wants:
      IW{1,1}  — input weight matrix  (hidden_1 × n_inputs)
      LW{i,j}  — layer weight matrices
      b{i}     — bias vectors
      layerSizes, activationFcn, inputRange

    exports a struct that can be loaded into MATLAB and
    used to recon. the network with the Neural Network Toolbox
    """
    mlp = _unwrap_mlp(obj)
    if mlp is None:
        return   # only export MLPs

    try:
        mat_path = pkl_path.with_suffix('.mat')
        mat_dict = _mlp_to_mat_struct(mlp, X_sample)
        scipy.io.savemat(str(mat_path), mat_dict)
        print(f"[io] Saved mat  → {mat_path}")
        _print_simulink_instructions(mat_path, mlp)

    except Exception as e:
        print(f"[io] MAT export skipped for {pkl_path.name}: {e}")


def _mlp_to_mat_struct(mlp: MLPRegressor,
                       X_sample: np.ndarray) -> dict:
    """
    conv. sklearn MLPRegressor weights to MATLAB struct.

    MATLAB naming follows Neural Network Toolbox convention, so the
    .mat can be loaded and the network reconstructed with:
        net = network_from_datum(load('drone_mlp_best_model.mat'))
    """
    n_layers = len(mlp.coefs_)
    mat = {
        # architecture
        'n_inputs':    np.array([[X_sample.shape[1]]],  dtype=np.float64),
        'n_outputs':   np.array([[mlp.coefs_[-1].shape[1]]], dtype=np.float64),
        'n_layers':    np.array([[n_layers]],            dtype=np.float64),
        'layer_sizes': np.array([[c.shape[1] for c in mlp.coefs_]],
                                 dtype=np.float64),
        'activation':  np.array([mlp.activation]),

        # weights and biases (1-indexed cell array)
        # MATLAB cell arrays stored as object arrays in scipy.io
        'weights':     np.empty((1, n_layers), dtype=object),
        'biases':      np.empty((1, n_layers), dtype=object),

        # input normalisation
        # filled in by save_model_with_scalers() if called from DATUM.py
        'input_mean':  np.zeros((1, X_sample.shape[1])),
        'input_std':   np.ones((1, X_sample.shape[1])),
    }

    for i, (W, b) in enumerate(zip(mlp.coefs_, mlp.intercepts_)):
        mat['weights'][0, i] = W.astype(np.float64)
        mat['biases'][0,  i] = b.astype(np.float64).reshape(-1, 1)

    return mat


# --------------------------------------------------
# ── save mpc ──────────────────────────────────────
# --------------------------------------------------

def save_mpc_bundle_mat(bundle: dict, pkl_path: str | Path) -> None:
    """
    Export the MPC bundle (A, B, ref_traj, u_min, u_max, dT) to .mat.
    Called separately from save_model() because bundles aren't sklearn objs.

    In Simulink, load with:
      b = load('drone_dynamics_best_model.mat');
      A = b.A;  B = b.B;
      Use with State-Space block or custom MPC S-function.
    """
    pkl_path = Path(pkl_path)
    mat_path = pkl_path.with_suffix('.mat')

    mat_dict = {}
    for key, val in bundle.items():
        if isinstance(val, np.ndarray):
            mat_dict[key] = val.astype(np.float64)
        elif isinstance(val, (int, float)):
            mat_dict[key] = np.array([[val]], dtype=np.float64)
        elif isinstance(val, list):
            mat_dict[key] = np.array(val, dtype=np.float64)
        elif isinstance(val, str):
            mat_dict[key] = np.array([val])
        # skip non-serialisable objects (state_vars list of strings handled above)

    # state_vars / input_vars as char arrays
    if 'state_vars' in bundle:
        mat_dict['state_vars'] = np.array(bundle['state_vars'])
    if 'input_vars' in bundle:
        mat_dict['input_vars'] = np.array(bundle['input_vars'])

    scipy.io.savemat(str(mat_path), mat_dict)
    print(f"[io] Saved mat  → {mat_path}")



# --------------------------------------------------
# ── load model ────────────────────────────────────
# --------------------------------------------------

def load_model(path: str | Path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Model file not found: {path}")
    obj = joblib.load(path)
    print(f"[io] Loaded     ← {path}")
    return obj



# --------------------------------------------------
# ── saves JSON metrics ────────────────────────────
# --------------------------------------------------

def save_metrics(metrics: dict, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    def _serialise(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (np.float32, np.float64, np.int32, np.int64)):
            return float(obj)
        raise TypeError(f"Not serialisable: {type(obj)}")

    with open(path, "w") as f:
        json.dump(metrics, f, indent=2, default=_serialise)
    print(f"[io] Metrics saved → {path}")


def load_metrics(path: str | Path) -> dict:
    with open(path) as f:
        return json.load(f)


def save_config(cfg, path: str | Path) -> None:
    def _ser(obj):
        if hasattr(obj, "__dict__"):
            return vars(obj)
        return str(obj)
    with open(path, "w") as f:
        json.dump(cfg, f, default=_ser, indent=2)
    print(f"[io] Config saved → {path}")