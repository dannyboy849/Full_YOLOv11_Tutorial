import os
import joblib, json, numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import optuna

from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPRegressor
from sklearn.linear_model import Ridge
from sklearn.linear_model import BayesianRidge
from sklearn.multioutput import MultiOutputRegressor
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.multioutput import MultiOutputRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import TimeSeriesSplit
from scipy.signal import savgol_filter

import warnings
warnings.filterwarnings("ignore", category=UserWarning)



# ------------------------------------------------
# 1: Configuration
# ------------------------------------------------


CSV_FILE_PATH = 'Data/Flight_Data3.csv'
# CSV_TEST_PATH = 'Data/Flight_Data3.csv'
MODEL_OUTPUT_PATH = 'Outputs/drone_dynamics_model.pkl'
BEST_MLP_MODEL_PATH = 'Outputs/drone_mlp_best_model.pkl'    
BEST_MODEL_OUTPUT_PATH = 'Outputs/drone_dynamics_best_model.pkl'
# FEATURE_SCALER_PATH = 'Outputs/feature_scaler.pkl'
# TARGET_SCALER_PATH = 'Outputs/target_scaler.pkl'


INPUT_VARS = ['RC.aileron', 
              'RC.elevator', 
              'RC.throttle', 
              'RC.rudder'
]


STATE_VARS_OG = [
    'OSD.latitude',
    'OSD.longitude',
    'OSD.altitude [m]',
    'OSD.xSpeed [m/s]',
    'OSD.ySpeed [m/s]',
    'OSD.zSpeed [m/s]',
    'OSD.pitch',
    'OSD.roll',
    'OSD.hSpeed [m/s]'
]


# Real wind data
AUXILIARY_VARS = [
    'WEATHER.windSpeed [m/s]', 'WEATHER.windDirection'
]


FEATURES = []


TARGET_DELTA = []


# ensure outputs directory exists
os.makedirs('Outputs', exist_ok=True)




# ------------------------------------------------
# 2: Data Preparation and Preprocessing
# ------------------------------------------------

def prepare_mpc_data(df):
    df = df.sort_values('OSD.flyTime [s]').reset_index(drop=True)


    # time step (dT)
    df['dT'] = df['OSD.flyTime [s]'].diff().bfill() 


    core_columns = [col for col in INPUT_VARS + STATE_VARS_OG if col in df.columns]
    before_core_drop = len(df)
    df = df.dropna(subset=core_columns).reset_index(drop=True)
    after_core_drop = len(df)
    print(f'prepare_mpc_data_integrated: dropped {before_core_drop - after_core_drop} rows due to missing core flight data.')


    if len(df) == 0:
        raise ValueError("No data remains after dropping rows with missing core flight/RC data.")


    # convert Lat/Lon to coords
    lat0 = np.radians(df['OSD.latitude'].iloc[0])
    lon0 = np.radians(df['OSD.longitude'].iloc[0])
    lat = np.radians(df['OSD.latitude'])
    lon = np.radians(df['OSD.longitude'])
    R_earth = 6378137.0 # meters
    df['pos_east']  = (lon - lon0) * R_earth * np.cos(lat0)
    df['pos_north'] = (lat - lat0) * R_earth
    df['pos_up'] = df['OSD.altitude [m]']


    # fill wind data NaNs if none
    df['WEATHER.windSpeed [m/s]'] = pd.to_numeric(df['WEATHER.windSpeed [m/s]'], errors='coerce').fillna(0.0)


    # convert wind direction degrees to radians first
    direction_map = {
        'N': 0.0, 'NNE': 22.5, 'NE': 45.0, 'ENE': 67.5, 'E': 90.0, 'ESE': 112.5, 'SE': 135.0, 
        'SSE': 157.5, 'S': 180.0, 'SSW': 202.5, 'SW': 225.0, 'WSW': 247.5, 'W': 270.0, 
        'WNW': 292.5, 'NW': 315.0, 'NNW': 337.5
    }


    # map the strings to floats, filling NaNs if not found
    df['WEATHER.windDirection_deg'] = df['WEATHER.windDirection'].map(direction_map)
    df['WEATHER.windDirection_deg'] = df['WEATHER.windDirection_deg'].fillna(0.0) 


    # degree column for sin/cos
    wind_direction_rad = np.radians(df['WEATHER.windDirection_deg'])
    df['wind_dir_sin'] = np.sin(wind_direction_rad)
    df['wind_dir_cos'] = np.cos(wind_direction_rad)
    df['wind_e'] = df['WEATHER.windSpeed [m/s]'] * df['wind_dir_cos']
    df['wind_n'] = df['WEATHER.windSpeed [m/s]'] * df['wind_dir_sin']


    # added Sin/Cos calc. to improve yaw error
    yaw_rad = np.radians(pd.to_numeric(df['OSD.yaw'], errors='coerce').fillna(0.0))
    df['yaw_sin'] = np.sin(yaw_rad)
    df['yaw_cos'] = np.cos(yaw_rad)


    # updated STATE_VARS w/ local coords + yaw improvement
    STATE_VARS = [
        'pos_east', 'pos_north', 'pos_up',
        'OSD.xSpeed [m/s]', 'OSD.ySpeed [m/s]', 'OSD.zSpeed [m/s]',
        'OSD.pitch', 'OSD.roll',
        'yaw_sin', 'yaw_cos', 
        'OSD.hSpeed [m/s]',
    ]


    # target delta variables: Δx = x_{k+1} - x_k
    for var in STATE_VARS:
        df[f'{var}_next'] = df[var].shift(-1)
        df[f'delta_{var}'] = df[f'{var}_next'] - df[var]


    # add dT for training
    global TARGET_DELTA 
    TARGET_DELTA = [f'delta_{s}' for s in STATE_VARS]
    

    # define all features
    global FEATURES
    FEATURES = INPUT_VARS + STATE_VARS + ['wind_e', 'wind_n' , 'dT']


    # drop NaNs
    df[FEATURES + TARGET_DELTA] = df[FEATURES + TARGET_DELTA].apply(pd.to_numeric, errors='coerce')
    df = df.dropna(subset=FEATURES + TARGET_DELTA).reset_index(drop=True)
    

    cols_to_check = STATE_VARS + ['OSD.yaw']
    df[cols_to_check].head(50).to_csv('Outputs/test_output.csv', index=False)
    print("Saved 'Outputs/test_output.csv' for debugging.")

    
    print(f"prepare_mpc_data_integrated: remaining rows: {len(df)}")
    return df, FEATURES, STATE_VARS




