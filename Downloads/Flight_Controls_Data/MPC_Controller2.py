# run_do_mpc_example.py
import numpy as np, joblib
from casadi import SX, vertcat
import do_mpc



# Linearized model x[k+1] ≈ A * x[k] + B * u[k]

# load saved AB and data
d = joblib.load('Outputs/drone_dynamics_best_model.pkl')
A = np.asarray(d['A'])
B = np.asarray(d['B'])
x0 = np.asarray(d['x0'])
u_min = d['u_min']; u_max = d['u_max']
dT = float(np.mean(d['dT']))
n_x = A.shape[0]
n_u = B.shape[1]


# Build do_mpc model (discrete-time linear)
model = do_mpc.model.Model('discrete')
x = model.set_variable(var_type='_x', var_name='x', shape=(n_x,1))
u = model.set_variable(var_type='_u', var_name='u', shape=(n_u,1))
rhs = SX(A) @ x + SX(B) @ u
model.set_rhs('x', expr=rhs)
xr = model.set_variable(var_type='_tvp', var_name='xr', shape=(n_x, 1))
model.setup()


# now create MPC controller from the prepared model
mpc = do_mpc.controller.MPC(model)
setup_mpc = {
    'n_horizon': 15,
    't_step': dT,
}
mpc.set_param(**setup_mpc)
# Debug prints 
print("do_mpc module:", getattr(do_mpc, "__version__", "no __version__"))

# Tuning:
# If tracking is slow or sluggish: You might need to increase the weight Q or n_horizon.
# If tracking is unstable or oscillatory: You might need to increase the input penalty R or reduce Q.
# If inputs hit constraints frequently: Check your u_min and u_max bounds and potentially adjust R.


# Q = np.eye(n_x)
# Q = np.zeros((n_x, n_x))
Q = np.diag([
    10.0, 10.0, 10.0,  # pos_east, pos_north, pos_up
    1.0, 1.0, 1.0,     # velocities
    0.0, 0.0,          # pitch/roll
    5.0, 5.0,          # yaw_sin, yaw_cos
    0.0                # hSpeed
])

# R = np.eye(n_u)*0.01
R = np.diag([0.05, 0.05, 20.0, 15.0])   # make throttle penalty large


# build objective in do_mpc: sum (x - xr)' Q (x - xr) + u' R u
x_diff = x - xr
lterm = x_diff.T @ Q @ x_diff + u.T @ R @ u 


# set objective
mpc.set_objective(lterm=lterm, mterm=SX(0)) 


# input constraints
for i in range(n_u):
    mpc.bounds['lower','_u', 'u'][i] = u_min[i]
    mpc.bounds['upper','_u', 'u'][i] = u_max[i]

# --------------------------------------------------
#  SIMULATION LOOP PREPARATION
# --------------------------------------------------


Tsim = 200
ref_traj_simple = np.tile(x0.flatten(), (Tsim, 1))
ref_traj_simple[:, 0] += 2.0 
ref_traj_simple[:, 8] = np.sin(np.pi/4) # Yaw to 45 degrees
ref_traj_simple[:, 9] = np.cos(np.pi/4)
ref_traj = ref_traj_simple 
Tsim = len(ref_traj)


# Add a placeholder/template TVP function required before setup()
def tvp_fun(t_now):
    tvp_array = mpc.get_tvp_template()
    for h in range(setup_mpc['n_horizon']):
        idx = min(int(t_now) + h, ref_traj.shape[0] - 1)
        tvp_array['_tvp', h, 'xr'] = ref_traj[idx].reshape((-1, 1))
    return tvp_array


mpc.set_tvp_fun(tvp_fun)

# --------------------------------------------------
#  MPC SETUP
# --------------------------------------------------

mpc.setup()


# Simulator (simple linear sim using same A,B)
simulator = do_mpc.simulator.Simulator(model)
tvp_template_sim = simulator.get_tvp_template()
simulator.set_tvp_fun(lambda t_now: tvp_template_sim)
simulator_config = {
    't_step': dT,
}
simulator.set_param(**simulator_config)
simulator.set_tvp_fun(lambda t_now: simulator.get_tvp_template())
simulator.setup()


# Set initial states for MPC and Simulator
x0 = x0.reshape((-1,1))
mpc.x0 = x0
mpc.set_initial_guess() 
simulator.x0 = x0 

x_hist = []
u_hist = []


for k in range(Tsim):
    u0 = mpc.make_step(x0)
    x0 = A @ x0 + B @ u0  
    x_hist.append(x0.flatten())
    u_hist.append(u0.flatten())


    # Instead of: x0 = A @ x0 + B @ u0  # simulate
    # You can:
    # 1. Send u0 commands to the drone hardware/physics engine
    # 2. Receive the actual next state measurement
    # 3. Update x0 with the measured state


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