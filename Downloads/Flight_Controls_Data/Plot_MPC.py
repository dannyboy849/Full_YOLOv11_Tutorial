import joblib
import numpy as np
import matplotlib.pyplot as plt


# Load the simulation results
x_hist, u_hist = joblib.load('Outputs/drone_sim_results.pkl')
d = joblib.load('Outputs/drone_dynamics_best_model.pkl')


# Extract necessary data for plotting
ref_traj_full = np.asarray(d['ref_traj'])
dT = float(np.mean(d['dT']))

STATE_VARS = d.get('state_vars', [f'State x[{i}]' for i in range(x_hist.shape[1])])
INPUT_VARS = d.get('input_vars', [f'Input u[{i}]' for i in range(u_hist.shape[1])])


# Define lengths and time array properly
Tsim_steps = x_hist.shape[0]  # Total of time steps simulated
n_x = x_hist.shape[1]         # Number of states
n_u = u_hist.shape[1]         # Number of inputs


# Time array covers Tsim_steps
time = np.arange(Tsim_steps) * dT 
ref_traj = ref_traj_full[:Tsim_steps, :]




# Plot States vs Reference
plt.figure(figsize=(14, 9))
for i in range(n_x):
    plt.subplot(n_x, 1, i + 1)
    plt.plot(time, x_hist[:, i], label=f'Actual {STATE_VARS[i]}')
    plt.plot(time, ref_traj[:, i], 'r--', label=f'Reference {STATE_VARS[i]}')
    plt.ylabel(STATE_VARS[i], fontsize=12)
    plt.legend(loc='upper left')
    plt.grid(True)

plt.xlabel('Time (s)')
plt.suptitle('MPC State Tracking Results')
plt.savefig('MPC_Output/State_vs_Reference.pdf', dpi=600, bbox_inches='tight')
plt.savefig('MPC_Output/State_vs_Reference.png', dpi=600, bbox_inches='tight')
plt.tight_layout()
plt.show()


# Plot Inputs
plt.figure(figsize=(10, 6))
time_u = time[:u_hist.shape[0]] 
for i in range(n_u):
    plt.subplot(n_u, 1, i + 1)
    plt.plot(time_u, u_hist[:, i], label=f'Command {INPUT_VARS[i]}')
    plt.ylabel(INPUT_VARS[i], fontsize=12)
    plt.legend()
    plt.grid(True)
plt.xlabel('Time (s)')
plt.suptitle('MPC Input Commands')
plt.savefig('MPC_Output/Inputs.pdf', dpi=600, bbox_inches='tight')
plt.savefig('MPC_Output/Inputs.png', dpi=600, bbox_inches='tight')
plt.show()


plt.figure(figsize=(10, 4))
plt.plot(time, x_hist[:, 8], label='Actual Yaw Sin (x[8])')
plt.plot(time, ref_traj[:, 8], 'r--', label='Reference Yaw Sin (xr[8])')
plt.ylabel('Yaw Sin Value', fontsize=12)
plt.xlabel('Time (s)', fontsize=12)
plt.legend()
plt.grid(True)
plt.savefig('MPC_Output/Yaw_sin.pdf', dpi=600, bbox_inches='tight')
plt.savefig('MPC_Output/Yaw_sin.png', dpi=600, bbox_inches='tight')
plt.show()