# ------------------------------------------------
# 3. Wind Estimation
# ------------------------------------------------

def estimate_wind_from_residuals(actual_next_states, predicted_next_states, STATE_VARS, df_processed, split_idx):
    
    # indices for ENU positions and velocities
    ve_idx = STATE_VARS.index('OSD.xSpeed [m/s]')
    vn_idx = STATE_VARS.index('OSD.ySpeed [m/s]')



    N_test = predicted_next_states.shape[0]


    # extract measured_v at indices split_idx+0
    N_test = predicted_next_states.shape[0]


    # align the indices correctly with the test set
    V_ground_east = df_processed['OSD.xSpeed [m/s]'].values[split_idx : split_idx + N_test]
    V_ground_north = df_processed['OSD.ySpeed [m/s]'].values[split_idx : split_idx + N_test]

    # calculate Air Speed Vector
    V_air_east = predicted_next_states[:, ve_idx] 
    V_air_north = predicted_next_states[:, vn_idx]

    # calculate Wind Speed Vector
    V_wind_east = V_ground_east - V_air_east
    V_wind_north = V_ground_north - V_air_north


    # speed & direction
    est_speed = np.sqrt(V_wind_east**2 + V_wind_north**2)
    dir_rad = np.arctan2(V_wind_north, V_wind_east)
    dir_deg = np.degrees(dir_rad)
    est_dir_from = (270 - dir_deg) % 360 

    # smooth the speed/direction data to reduce sensor noise
    if len(est_speed) >= 51:
        est_speed = savgol_filter(est_speed, 51, 3)
        V_wind_east = savgol_filter(V_wind_east, 51, 3)
        V_wind_north = savgol_filter(V_wind_north, 51, 3)
        dir_rad_smooth = np.arctan2(V_wind_north, V_wind_east)
        est_dir_from = (270 - np.degrees(dir_rad_smooth)) % 360
        

    return est_speed, est_dir_from, V_wind_east, V_wind_north



# ------------------------------------------------
# 4. Boundary Violations
# ------------------------------------------------

def analyze_violations(actual_data, predicted_data, state_name):
    # Calculate errors
    errors = predicted_data - actual_data
    if state_name in ['Yaw Angle', 'OSD.yaw']:
        errors = (errors + 180) % 360 - 180 
        

    # Calculate the standard deviation of the errors from the test set
    std_dev_error = np.std(errors)
    

    # 95% confidence prediction is correct
    safety_threshold = 2 * std_dev_error
    


    # Check where the absolute error exceeds threshold
    violations = np.abs(errors) > safety_threshold
    

    # Calculate the percentage of time points that are violations
    violation_percentage = (np.sum(violations) / len(errors)) * 100
    

    print(f"\n--- Safety Analysis for {state_name} ---")
    print(f"Error Std Dev (1-Sigma): {std_dev_error:.4f}")
    print(f"Safety Threshold (+/- 2-Sigma): {safety_threshold:.4f}")
    print(f"Violation Rate: {violation_percentage:.2f}% of time steps violate the boundary.")
    

    return violation_percentage, safety_threshold, errors




# ------------------------------------------------
# 5: Main script 
# ------------------------------------------------

if __name__ == '__main__':
    df = pd.read_csv(CSV_FILE_PATH)
    df_processed, FEATURES, STATE_VARS = prepare_mpc_data(df)    
    print(f"Data prepared. Total samples: {len(df_processed)}")


    # separates features (X) and targets (y)
    X = df_processed[FEATURES].values.astype(float)
    y = df_processed[TARGET_DELTA].values.astype(float)


    # split
    N = len(X)
    split_idx = int(N * 0.66) 
    X_train_raw = X[:split_idx]
    y_train_raw = y[:split_idx]
    X_test_raw = X[split_idx:]
    y_test_raw = y[split_idx:]

    
    # df_train = pd.read_csv(CSV_FILE_PATH)
    # X_train_raw = df_train[X].values
    # y_train_raw = df_train[y].values


    # df_test = pd.read_csv(CSV_TEST_PATH)
    # X_test_raw = df_test[X].values
    # y_test_raw = df_test[y].values


    # states for baseline
    states_test_raw = df_processed[STATE_VARS].values[split_idx:]
    states_next_test_actual = states_test_raw + y_test_raw


    # scales features for better performance
    scaler_X = StandardScaler()
    X_train_scaled = scaler_X.fit_transform(X_train_raw)
    X_test_scaled = scaler_X.transform(X_test_raw) 
    joblib.dump(scaler_X, 'Outputs/feature_scaler_integrated.pkl')

    # scales targets for NNs
    scaler_y = StandardScaler()
    y_train_scaled = scaler_y.fit_transform(y_train_raw)
    y_test_scaled = scaler_y.transform(y_test_raw)
    joblib.dump(scaler_y, 'Outputs/target_delta_scaler.pkl')

    print(f"Chronological split -> Train: {len(X_train_scaled)}, Test: {len(X_test_scaled)}")


    # base MLP model training
    mlp_model = MLPRegressor(hidden_layer_sizes=(128, 64),
                        max_iter=1500, 
                        solver='adam',  
                        random_state=42,
                        early_stopping=True,
                        verbose=False)
    
    # fit the model
    mlp_model.fit(X_train_scaled, y_train_scaled)
    

# Copy + Paste of initial MPC run
# EXIT: Optimal Solution Found.
#            S  :   t_proc      (avg)   t_wall      (avg)    n_eval
#        nlp_f  |   5.00us (  2.50us)   4.59us (  2.29us)         2
#        nlp_g  |  18.00us (  9.00us)  16.73us (  8.36us)         2
#   nlp_grad_f  |   9.00us (  3.00us)   7.97us (  2.66us)         3
#   nlp_hess_l  |   2.00us (  2.00us)   1.65us (  1.65us)         1
#    nlp_jac_g  |  25.00us (  8.33us)  25.24us (  8.41us)         3
#        total  |   1.17ms (  1.17ms)   1.17ms (  1.17ms)         1
# Finished MPC run.

