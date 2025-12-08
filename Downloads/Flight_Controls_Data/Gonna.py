import numpy as np
import joblib
import matplotlib.pyplot as plt
import do_mpc
from casadi import SX
from scipy.linalg import solve_discrete_are


# load saved AB and data
d = joblib.load('Outputs/drone_dynamics_best_model.pkl')
A = np.asarray(d['A'])
B = np.asarray(d['B'])


STATE_VARS = d['state_vars']
INPUT_VARS = d['input_vars']


x0 = np.asarray(d['x0']).astype(float).reshape(-1, 1)   # column vector
# x0 = np.asarray(d['x0'])
ref_traj = np.asarray(d['ref_traj'])
dT = float(np.mean(d['dT']))
u_min = np.asarray(d.get('u_min', [-1.0]*B.shape[1]))
u_max = np.asarray(d.get('u_max', [1.0]*B.shape[1]))
# u_min = d['u_min']; u_max = d['u_max']


n_x = A.shape[0]
n_u = B.shape[1]


print('Loaded bundle. A shape', A.shape, 'B shape', B.shape)
print('n_x, n_u =', n_x, n_u, 'dT=', dT)




# ---------------------
# Detect delta-state vs direct-state model
# ---------------------
if np.max(np.abs(A)) < 1.5:   # typical dynamics; but presence of values near 1 implies direct model
    # If A rows mostly << 1, we'll still treat as direct. Use better heuristic:
    # if eigenvalues mostly < 0.999 and many near 0.99+ -> direct; but safe approach:
    # ask heuristics: if A has many elements < 0.2 treat as delta. else direct.
    frac_small = np.mean(np.abs(A) < 0.2)
    if frac_small > 0.6:
        model_type = 'delta'   # Δx = A x + B u, so x_next = x + A x + B u
    else:
        model_type = 'direct'  # x_next = A x + B u
else:
    model_type = 'direct'


print('Heuristic model_type =', model_type)


u_mid = 0.5 * (u_max + u_min)
u_half = 0.5 * (u_max - u_min)
normalize_u = True


B_norm = B * u_half.reshape(1, -1)

# Linearized model x[k+1] ≈ A * x[k] + B * u[k]




# ---------------------
# Discrete-Time do_mpc model
# ---------------------
model_type = 'discrete'
model = do_mpc.model.Model(model_type)


# states and inputs
x = model.set_variable(var_type='_x', var_name='x', shape=(n_x, 1))
u = model.set_variable(var_type='_u', var_name='u', shape=(n_u, 1))
u_prev = model.set_variable(var_type='_tvp', var_name='u_prev', shape=(n_u,1))


# Time-varying reference
xr = model.set_variable(var_type='_tvp', var_name='xr', shape=(n_x, 1)) 


# Discrete dynamics: x_{k+1} = A x + B u
A_cas = SX(A)  
B_cas = SX(B_norm if normalize_u else B)
# B_cas = SX(B)


B_mid = (B @ u_mid.reshape(-1,1)).reshape((-1,1))   # shape (n_x,1)
B_mid_cas = SX(B_mid)


rhs = A_cas @ x + B_cas @ u + B_mid_cas  # CasADi SX expression 
model.set_rhs('x', rhs)
model.setup()




# ---------------------
#  MPC controller
# ---------------------
mpc = do_mpc.controller.MPC(model)


# MPC parameters
N_horizon = 30
setup_mpc = {
    'n_horizon': N_horizon,
    't_step': dT,
}
mpc.set_param(**setup_mpc)


# If tracking is slow or sluggish: You might need to increase the weight Q or n_horizon.
# If tracking is unstable or oscillatory: You might need to increase the input penalty R or reduce Q.
# If inputs hit constraints frequently: Check your u_min and u_max bounds and potentially adjust R.

# objective: quadratic tracking
Q = np.diag([10,10,10, 5,5,5, 2,2,2, 1])

# weights
R_diag = [0.1, 0.1, 10.0, 0.1]   # heavy on throttle
R = np.diag(R_diag)


# Terminal cost from DARE
P = solve_discrete_are(
    np.asarray(A), 
    np.asarray(B_norm if normalize_u else B), 
    Q, R
)

# lterm and mterm
x_err = x - xr


du = u - u_prev
Rdu = SX(np.diag([0.1, 0.1, 5.0, 0.1]))   # tune: large on throttle delta
lterm = x_err.T @ SX(Q) @ x_err + u.T @ SX(R) @ u + du.T @ Rdu @ du
mterm = x_err.T @ SX(P) @ x_err


mpc.set_objective(lterm=lterm, mterm=mterm)

# input bounds: MPC uses normalized
for i in range(n_u):
    mpc.bounds['lower', '_u', 'u'][i] = -1.0
    mpc.bounds['upper', '_u', 'u'][i] = 1.0


def tvp_fun(t_now):
    tvp_template = mpc.get_tvp_template()
    k = int(t_now / dT)
    for h in range(N_horizon):
        idx = min(k + h, len(ref_traj)-1)
        tvp_template['_tvp', h, 'xr'] = ref_traj[idx].reshape((-1,1))
        # we will set u_prev externally each step (last known normalized u)
        # tvp_template['_tvp', h, 'u_prev'] = last_u_norm.reshape((-1,1))
    return tvp_template


