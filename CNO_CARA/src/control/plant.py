"""
src/control/plant.py

plant functions for closed-loop simulation with MLP residual

called by: run_pipeline.py

"""

import numpy        as np
import casadi       as ca
import torch.nn     as nn


class PyTorchResidualMLP(nn.Module):
    def __init__(self, input_dim, output_dim, hidden_layers=[64, 64]):
        super().__init__()
        layers = []
        prev_dim = input_dim
        for h_dim in hidden_layers:
            layers.append(nn.Linear(prev_dim, h_dim))
            layers.append(nn.ReLU()) # Matches 'relu' in your bundle loader
            prev_dim = h_dim
        layers.append(nn.Linear(prev_dim, output_dim))
        self.network = nn.Sequential(*layers)

    def forward(self, x):
        return self.network(x)

print("Plants started...")

def stable_state_update(x, delta):

    # linear propagation
    x_next = x + delta
    return np.nan_to_num(x_next, nan=0.0, posinf=100.0, neginf=-100.0)


def safe_mlp_delta(mlp_model, scaler_X, scaler_y, x, u, aux, mapper):
    
    """
    safe and NaN-proof MLP residual inference
    """
    try:
        # evaluate feature mapping
        xu_raw = mapper.build(x, u, aux)
        
        # coerce to flat array layout for scikit-learn tracking consistency
        if hasattr(xu_raw, "toarray"):
            xu = xu_raw.toarray().reshape(1, -1)
        else:
            xu = np.asarray(xu_raw).reshape(1, -1)

        xu_scaled = scaler_X.transform(xu)
        delta = scaler_y.inverse_transform(
            mlp_model.predict(xu_scaled)
        ).flatten()
        return np.nan_to_num(delta, nan=0.0, posinf=0.0, neginf=0.0)
    except Exception:
        return np.zeros_like(x).flatten()
    

def make_mlp_plant(mlp_model, scaler_X, scaler_y, mapper, A, B,
                   x_mean, x_std, u_mean, u_std, wind_traj=None):
    """
    MLP-augmented plant for closed-loop simulation.

    x_{k+1} = (I+A)·x_s·σ_x + μ_x  +  g_θ(scaler_X([x,u]))
    """
    I_A          = np.eye(A.shape[0]) + A
    step_counter = [0]

    def plant_fn(x, u):
        x_raw    = x.flatten()
        u_raw    = u.flatten()

        # nominal step in phi-normalised space 
        x_scaled = (x_raw - x_mean) / x_std
        u_scaled = (u_raw - u_mean) / u_std

        linear_next_scaled = I_A @ x_scaled + B @ u_scaled
        linear_next        = linear_next_scaled * x_std + x_mean   # physical

        # MLP residual: pass RAW physical (x, u) — scaler_X applied inside
        residual_delta = safe_mlp_delta(
            mlp_model, scaler_X, scaler_y,
            x_raw, u_raw,         
            aux={},
            mapper=mapper,
        )

        x_next  = linear_next + residual_delta
        x_next  = stable_state_update(x_raw, x_next - x_raw)

        k       = step_counter[0]
        step_counter[0] += 1
        if wind_traj is not None:
            x_next += wind_traj[min(k, len(wind_traj) - 1)]

        return x_next.flatten()

    return plant_fn


def make_casadi_symbolic_plant(casadi_mlp_fn, mapper, A, B, x_mean, x_std, u_mean, u_std, wind_traj=None):
    """
    Evaluates the vehicle plant inside the simulation loop using analytical gradients.
    """
    n_x = A.shape[0]
    n_u = B.shape[1]

    # create static CasADi symbols for fast step evaluations
    x_sym = ca.SX.sym('x', n_x)
    u_sym = ca.SX.sym('u', n_u)
    
    # construct symbolic execution graph
    x_scaled = (x_sym - x_mean) / x_std
    u_scaled = (u_sym - u_mean) / u_std
    I_A = np.eye(n_x) + A
    linear_next = (I_A @ x_scaled + B @ u_scaled) * x_std + x_mean
    
    # use feature spec mapper to build the complete 28-feature array
    if casadi_mlp_fn is not None:
        # Build features symbolically via your blueprint specification mapping
        xu_features = mapper.build(x_sym, u_sym, aux={})
        if isinstance(xu_features, (list, tuple)):
            xu_features_vector = ca.vertcat(*xu_features)
        else:
            xu_features_vector = ca.reshape(xu_features, -1, 1)

        # run inference through the compiled neural network layers
        residual_delta = casadi_mlp_fn(xu_features_vector)
        x_next_sym = linear_next + residual_delta

    else:
        x_next_sym = linear_next

    # final graph into an C-function block
    fast_plant = ca.Function('fast_plant', [x_sym, u_sym], [x_next_sym])
    
    step_counter = [0]

    def plant_fn(x, u):
        x_raw = x.flatten()
        u_raw = u.flatten()
        
        # Fast numerical evaluation with zero overhead
        x_next = np.array(fast_plant(x_raw, u_raw)).flatten()
        
        k = step_counter[0]
        step_counter[0] += 1
        if wind_traj is not None:
            x_next += wind_traj[min(k, len(wind_traj) - 1)]
            
        return x_next

    return plant_fn