# EXIT: Optimal Solution Found.
#            S  :   t_proc      (avg)   t_wall      (avg)    n_eval
#        nlp_f  |   4.00us (  2.00us)   3.96us (  1.98us)         2
#        nlp_g  |  16.00us (  8.00us)  14.54us (  7.27us)         2
#   nlp_grad_f  |  10.00us (  3.33us)   8.14us (  2.71us)         3
#   nlp_hess_l  |   1.00us (  1.00us)   1.45us (  1.45us)         1
#    nlp_jac_g  |  25.00us (  8.33us)  25.70us (  8.57us)         3
#        total  |   1.14ms (  1.14ms)   1.14ms (  1.14ms)         1
# Finished MPC run.


# ------------------------------------------------
# 6. Model Benchmarking and Hyperparameter Optimization
# ------------------------------------------------

    print("\nStarting Model Benchmarking...")


    # predict scaled values, then inverse transform
    delta_pred_test_scaled = mlp_model.predict(X_test_scaled)
    delta_pred_test = scaler_y.inverse_transform(delta_pred_test_scaled)


    # pred next absolute state: x_{k+1} = x_k + Δx_pred
    states_next_pred = states_test_raw + delta_pred_test 


    # evaluate the model
    overall_rmse = np.sqrt(mean_squared_error(states_next_test_actual, states_next_pred))
    overall_r2 = r2_score(states_next_test_actual, states_next_pred)


    # setup evaluation functions
    def evaluate_model(model, X_test_scaled, y_test_scaled, scaler_y, states_test_raw, STATE_VARS):
        """Predicts, inverse transforms, and evaluates RMSE/R2 for all states."""


        # predict scaled deltas, then inverse transform again
        delta_pred_test_scaled = model.predict(X_test_scaled)
        delta_pred_test = scaler_y.inverse_transform(delta_pred_test_scaled)


        # reconstruct the predicted next absolute state: x_{k+1} = x_k + Δx_pred
        states_next_pred = states_test_raw + delta_pred_test 
        

        # calculate actual next states for comparison (actual current state + actual delta)
        states_next_test_actual = states_test_raw + scaler_y.inverse_transform(y_test_scaled)


        # equations for RMSE/R^2
        overall_rmse = np.sqrt(mean_squared_error(states_next_test_actual, states_next_pred))
        overall_r2 = r2_score(states_next_test_actual, states_next_pred)
        

        # print(f"\n--- Base Ridge Model Results ---")
        print(f"Overall RMSE: {overall_rmse:.4f}")
        print(f"Overall R^2 Score: {overall_r2:.4f}")


        results_by_state = {}
        for i, s in enumerate(STATE_VARS):
            rmse_s = np.sqrt(mean_squared_error(states_next_test_actual[:,i], states_next_pred[:,i]))
            r2_s = r2_score(states_next_test_actual[:,i], states_next_pred[:,i])
            results_by_state[s] = {'RMSE': rmse_s, 'R2': r2_s}
            print(f"Variable: {s:20s} RMSE: {rmse_s:.4f}  R2: {r2_s:.4f}")
        

        return overall_rmse, results_by_state, states_next_pred, states_next_test_actual



    # --- Checking for Data Leakage ---

    # normalized RMSE per state
    normed = {}
    for i, s in enumerate(STATE_VARS):
        rmse_s = np.sqrt(mean_squared_error(states_next_test_actual[:, i], states_next_pred[:, i]))
        std_s = np.std(states_next_test_actual[:, i])
        normed[s] = rmse_s / (std_s if std_s > 0 else 1.0)
    print("Normalized RMSE (RMSE / std) per state:")
    for s, v in normed.items():
        print(f"  {s:20s}: {v:.4f}")


    print(f"Data Leakage Detected: {any(c.endswith('_next') for c in FEATURES)}")    



    # --- Benchmarking all models ---

    def run_benchmarks(X_train_scaled, X_test_scaled, y_train_scaled, y_test_scaled, scaler_y, states_test_raw, STATE_VARS):
        
        # 1. Ridge Regression
        print("\nRidge Regression:")
        ridge_model = Ridge()
        ridge_model.fit(X_train_scaled, y_train_scaled)
        _, _, ridge_preds, actual_next_states = evaluate_model(ridge_model, X_test_scaled, y_test_scaled, scaler_y, states_test_raw, STATE_VARS)


        # 2. BayesianRidge Regression
        print("\nBayesianRidge Regression:")
        br_base = BayesianRidge()
        br_model = MultiOutputRegressor(br_base) 
        br_model.fit(X_train_scaled, y_train_scaled)
        _, _, br_preds, _ = evaluate_model(br_model, X_test_scaled, y_test_scaled, scaler_y, states_test_raw, STATE_VARS)


        # 3. Random Forest Regressor
        print("\nRandom Forest:")
        rf_model = RandomForestRegressor(n_estimators=100, 
                                         random_state=42, 
                                         n_jobs=-1)
        rf_model.fit(X_train_scaled, y_train_scaled)
        _, _, rf_preds, _ = evaluate_model(rf_model, X_test_scaled, y_test_scaled, scaler_y, states_test_raw, STATE_VARS)
            

        # 4. Linear Regression
        print("\nLinear Regression:")
        lr_base = LinearRegression()
        lr_model = MultiOutputRegressor(lr_base)
        lr_model.fit(X_train_scaled, y_train_scaled)
        _, _, lr_preds, _ = evaluate_model(lr_model, X_test_scaled, y_test_scaled, scaler_y, states_test_raw, STATE_VARS)

        
        # 5. MLP Regressor
        print("\nMLP Regression:")
        mlp_model = MLPRegressor(hidden_layer_sizes=(108, 64),
                            learning_rate='adaptive',
                            max_iter=1000, 
                            solver='adam',  
                            random_state=42,
                            early_stopping=True,
                            verbose=False)
        mlp_model.fit(X_train_scaled, y_train_scaled)
        _, _, mlp_preds, _ = evaluate_model(mlp_model, X_test_scaled, y_test_scaled, scaler_y, states_test_raw, STATE_VARS)




        # 6. Hyperparameter Optimization for MLP using Optuna
        print("\nStarting MLP Hyperparameter Optimization (Using Optuna Bayesian Search)...")


        def objective(trial):
            n1 = trial.suggest_int('n1', 64, 200)
            n2 = trial.suggest_int('n2', 0, 150)
            hidden = (n1, n2) if n2 > 0 else (n1,)
            alpha = trial.suggest_float('alpha', 1e-6, 1e-2)
            batch = trial.suggest_categorical('batch_size', [32, 64, 128])
            activation = trial.suggest_categorical('activation', ['tanh', 'relu'])
            lr = trial.suggest_categorical('learning_rate', ['constant', 'adaptive'])


            # disable early_stopping during CV to avoid internal val split
            clf = MLPRegressor(hidden_layer_sizes=hidden,
                               alpha=alpha,
                               batch_size=batch,
                               activation=activation,
                               learning_rate=lr,
                               solver='adam',
                               max_iter=2000,
                               early_stopping=False,
                               random_state=42)

            tscv_local = TimeSeriesSplit(n_splits=3)
            fold_rmses = []
            for tr_idx, val_idx in tscv_local.split(X_train_scaled):
                Xtr, Xval = X_train_scaled[tr_idx], X_train_scaled[val_idx]
                ytr, yval = y_train_scaled[tr_idx], y_train_scaled[val_idx]

                clf.fit(Xtr, ytr)
                pred_scaled = clf.predict(Xval)

                if scaler_y is not None:
                    pred = scaler_y.inverse_transform(pred_scaled)
                    true = scaler_y.inverse_transform(yval)
                else:
                    pred = pred_scaled
                    true = yval

                fold_rmses.append(np.sqrt(mean_squared_error(true, pred)))
            return float(np.mean(fold_rmses))


        # run study with safe try/except and modest trial count
        try:
            study = optuna.create_study(direction='minimize', sampler=optuna.samplers.TPESampler(seed=42))
            study.optimize(objective, n_trials=15, n_jobs=1, show_progress_bar=True) # Change n_trials for desired training epochs


            best = study.best_params
            best_hidden = (best['n1'], best['n2']) if best.get('n2', 0) > 0 else (best['n1'],)
            # early stopping when fitting full train
            best_mlp_model = MLPRegressor(hidden_layer_sizes=best_hidden,
                                          alpha=best['alpha'],
                                          batch_size=best['batch_size'],
                                          activation=best['activation'],
                                          learning_rate=best.get('learning_rate', 'adaptive'),
                                          solver='adam',
                                          max_iter=3000,
                                          early_stopping=True,
                                          n_iter_no_change=30,
                                          random_state=42)


            # fit on full training data
            best_mlp_model.fit(X_train_scaled, y_train_scaled)


            # evaluate and get predictions
            _, _, mlp_best_preds, _ = evaluate_model(best_mlp_model, X_test_scaled, y_test_scaled, scaler_y, states_test_raw, STATE_VARS)


            print("\nOptuna best params:")
            print(best)
            # joblib.dump(best_mlp_model, BEST_MODEL_OUTPUT_PATH)
            # print(f"Saved best MLP model to {BEST_MODEL_OUTPUT_PATH}")


        except Exception as e:
            print("Optuna tuning failed — falling back to baseline MLP. Error:", e)
            best_mlp_model = mlp_model
            mlp_best_preds = mlp_preds




        # --- 3b. Measuring safety boundary violations ---

        actual_yaw_sin = actual_next_states[:, STATE_VARS.index('yaw_sin')]
        actual_yaw_cos = actual_next_states[:, STATE_VARS.index('yaw_cos')]
        actual_yaw = np.degrees(np.arctan2(actual_yaw_sin, actual_yaw_cos))


        predicted_yaw_sin = br_preds[:, STATE_VARS.index('yaw_sin')]
        predicted_yaw_cos = br_preds[:, STATE_VARS.index('yaw_cos')]
        predicted_yaw = np.degrees(np.arctan2(predicted_yaw_sin, predicted_yaw_cos))


        print("\n--- Running Safety Analysis using Best Model ---")


        # analyze safety states
        analyze_violations(
            actual_next_states[:, STATE_VARS.index('pos_up')], 
            mlp_best_preds[:, STATE_VARS.index('pos_up')], 
            'Altitude (m)'
        )
        analyze_violations(
            actual_next_states[:, STATE_VARS.index('OSD.roll')], 
            br_preds[:, STATE_VARS.index('OSD.roll')], 
            'Roll (deg)'
        )
        analyze_violations(
            actual_next_states[:, STATE_VARS.index('OSD.pitch')], 
            br_preds[:, STATE_VARS.index('OSD.pitch')], 
            'Pitch (deg)'
        )
        analyze_violations(
            actual_yaw, 
            predicted_yaw, 
            'Yaw (deg)'
        )


        # Wind Prediction

        N_test = len(actual_next_states) # Number of samples in test set

        # 1. Align all required arrays to the test set indices (split_idx to end)
        actual_wind_speed = df_processed['WEATHER.windSpeed [m/s]'].values[split_idx : split_idx + N_test]
        actual_wind_direction = df_processed['WEATHER.windDirection_deg'].values[split_idx : split_idx + N_test]
        
        # 2. Call the function with perfectly aligned arrays
        est_speed, est_dir, _, _ = estimate_wind_from_residuals(
            actual_next_states, 
            br_preds, # Use the correct predictions array name
            STATE_VARS,
            df_processed, # We only need this for structure/indices now
            split_idx
        )


        return ridge_preds, actual_wind_speed,actual_wind_direction, N_test,  br_preds, rf_preds, lr_preds, mlp_preds, mlp_best_preds, actual_next_states, best_mlp_model, est_speed, est_dir, br_model 