mpc.set_tvp_fun(tvp_fun)


# helper: build a tvp function factory that returns tvp template for each time k
def make_tvp_for_step(k):
    tvp_template = mpc.get_tvp_template()
    # tvp_template indexing: tvp_template['_tvp', h, 'xr'] where h = 0..N_horizon-1
    for h in range(N_horizon):
        idx_ref = min(k + h, len(ref_traj)-1)
        tvp_template['_tvp', h, 'xr'] = ref_traj[idx_ref].reshape((-1, 1))
    return tvp_template


mpc.set_rterm(u=0.01)


# soft constraint: limit on throttle rate (optional). We'll add a small du penalty via rterm on u differences
# do_mpc can accept rterm on u; to penalize Δu more, we'll slightly increase R or add tvp of u_prev in objective (advanced).
mpc.setup()


mpc.x0 = x0
mpc.set_initial_guess()




# ---------------------
# Simulator (simple linear sim)
# ---------------------
simulator = do_mpc.simulator.Simulator(model)
simulator.set_param(t_step=dT)

mpc_tvp_template = mpc.get_tvp_template()
def sim_tvp_fun(t_now):
    return mpc_tvp_template

tvp_template_sim = simulator.get_tvp_template()

def sim_tvp_fun(t_now):
    k = int(t_now / dT)
    tvp_template_sim['xr'] = ref_traj[min(k, len(ref_traj)-1)].reshape((-1,1))
    return tvp_template_sim

simulator = do_mpc.simulator.Simulator(model)
simulator.set_param(t_step=dT)
simulator.set_tvp_fun(sim_tvp_fun)
simulator.setup()




# ---------------------
# initialize mpc with x0
# ---------------------
mpc.x0 = x0
mpc.set_initial_guess()




# ---------------------
# Run closed-loop tracking using ref_traj as TVP: fill tvp template each step
# ---------------------
Tsim = min(len(ref_traj), 800)   # limit simulation length for speed
x_hist = np.zeros((Tsim, n_x))
u_hist = np.zeros((Tsim, n_u))


x_curr = x0.copy()


for k in range(Tsim):

    # compute optimal u_norm
    u_opt = mpc.make_step(x_curr)

    # convert normalized u to raw for simulation if normalization enabled
    if normalize_u:
        u_raw = u_mid.reshape((-1,1)) + u_half.reshape((-1,1)) * u_opt.reshape((-1,1))
    else:
        u_raw = u_opt.reshape((-1,1))

    x_next = A @ x_curr + B @ u_raw

    x_hist[k, :] = x_next.flatten()
    u_hist[k, :] = u_raw.flatten()

    x_curr = x_next.copy()
    mpc.x0 = x_curr




# ---------------------
# Save and plot results
# ---------------------
np.savez('Outputs/do_mpc_run_results.npz', x_hist=x_hist, u_hist=u_hist, ref_traj=ref_traj[:Tsim])
print('Saved Outputs/do_mpc_run_results.npz')


# plot a few states (first three for example)
time = np.arange(Tsim) * dT
plt.figure(figsize=(9,5))
for i in range(min(3, n_x)):
    plt.subplot(3,1,i+1)
    plt.plot(time, x_hist[:, i], label=f'MPC x[{i}]')
    if Tsim <= len(ref_traj):
        plt.plot(time, ref_traj[:Tsim, i], '--', label=f'ref[{i}]')
    plt.legend()
plt.tight_layout()
plt.show()


plt.figure(figsize=(9,4))
for j in range(n_u):
    plt.plot(time, u_hist[:, j], label=f'u_raw[{j}]')
plt.title('Applied control (raw units)')
plt.legend()
plt.show()
# ---------------------



# convert to arrays and plot externally
x_hist = np.array(x_hist)
u_hist = np.array(u_hist)
print('Finished MPC run.')
joblib.dump((x_hist, u_hist), 'Outputs/drone_sim_results.pkl')


"""
def save_do_mpc_bundle(path='Outputs/do_mpc_bundle.pkl', A=None, B=None, scaler_X=None, scaler_y=None, state_vars=None, input_vars=None, x0=None, ref_traj=None, u_min=None, u_max=None, dT=None):
    payload = {
        'A': A, 'B': B, 'state_vars': state_vars, 'input_vars': input_vars,
        'x0': x0, 'ref_traj': ref_traj, 'u_min': u_min, 'u_max': u_max, 'dT': dT
    }
    joblib.dump(payload, path)
    if scaler_X is not None: joblib.dump(scaler_X, path.replace('.pkl','_scalerX.pkl'))
    if scaler_y is not None: joblib.dump(scaler_y, path.replace('.pkl','_scalery.pkl'))
    print('Saved do_mpc bundle to', path)

def load_do_mpc_bundle(path='Outputs/do_mpc_bundle.pkl'):
    payload = joblib.load(path)
    return payload 
"""