import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import mean_squared_error, r2_score
import joblib


# --- Configuration ---
CSV_FILE_PATH = 'Data/Flight_Data.csv'
MODEL_PATH = 'Outputs/drone_dynamics_best_model.pkl' # BayesianRidge here
SCALER_X_PATH = 'Outputs/feature_scaler_integrated.pkl'
SCALER_Y_PATH = 'Outputs/target_delta_scaler.pkl'


TIME_VAR = 'OSD.flyTime [s]'
ALTITUDE_VAR = 'OSD.altitude [m]' # Using raw name just for data read
# Define your final STATE_VARS and INPUT_VARS as they were in the main script
INPUT_VARS = ['RC.aileron', 'RC.elevator', 'RC.throttle', 'RC.rudder']
STATE_VARS = [
            'pos_east', 'pos_north', 'pos_up',
            'OSD.xSpeed [m/s]', 'OSD.ySpeed [m/s]', 'OSD.zSpeed [m/s]',
            'OSD.pitch', 'OSD.roll',
            'yaw_sin', 'yaw_cos', 
            'OSD.hSpeed [m/s]'
            ]


# PID Gains (These are example starting points, you can tune these!)
KP = 3.8 # Proportional gain (how hard we react to current error)
KI = 0.095 # Integral gain (how hard we react to accumulated error)
KD = 0.005  # Derivative gain (how hard we react to rate of change of error)




# ------------------------------------------------
# 1. Load and Prepare Data
# ------------------------------------------------

df = pd.read_csv(CSV_FILE_PATH)
df = df.sort_values(TIME_VAR).dropna(subset=[ALTITUDE_VAR, TIME_VAR])


# Load the trained BayesianRidge model and scalers
try:
    # Assuming you saved the best model instance in the previous script
    trained_model = joblib.load(MODEL_PATH) 
    scaler_X = joblib.load(SCALER_X_PATH)
    scaler_y = joblib.load(SCALER_Y_PATH)
except FileNotFoundError:
    print(f"Error: Model files not found. Run the main training script first.")
    exit()


time_points = df[TIME_VAR].values
actual_altitude_raw = df[ALTITUDE_VAR].values
dt = np.mean(df[TIME_VAR].diff().dropna()) # Average time step


# We need the initial state in the CORRECT format for the trained model
# You need the initial state vector Xk, which requires running your data prep function on the raw DF first
from Data-Driven_MPC import prepare_mpc_data # Import the data prep function


df_processed, FEATURES, STATE_VARS = prepare_mpc_data(df.copy())
initial_state_vector = df_processed[STATE_VARS].iloc[0].values.astype(float)
actual_inputs_df = df_processed[INPUT_VARS + ['BATTERY.voltage [V]', 'BATTERY.current [A]', 'WEATHER.windSpeed [m/s]', 'wind_dir_sin', 'wind_dir_cos', 'dT']]

# ------------------------------------------------
# 2. Run PID Simulation
# ------------------------------------------------

def run_pid_simulation_with_model(target_altitudes_raw, actual_inputs_df, dt, Kp, Ki, Kd, model, scaler_X, scaler_y, initial_state):
    simulated_states = []
    current_state = initial_state.copy()
    integral_error = 0
    previous_error = 0
    
    # Get the index for the 'pos_up' variable in your STATE_VARS list
    altitude_idx = STATE_VARS.index('pos_up')
    
    # We will use the *actual* altitude from the original flight data as the *target* for our PID controller
    for i, target_altitude_raw in enumerate(target_altitudes_raw[:-1]): # Iterate up to the second to last time step
        current_altitude_sim = current_state[altitude_idx]
        
        # Calculate PID error using the current simulated altitude and actual historical target
        error = target_altitude_raw - current_altitude_sim
        integral_error += error * dt
        derivative_error = (error - previous_error) / dt
        pid_output = (Kp * error) + (Ki * integral_error) + (Kd * derivative_error)
        
        # We assume PID output is a throttle command adjustment (0 to 1)
        # This is a highly simplified assumption for just altitude
        throttle_command_pid = np.clip(pid_output, 0.0, 1.0) 

        # --- Use the *Trained Data-Driven Model* for dynamics prediction ---
        # We need to construct the feature vector for the model
        # For a true comparison, we would use the actual historical aileron/elevator/rudder inputs
        
        # Extract the historical actual inputs and disturbances for this time step
        historical_inputs_and_features = actual_inputs_df.iloc[i].values
        
        # Adjust only the throttle input with our calculated PID output
        historical_inputs_and_features[INPUT_VARS.index('RC.throttle')] = throttle_command_pid

        # Construct the full feature vector X_k = [u_k, x_k, d_k, dT]
        features_vector = np.hstack([historical_inputs_and_features[:-1], current_state, historical_inputs_and_features[-1]]).reshape(1, -1)
        
        # Scale and predict the delta state
        features_scaled = scaler_X.transform(features_vector)
        delta_pred_scaled = model.predict(features_scaled)
        delta_pred = scaler_y.inverse_transform(delta_pred_scaled).flatten()

        # Update current state for next loop iteration: x_{k+1} = x_k + Δx_pred
        current_state += delta_pred
        simulated_states.append(current_state)
        
        previous_error = error
        
    return np.array(simulated_states)


# Run the PID Simulation with the Data-Driven Model
simulated_results_pid = run_pid_simulation_with_model(
    actual_altitude_raw, 
    actual_inputs_df, 
    dt, 
    KP, KI, KD, 
    trained_model, 
    scaler_X, scaler_y, 
    initial_state_vector
)
df_simulated_pid = pd.DataFrame(simulated_results_pid, columns=STATE_VARS)
df_simulated_pid[TIME_VAR] = time_points[1:] # Align time stamps

# ------------------------------------------------
# 3. Visualization and Comparison
# ------------------------------------------------

plt.figure(figsize=(12, 6))
# We compare the target (actual recorded flight path altitude) with the PID controller's simulated tracking
plt.plot(time_points, actual_altitude_raw, label='True Flight Data (Target Path)', color='red', linestyle='-')
plt.plot(df_simulated_pid[TIME_VAR], df_simulated_pid['pos_up'], label=f'Simulated PID Tracker (Kp={KP}) using Data Model', color='green')
plt.title('Altitude Control Comparison: True Flight vs. PID Simulation with Data Model')
plt.xlabel('Time (s)')
plt.ylabel('Altitude (m)')
plt.legend()
plt.grid(True)
plt.show()