# ------------------------------------------------
# 7: Integrate Into Original Main Script
# ------------------------------------------------



    # ensures X_train_scaled, y_train_scaled, etc. are available
    ridge_preds, br_preds, rf_preds, lr_preds, mlp_preds, mlp_best_preds, actual_next_states, best_mlp_model_instance, est_speed, est_dir, best_br_model = run_benchmarks(
        X_train_scaled, 
        X_test_scaled, 
        y_train_scaled, 
        y_test_scaled, 
        scaler_y, 
        states_test_raw, 
        STATE_VARS
    )


    # re-run prediction step using the `best_model`
    delta_pred_test_scaled = best_br_model.predict(X_test_scaled)

    def estimate_linear_model(df):
        """
        Estimate A,B from data using least squares:
            x_next ≈ A x + B u
        - Accepts df with either f'{s}_next' columns for each state in STATE_VARS,
        or will fall back to using df[STATE_VARS].shift(-1) (dropping last row).
        - Returns A (n_x x n_x), B (n_x x n_u)
        """
        state_cols = list(STATE_VARS)
        input_cols = list(INPUT_VARS)
        next_state_cols = [f"{s}_next" for s in state_cols]


        # choose Y,X_state,U aligned rows
        if all(c in df.columns for c in next_state_cols):
            Y = df[next_state_cols].values
            X_state = df[state_cols].values
            U = df[input_cols].values
        else:
            # fallback to shifted next state
            Y = df[state_cols].shift(-1).dropna().values
            X_state = df[state_cols].values[:Y.shape[0], :]
            U = df[input_cols].values[:Y.shape[0], :]


        if Y.shape[0] < 2:
            raise ValueError("Not enough samples to estimate linear model")

        # build regression matrix Phi = [X_state | U]  (N x (n_x + n_u))
        Phi = np.hstack([X_state, U])  # shape (N, n_phi)
        # Phi @ Theta = Y 
        Theta, *_ = np.linalg.lstsq(Phi, Y, rcond=None)


        n_x = len(state_cols)
        n_phi = Theta.shape[0]
        n_u = n_phi - n_x


        Theta_state = Theta[:n_x, :]   # shape (n_x, n_x)
        Theta_input = Theta[n_x:, :]   # shape (n_u, n_x)


        # A such that x_next = X_state @ A.T  -> A = Theta_state.T
        A = Theta_state.T
        # B such that x_next = U @ B.T -> B = Theta_input.T
        B = Theta_input.T


        return A.astype(float), B.astype(float)


    A_est, B_est = estimate_linear_model(df_processed)


    do_mpc_bundle = {
        'A': A_est.astype(float),
        'B': B_est.astype(float),
        'state_vars': STATE_VARS,
        'input_vars': INPUT_VARS,
        'x0': df_processed[STATE_VARS].iloc[0].values.astype(float),
        'ref_traj': df_processed[[f'{s}_next' for s in STATE_VARS]].values, 
        'u_min': np.array([-1.0, -1.0, 0.0, -1.0]),
        'u_max': np.array([1.0, 1.0, 1.0, 1.0]),
        'dT': df_processed['dT'].mean()
    }
    joblib.dump(do_mpc_bundle, BEST_MODEL_OUTPUT_PATH)
    print(f"Saved do_mpc bundle (A,B...) to {BEST_MODEL_OUTPUT_PATH}")


    # Save the trained MLP model to a separate file (so you don't overwrite the AB bundle)
    # joblib.dump(best_br_model, BEST_MODEL_OUTPUT_PATH)
    # print(f"Saved MLP model to {BEST_MODEL_OUTPUT_PATH}")


    # Wind Setup
    state_to_idx = {name: i for i, name in enumerate(STATE_VARS)}

    def safe_state_index(name):
        """Return index if present, otherwise None."""
        return state_to_idx.get(name, None)


# ------------------------------------------------
# 8. Comparison Plots
# ------------------------------------------------
    try:
        split_idx
    except NameError:
        # fallback: if you used X_train/X_test, compute from X
        split_idx = len(X_train_scaled)  # adapt to your context

    # Extracting indexing
    roll_idx = STATE_VARS.index('OSD.roll')
    pitch_idx = STATE_VARS.index('OSD.pitch')
    yaw_sin_idx = STATE_VARS.index('yaw_sin')
    yaw_cos_idx = STATE_VARS.index('yaw_cos')
    altitude_idx = STATE_VARS.index('pos_up')
    wind_idx = safe_state_index('WEATHER.windSpeed [m/s]')


    # Extracting actual states
    actual_east_full = df_processed['pos_east'].values
    actual_north_full = df_processed['pos_north'].values
    actual_up_full = df_processed['pos_up'].values
    actual_east = actual_next_states[:, STATE_VARS.index('pos_east')]
    actual_north = actual_next_states[:, STATE_VARS.index('pos_north')]
    actual_up = actual_next_states[:, STATE_VARS.index('pos_up')]
    actual_altitude = df_processed['pos_up'].values[split_idx:]
    actual_roll = df_processed['OSD.roll'].values[split_idx:]
    actual_pitch = df_processed['OSD.pitch'].values[split_idx:]
    actual_yaw_sin = df_processed['yaw_sin'].values[split_idx:]
    actual_yaw_cos = df_processed['yaw_cos'].values[split_idx:]
    actual_yaw = np.degrees(np.arctan2(actual_yaw_sin, actual_yaw_cos))
    actual_wind_speed = df_processed['WEATHER.windSpeed [m/s]'].values[split_idx:]
    actual_wind_direction = df_processed['WEATHER.windDirection_deg'].values[split_idx:]


    # Extracting predicted states
    predicted_altitude = states_next_pred[:, altitude_idx]
    predicted_roll = states_next_pred[:, roll_idx]
    predicted_pitch = states_next_pred[:, pitch_idx]
    predicted_yaw_sin = states_next_pred[:, yaw_sin_idx]
    predicted_yaw_cos = states_next_pred[:, yaw_cos_idx]
    predicted_yaw = np.degrees(np.arctan2(predicted_yaw_sin, predicted_yaw_cos))


    # Model-predicted next state using learned f(x,u)
    x_model_next = states_next_pred
    x_true_next = actual_next_states
    residual = x_true_next - x_model_next

    # Calculate absolute errors over the test dataset time points
    error_altitude = predicted_altitude - actual_altitude
    error_roll = predicted_roll - actual_roll
    error_pitch = predicted_pitch - actual_pitch
    error_yaw = predicted_yaw - actual_yaw
    error_yaw = (error_yaw + 180) % 360 - 180 


    assert predicted_altitude.shape == actual_altitude.shape        


    # Plot flight time
    time_points = df_processed['OSD.flyTime [s]'].values[split_idx : split_idx + N_test] # Align time axis precisely    

    # RMSE for each model
    rmse_mlp = np.sqrt(mean_squared_error(actual_next_states, mlp_preds))
    rmse_ridge = np.sqrt(mean_squared_error(actual_next_states, ridge_preds))
    rmse_br = np.sqrt(mean_squared_error(actual_next_states, br_preds))
    rmse_rf = np.sqrt(mean_squared_error(actual_next_states, rf_preds))
    rmse_lr = np.sqrt(mean_squared_error(actual_next_states, lr_preds))
    rmse_bmlp = np.sqrt(mean_squared_error(actual_next_states, mlp_best_preds))
    rmse_speed = np.sqrt(mean_squared_error(actual_wind_speed, est_speed))
    dir_error = actual_wind_direction - est_dir
    dir_error = (dir_error + 180) % 360 - 180
    rmse_direction = np.sqrt(mean_squared_error(np.zeros_like(dir_error), dir_error))

    print("\n--- Wind Estimation RMSE ---")
    print(f"Wind Speed RMSE: {rmse_speed:.4f} m/s")
    print(f"Wind Direction RMSE: {rmse_direction:.4f} m/s")


    # check to ensure matching
    print("shapes:", actual_next_states.shape, mlp_preds.shape)

    # --- Starting plots ---
    print("\nGenerating 3D visualization...")


    # --- Comparison Plot Setup ---
    def plot_state_comparison(actual_data, ridge_data, br_data, rf_data, mlp_data, best_mlp_data, unit_label):
        plt.figure(figsize=(12, 6))
        plt.plot(time_points, actual_data, label='True Flight Data', color='red', linestyle='--', alpha=0.8)
        plt.plot(time_points, ridge_data, label='Ridge Prediction', color='green', alpha=0.7)
        plt.plot(time_points, br_data, label='BayesianRidge Prediction', color='purple', alpha=0.7)
        plt.plot(time_points, rf_data, label='Random Forest Prediction', color='orange', alpha=0.7)
        plt.plot(time_points, mlp_data, label='MLP Prediction', color='blue', alpha=0.7)
        plt.plot(time_points, best_mlp_data, label='MLP Prediction', color='blue', alpha=0.7)
        plt.xlabel('Time (s)', fontsize=12)
        plt.ylabel(unit_label, fontsize=12)
        plt.legend(loc='upper right', fontsize=11)
        plt.grid(True)
        plt.tight_layout()
        plt.show()




    # --- 8A: Best Flight Path Comparison ---
    fig = plt.figure(figsize=(10, 7))
    ax = fig.add_subplot(111, projection='3d')


    ax.plot(actual_east_full, actual_north_full, actual_up_full, label='True Flight Path', color='red', linewidth=4, alpha=0.6)
    ax.plot(br_preds[:, STATE_VARS.index('pos_east')], br_preds[:, STATE_VARS.index('pos_north')], br_preds[:, STATE_VARS.index('pos_up')], label=f'Best MLP Path - RMSE: {rmse_br:.4f}', color='black', linewidth=2)
    ax.set_xlabel('East Position (m)', fontsize=12)
    ax.set_ylabel('North Position (m)', fontsize=12)
    ax.set_zlabel('Altitude (m)', fontsize=12)
    ax.legend(loc='best', fontsize=11)
    ax.grid(True)
    plt.savefig('Outputs/8A_3d_mlp_flight_path.pdf', dpi=600, bbox_inches='tight')
    plt.show()




    # --- 8B: 3D All Flight Path Comparison ---
    fig = plt.figure(figsize=(10, 7))
    ax = fig.add_subplot(111, projection='3d')


    ax.plot(actual_east_full, actual_north_full, actual_up_full, label='True Full Flight Path', color='brown', linewidth=4, alpha=0.6)
    ax.plot(ridge_preds[:, STATE_VARS.index('pos_east')], ridge_preds[:, STATE_VARS.index('pos_north')], ridge_preds[:, STATE_VARS.index('pos_up')], label=f'Ridge Predicted Path - RMSE: {rmse_ridge:.4f}', color='green', linewidth=1)
    ax.plot(br_preds[:, STATE_VARS.index('pos_east')], br_preds[:, STATE_VARS.index('pos_north')], br_preds[:, STATE_VARS.index('pos_up')], label=f'BayesianRidge Predicted Path - RMSE: {rmse_br:.4f}', color='pink', linewidth=1)
    ax.plot(rf_preds[:, STATE_VARS.index('pos_east')], rf_preds[:, STATE_VARS.index('pos_north')], rf_preds[:, STATE_VARS.index('pos_up')], label=f'Random Forest Predicted Path - RMSE: {rmse_rf:.4f}', color='orange', linewidth=1)
    ax.plot(lr_preds[:, STATE_VARS.index('pos_east')], lr_preds[:, STATE_VARS.index('pos_north')], lr_preds[:, STATE_VARS.index('pos_up')], label=f'Linear Regression Predicted Path - RMSE: {rmse_lr:.4f}', color='cyan', linewidth=1)
    ax.plot(mlp_preds[:, STATE_VARS.index('pos_east')], mlp_preds[:, STATE_VARS.index('pos_north')], mlp_preds[:, STATE_VARS.index('pos_up')], label=f'MLP Predicted Path - RMSE: {rmse_mlp:.4f}', color='blue', linewidth=1)
    ax.plot(mlp_best_preds[:, STATE_VARS.index('pos_east')], mlp_best_preds[:, STATE_VARS.index('pos_north')], mlp_best_preds[:, STATE_VARS.index('pos_up')], label=f'Best MLP Path - RMSE: {rmse_bmlp:.4f}', color='black', linewidth=1)
    ax.set_xlabel('East Position (m)', fontsize=12)
    ax.set_ylabel('North Position (m)', fontsize=12)
    ax.set_zlabel('Altitude (m)', fontsize=12)
    ax.legend(loc='best', fontsize=9)
    ax.grid(True)
    plt.savefig('Outputs/8B_3d_all_models_flight_path.pdf', dpi=600, bbox_inches='tight')
    plt.show()




    # --- 8C. Altitude, Roll, Pitch and Yaw Angle Comparison over time ---
    fig, (ax_alt, ax_roll, ax_pitch, ax_yaw) = plt.subplots(4, 1, figsize=(10, 7), sharex=True)


    # Plot Altitude
    ax_alt.plot(time_points, actual_altitude, label='Actual Altitude ', color='red', alpha=1)
    ax_alt.plot(time_points, predicted_altitude, label='Best Model Altitude', color='blue')
    ax_alt.set_title('Altitude Height Tracking', fontsize=12)
    ax_alt.set_ylabel('Altitude (m)', fontsize=12)
    ax_alt.legend(loc='best', fontsize=11)
    ax_alt.grid(True)


    # Plot Roll
    ax_roll.plot(time_points, actual_roll, label='Actual Roll ', color='red', alpha=1)
    ax_roll.plot(time_points, predicted_roll, label='Best Model Roll', color='blue')
    ax_roll.set_title('Roll Angle Tracking', fontsize=12)
    ax_roll.set_ylabel('Roll (degrees)', fontsize=12)
    ax_roll.legend(loc='upper right', fontsize=11)
    ax_roll.grid(True)


    # Plot Pitch
    ax_pitch.plot(time_points, actual_pitch, label='Actual Pitch', color='red', alpha=1)
    ax_pitch.plot(time_points, predicted_pitch, label='Best Model Pitch', color='blue')
    ax_pitch.set_title('Pitch Angle Tracking', fontsize=12)
    ax_pitch.set_ylabel('Pitch (degrees)', fontsize=12)
    ax_pitch.legend(loc='upper right', fontsize=11)
    ax_pitch.grid(True)


    # Plot Yaw
    ax_yaw.plot(time_points, actual_yaw, label='Actual Yaw', color='red', alpha=1)
    ax_yaw.plot(time_points, predicted_yaw, label='Best Model Pitch', color='blue')
    ax_yaw.set_title('Yaw Angle Tracking', fontsize=12)
    ax_yaw.set_xlabel('Time (s)', fontsize=12)
    ax_yaw.set_ylabel('Yaw (degrees)', fontsize=12)
    ax_yaw.legend(loc='best', fontsize=11)
    ax_yaw.grid(True)
    plt.tight_layout(pad=3.0)
    plt.savefig('Outputs/8C_pitch_roll_yaw_tracking.pdf', dpi=600, bbox_inches='tight')
    plt.show()




    # --- 8D. Plotting (RMSE) Error Over Time ---

    fig_errors, (ax_alt_err, ax_roll_err, ax_pitch_err, ax_yaw_err) = plt.subplots(4, 1, figsize=(10, 7), sharex=True)
    plt.title('Prediction Errors Over Time Using Best Model Model')


    # Plot Altitude Error
    ax_alt_err.plot(time_points, error_altitude, label='Altitude Prediction Error', color='orange')
    rmse_alt = np.sqrt(mean_squared_error(actual_altitude, predicted_altitude))
    ax_alt_err.axhline(y=0, color='gray', linestyle='-')
    ax_alt_err.axhline(y=rmse_alt, color='black', linestyle='--', label=f'RMSE: {rmse_alt:.4f} (m)')
    ax_alt_err.axhline(y=-rmse_alt, color='black', linestyle='--')
    ax_alt_err.set_title('Altitude Prediction Error', fontsize=12)
    ax_alt_err.set_ylabel('Error (m)', fontsize=12)
    ax_alt_err.legend(loc='upper right', fontsize=11)
    ax_alt_err.grid(True)


    # Plot Roll Error
    ax_roll_err.plot(time_points, error_roll, label='Roll Prediction Error', color='purple')
    rmse_roll = np.sqrt(mean_squared_error(actual_roll, predicted_roll))
    ax_roll_err.axhline(y=0, color='gray', linestyle='-')
    ax_roll_err.axhline(y=rmse_roll, color='black', linestyle='--', label=f'RMSE: {rmse_roll:.4f} deg')
    ax_roll_err.axhline(y=-rmse_roll, color='black', linestyle='--')
    ax_roll_err.set_title('Roll Prediction Error', fontsize=12)
    ax_roll_err.set_ylabel('Error (degrees)', fontsize=12)
    ax_roll_err.legend(loc='best', fontsize=11)
    ax_roll_err.grid(True)


    # Plot Pitch Error
    ax_pitch_err.plot(time_points, error_pitch, label='Pitch Prediction Error', color='green')
    rmse_pitch = np.sqrt(mean_squared_error(actual_pitch, predicted_pitch))
    ax_pitch_err.axhline(y=0, color='gray', linestyle='-')
    ax_pitch_err.axhline(y=rmse_pitch, color='black', linestyle='--', label=f'RMSE: {rmse_pitch:.4f} deg')
    ax_pitch_err.axhline(y=-rmse_pitch, color='black', linestyle='--')
    ax_pitch_err.set_title('Pitch Prediction Error)', fontsize=12)
    ax_pitch_err.set_ylabel('Error (degrees)', fontsize=12)
    ax_pitch_err.legend(loc='best', fontsize=11)
    ax_pitch_err.grid(True)


    # Plot Yaw Error
    ax_yaw_err.plot(time_points, error_yaw, label='Yaw Prediction Error', color='orange')
    rmse_yaw = np.sqrt(mean_squared_error(np.zeros_like(error_yaw), error_yaw))
    ax_yaw_err.axhline(y=0, color='gray', linestyle='-')
    ax_yaw_err.axhline(y=rmse_yaw, color='black', linestyle='--', label=f'RMSE: {rmse_yaw:.4f} deg')
    ax_yaw_err.axhline(y=-rmse_yaw, color='black', linestyle='--')
    ax_yaw_err.set_title('Yaw Prediction Error', fontsize=12)
    ax_yaw_err.set_xlabel('Time (s)', fontsize=12)
    ax_yaw_err.set_ylabel('Error (degrees)', fontsize=12)
    ax_yaw_err.legend(loc='best', fontsize=11)
    ax_yaw_err.grid(True)
    plt.tight_layout(pad=3.0)
    plt.savefig('Outputs/8D_prediction_errors_over_time.pdf', dpi=600, bbox_inches='tight')
    plt.show()




    # --- 8E. Plotting with Uncertainty Bands ---
    def plot_states_2x2(time_points,
                        actual_next_states,
                        ridge_preds,
                        br_preds,
                        rf_preds,
                        mlp_best_preds,
                        state_info,
                        ):
        
        fig_unc, axes_unc = plt.subplots(2, 2, figsize=(10, 7), sharex=True)
        axes_unc = axes_unc.flatten()


        model_preds = {
            'Ridge': ridge_preds,
            'BayesianRidge': br_preds,
            'Random Forest': rf_preds,
            'MLP+Optuna': mlp_best_preds
        }


        for i, (title, idx, unit) in enumerate(state_info):
            ax = axes_unc[i] # Use 'ax' as local variable
            if title == 'Yaw Angle':    
                actual_sin = actual_next_states[:, STATE_VARS.index('yaw_sin')]
                actual_cos = actual_next_states[:, STATE_VARS.index('yaw_cos')]
                actual_data = np.degrees(np.arctan2(actual_sin, actual_cos))
                

                for model_name, preds in model_preds.items():
                    pred_sin = preds[:, STATE_VARS.index('yaw_sin')]
                    pred_cos = preds[:, STATE_VARS.index('yaw_cos')]
                    pred_data = np.degrees(np.arctan2(pred_sin, pred_cos))
                    ax.plot(time_points, pred_data, label=f'{model_name} Pred', linestyle='--')
                

                else:
                    # For all other states (roll, pitch, alt, pos, vel)
                    actual_data = actual_next_states[:, idx]
                    ax.plot(time_points, actual_data, label='True Flight Data', color='red', linewidth=3, alpha=0.7)
                    
                    for model_name, preds in model_preds.items():
                        ax.plot(time_points, preds[:, idx], label=f'{model_name} Pred', linestyle='--')

            ax.set_ylabel(unit, fontsize=14)
            ax.grid(True)
            ax.legend(loc='best', fontsize=10)


        # Check if we have 4 plots in total (indices 2 and 3)
        if len(axes_unc) == 4:
            axes_unc[2].set_xlabel('Time (s)', fontsize=14)
            axes_unc[3].set_xlabel('Time (s)', fontsize=14)
        elif len(axes_unc) > 0: # Or set on the last plot if fewer than 4
                axes_unc[-1].set_xlabel('Time (s)', fontsize=14)


        plt.tight_layout(pad=3.0)
        plt.savefig('Outputs/8E_uncertainty_bands.pdf', dpi=600, bbox_inches='tight')
        plt.show()




    # --- 8F. Plotting Control Inputs (Rudder, Elevator, Thrust, Aileron) ---

    print("\nGenerating plots for control inputs...")
    

    # Get indices for control inputs
    aileron_idx = INPUT_VARS.index('RC.aileron')
    elevator_idx = INPUT_VARS.index('RC.elevator')
    throttle_idx = INPUT_VARS.index('RC.throttle')
    rudder_idx = INPUT_VARS.index('RC.rudder')


    # Use the full X dataset from the beginning to get all input commands
    full_time_points = df_processed['OSD.flyTime [s]'].values
    full_inputs = df_processed[INPUT_VARS].values


    fig_inputs, axes_inputs = plt.subplots(2, 2, figsize=(12, 10), sharex=True)
    axes_inputs = axes_inputs.flatten()


    # Plot Aileron
    axes_inputs[0].plot(full_time_points, full_inputs[:, aileron_idx], label='RC.aileron Command', color='blue')
    axes_inputs[0].set_title('Aileron Input')
    axes_inputs[0].set_ylabel('Command Value (Normalized)')
    axes_inputs[0].grid(True)


    # Plot Elevator
    axes_inputs[1].plot(full_time_points, full_inputs[:, elevator_idx], label='RC.elevator Command', color='green')
    axes_inputs[1].set_title('Elevator Input')
    axes_inputs[1].set_ylabel('Command Value (Normalized)')
    axes_inputs[1].grid(True)


    # Plot Throttle
    axes_inputs[2].plot(full_time_points, full_inputs[:, throttle_idx], label='RC.throttle Command', color='red')
    axes_inputs[2].set_title('Throttle Input')
    axes_inputs[2].set_xlabel('Time (s)')
    axes_inputs[2].set_ylabel('Command Value (Normalized 0-1)')
    axes_inputs[2].grid(True)


    # Plot Rudder
    axes_inputs[3].plot(full_time_points, full_inputs[:, rudder_idx], label='RC.rudder Command', color='purple')
    axes_inputs[3].set_title('Rudder Input')
    axes_inputs[3].set_xlabel('Time (s)')
    axes_inputs[3].set_ylabel('Command Value (Normalized)')
    axes_inputs[3].grid(True)


    plt.tight_layout(pad=3.0)
    plt.savefig('Outputs/8F_control_inputs_over_time.pdf', dpi=600, bbox_inches='tight')
    plt.show()


    ax_yaw_err.axhline(y=rmse_yaw, color='black', linestyle='--', label=f'RMSE: {rmse_yaw:.4f} deg')


    time_points = df_processed['OSD.flyTime [s]'].values[split_idx : split_idx + N_test] # Align time axis precisely


    # Wind Plots


    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    ax1.plot(time_points, actual_wind_speed, label='Actual Measured Wind Speed', color='red', linewidth=2)
    ax1.plot(time_points, est_speed, label='Estimated Wind Speed', color='blue', linestyle='--')
    ax1.axhline(y=rmse_speed, color='black', linestyle='--', label=f'RMSE: {rmse_speed:.4f} m/s')
    ax1.set_title('Wind Speed: Actual vs. Estimated')
    ax1.set_ylabel('Speed (m/s)')
    ax1.legend()
    ax1.grid(True)

    ax2.plot(time_points, actual_wind_direction, label='Actual Measured Direction', color='red', linewidth=2)
    ax2.plot(time_points, est_dir, label='Estimated Direction (Model Residuals)', color='blue', linestyle='--')
    # Add horizontal line for the RMSE value
    ax2.axhline(y=rmse_direction, color='black', linestyle='--', label=f'RMSE: {rmse_direction:.4f} deg')
    ax2.set_title('Wind Direction: Actual vs. Estimated')
    ax2.set_xlabel('Time (s)')
    ax2.set_ylabel('Direction (Degrees)')
    ax2.set_ylim(0, 360)
    ax2.legend()
    ax2.grid(True)

    plt.tight_layout()
    plt.savefig('Outputs/8G_wind_estimation_comparison.pdf', dpi=600, bbox_inches='tight')
    plt.show()