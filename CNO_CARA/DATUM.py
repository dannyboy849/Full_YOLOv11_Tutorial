"""
DATUM.py - v1.1
───────────────
the whole hub placement project; good luck!

the training sequence goes in the order:
-----------
1.  config           load & merges all YAMLs
2.  vehicle select   prompts user or read cfg.vehicle_type to set input_vars
3.  validate raw     setup and quality report
4.  prepare          feature setup, delta targets
5.  split and scale  chronological split, fit StandardScalers
6.  benchmark        Ridge, BayesianRidge, RandomForest, Linear, MLP
7.  Optuna           MLP hyperparameter search
8.  GRU              sequence model (cfg.train_gru: true in base.yaml)
9.  evaluate         per-state metrics on test set
10. MPC bundle       estimate A, B; save do-mpc pkl
11. plot             all figures (15A–15H)
12. saves artifacts  models, scalers, metrics.json
"""

import io, os, sys, warnings
import time
import numpy                    as np
import pandas                   as pd
import networkx                 as nx


from plot                       import run_plots, run_plotly_dashboard
from train                      import build_linear, build_mlp_optuna
from types                      import SimpleNamespace
from prepare                    import prepare_mpc_data
from pathlib                    import Path
from evaluate                   import (evaluate_model, time_series_cv_score,
                                    compute_permutation_importance)
from utils.io                   import load_csv, save_config, save_model, save_metrics
from validation                 import check_no_leakage, normalized_rmse_report
from utils.config               import load_config
from utils.splits               import time_series_split
from utils.vehicle              import select_vehicle, apply_vehicle_to_cfg, AERO_PARAMS
from control.mpc_train          import run_mpc_train
from sklearn.multioutput        import MultiOutputRegressor
from sklearn.preprocessing      import StandardScaler
from evaluation.comparison      import run_mpc_comparison
from sklearn.neural_network     import MLPRegressor
from planning.hub_optimizer     import HubOptimizer
from planning.weather_engine    import PhysicsInformedWeatherEngine
from environment.environment    import Environment


# requirements for DATUM
sys.path.insert(0, str(Path(__file__).parent / "src"))
assert sys.version_info >= (3, 12), "This script requires Python 3.12+"



# --------------------------------------------------
# ── helpers ───────────────────────────────────────
# --------------------------------------------------

def _compute_sigma_bounds(linear_model, scaler_X, scaler_y,
                          X_te_s, y_te_s, states_test_raw, output_vars):
    """compute per-state 2-sigma residual bounds on test set."""
    _, y_pred, y_actual = evaluate_model(
        linear_model, X_te_s, y_te_s, scaler_y, states_test_raw, output_vars
    )
    residuals = y_pred - y_actual        # (N, n_states)
    sigma = np.std(residuals, axis=0)    # (n_states,)
    
    print("[pipeline] Per-state residual 2σ bounds:")
    for name, s in zip(output_vars, sigma):
        print(f"  {name:<25} 2σ = {2*s:.4f}")
    return 2.0 * sigma

 
def correlation_report(df, features):

    corr = df[features].corr().abs()
    high_corr = np.where((corr > 0.95) & (corr < 1.0))

    print("\n[features] Highly correlated pairs (>0.95):")
    for i, j in zip(*high_corr):
        print(f"{features[i]} <-> {features[j]} : {corr.iloc[i, j]:.3f}")


def temporal_error_profile(y_true, y_pred):
    err = np.sqrt((y_true - y_pred)**2).mean(axis=1)

    print("\n[analysis] Temporal error snapshot:")
    print(f"  first 10 mean errors: {err[:10]}")
    print(f"  last  10 mean errors: {err[-10:]}")


def _apply_motor_limits(cfg, vehicle_type: str):
    """
    automatically set cfg.mpc.u_min / u_max from vehicle profile.
    values in mpc.yaml are used only if vehicle_type == 'custom'.
    """
 
    MOTOR_LIMITS = {
        # vehicle_type: PWM (u_min, u_max)
        "quadcopter": (
            [1000, 1000, 1000, 1000],
            [2000, 2000, 2000, 2000],
        ),
        "vtol": (
            [1000, 1000, 1000, 1000, 1000],
            [2000, 2000, 2000, 2000, 2000],
        ),
        "hexacopter": (
            [1000, 1000, 1000, 1000, 1000, 1000],
            [2000, 2000, 2000, 2000, 2000, 2000],
        )
    }

    if vehicle_type in MOTOR_LIMITS:
        u_min, u_max = MOTOR_LIMITS[vehicle_type]
        n = len(cfg.input_vars)
        u_min = (u_min + [1000] * n)[:n]
        u_max = (u_max + [2000] * n)[:n]

        cfg.mpc = SimpleNamespace(
            **{k: v for k, v in vars(cfg.mpc).items()
               if k not in ("u_min", "u_max")},
            u_min=u_min,
            u_max=u_max,
        )

        print(f"[pipeline] Motor limits auto-set for {vehicle_type} "
              f"({n} channels).")
        
    else:
        print(f"[pipeline] Using mpc.yaml motor limits for '{vehicle_type}'.")

    return cfg


def _add_vtol_mode_feature(df, features: list) -> None:

    """
    added a binary hover/fixed-wing mode flag based on airspeed;
    otherwise, it uses altitude rate as a substitute, which is less accurate, but still helpful.
    """

    if "airspeed" in df.columns:
        df["airspeed_norm"] = df["airspeed"] / df["airspeed"].max()

    elif "bar_cr" in df.columns:
        df["flight_mode"] = (df["bar_cr"].abs() < 1.0).astype(float)

    else:
        df["flight_mode"] = 0.0

    if "flight_mode" not in features:
        features.append("flight_mode")

    print("[pipeline] VTOL: added 'flight_mode' transition feature.")


def select_best_model(all_results: dict):
    """
    select best model based on aggregate metric.
    assumes structure:
    all_results[name]["overall"][metric]
    """
    best_name = None
    best_score = float("inf")

    for name, res in all_results.items():
        overall = res.get("overall", {})

        if not isinstance(overall, dict):
            raise ValueError(f"[selection] Unexpected format for '{name}': {overall}")

        # normalize key access
        keys = {k.lower(): k for k in overall.keys()}

        if "rmse" in keys:
            score = overall[keys["rmse"]]

        elif "mse" in keys:
            score = overall[keys["mse"]] ** 0.5

        else:
            raise ValueError(
                f"[selection] No rmse/mse found for '{name}'. Keys: {list(overall.keys())}"
            )

        if score < best_score:
            best_score = score
            best_name = name

    print(f"[selection] Best model: {best_name} (rmse={best_score:.5f})")
    return best_name


def main():
    
    # --------------------------------------------------
    # ── 1. config ─────────────────────────────────────
    # --------------------------------------------------

    cfg = load_config("base", "dataset", "model", "mpc")
    warnings.filterwarnings(cfg.warnings_filter, category=UserWarning)
    for p in [cfg.paths.models, cfg.paths.logs,
              cfg.paths.plots,  cfg.paths.checkpoints]:
        os.makedirs(p, exist_ok=True)
    print(f"{cfg.device =}")



    # --------------------------------------------------
    # ── 2. UAS selection ──────────────────────────────
    # --------------------------------------------------

    vehicle_type = select_vehicle(cfg)
    cfg = apply_vehicle_to_cfg(cfg, vehicle_type)

    # optimization mode prompt block
    print("\n" + "="*50)
    print(" [hub prompt] Hub Optimization Framework Mode")
    print("="*50)
    print("  1 = dispersed  (Spatially spread multi-hub allocation)")
    print("  2 = continuous (Continuous coordinate solver)")
    mode_map = {"1": "dispersed", "2": "continuous"}
    
    while True:
        mode_choice = input("Choose engine target mode (1 or 2) [Default=1]: ").strip()
        if not mode_choice:
            cfg.active_strategic_mode = "dispersed"
            break
        if mode_choice in mode_map:
            cfg.active_strategic_mode = mode_map[mode_choice]
            break
        print("[!] Selection out of bounds. Enter 1 or 2.")

    # target hubs volume capacity count prompt block
    print("\n" + "="*50)
    print(" [hub prompt] Target Distribution Infrastructure Capacity")
    print("="*50)
    while True:
        try:
            user_hubs_count = input("Enter target volume capacity allocation hub node count [Default=7]: ").strip()
            if not user_hubs_count:
                cfg.target_hubs_count = 7
                break
            h_count = int(user_hubs_count)
            if 1 <= h_count <= 49:
                cfg.target_hubs_count = h_count
                break
            print("[!] Range exception. Choose an count between 1 and 49.")
        except ValueError:
            print("[!] Numeric integer input required.")

    print(f"\n[LOCK] Strategy parameters saved: Mode={cfg.active_strategic_mode.upper()} | Count={cfg.target_hubs_count}")
    print("="*50 + "\n")

    # validates u_min/u_max length matches n_motors
    n_motors = cfg.vehicle_profile.n_motors
    n_inputs = len(cfg.input_vars)
    u_min = cfg.mpc.u_min
    u_max = cfg.mpc.u_max
    if len(u_min) != n_inputs:
        raise ValueError(
            f"mpc.yaml u_min has {len(u_min,u_max)} entries but vehicle has "
            f"{n_inputs} input channels. Update configs/mpc.yaml."
            # f"the selected vehicle, {select_vehicle}, has {n_motors}."
        )



    # --------------------------------------------------
    # ── 3. load & validate ────────────────────────────
    # --------------------------------------------------

    train_path = Path(cfg.paths.data_processed) / cfg.dataset.train_file
    df_raw     = load_csv(train_path)



    # --------------------------------------------------
    # ── 4. prepare ────────────────────────────────────
    # --------------------------------------------------

    df, features, output_vars, target_deltas = prepare_mpc_data(df_raw, cfg)
    check_no_leakage(features)

    # for VTOLs only: adds flight-mode feature (hover vs fixed-wing)
    if vehicle_type == "vtol" and cfg.vehicle_profile.has_transition:
        _add_vtol_mode_feature(df, features)



    # --------------------------------------------------
    # ── 5. split and scale ────────────────────────────
    # --------------------------------------------------

    X          = df[features].values.astype(float)
    y          = df[target_deltas].values.astype(float)
    states_raw = df[output_vars].values.astype(float)

    X_train, X_test, y_train, y_test = time_series_split(
        X, y, cfg.dataset.test_split
    )
    states_test_raw = states_raw[len(X_train):]

    scaler_X = StandardScaler().fit(X_train)
    scaler_y = StandardScaler().fit(y_train)
    save_model(features, Path(cfg.paths.models) / "feature_list.pkl")
    print(f"\n[pipeline] Saved feature list ({len(features)} features)")

    X_tr_s = scaler_X.transform(X_train)
    X_te_s = scaler_X.transform(X_test)
    y_tr_s = scaler_y.transform(y_train)
    y_te_s = scaler_y.transform(y_test)



    # --------------------------------------------------
    # ── 6. linear model  ──────────────────────────────
    # --------------------------------------------------

    print("\n" + "="*60)
    all_preds    = {}

    print("\n── Linear ──")
    linear_model = build_linear()
    linear_model.fit(X_tr_s, y_tr_s)

    # single evaluation call
    res_linear, preds_linear, actual_linear = evaluate_model(
        linear_model, X_te_s, y_te_s, scaler_y, states_test_raw, output_vars
    )
    all_preds["Linear"] = preds_linear

    _saved = sys.stdout
    sys.stdout = io.StringIO()
    sigma_bounds = _compute_sigma_bounds(
        linear_model, scaler_X, scaler_y,
        X_te_s, y_te_s, states_test_raw, output_vars
    )
    sys.stdout = _saved

    # normalised RMSE report
    normalized_rmse_report(actual_linear, preds_linear, output_vars)

    cv_score = time_series_cv_score(linear_model, X_tr_s, y_tr_s, scaler_y)
    print(f"[CV] Linear rmse: {cv_score:.5f}")
    print(f"output_vars: {len(output_vars)}")

    save_model(linear_model, Path(cfg.paths.models) / "linear_model.pkl")

    linear_rmse = np.sqrt(np.mean(
        (y_te_s - linear_model.predict(X_te_s))**2
    ))



    # --------------------------------------------------
    # ── 7. residual MLP (gating correction) ──────────
    # --------------------------------------------------

    print("\n── MLP residual (gating) ──")

    linear_pred_train     = linear_model.predict(X_tr_s)
    residual_targets_full = y_tr_s - linear_pred_train         # (N_tr, n_states)

    # per-state gate using NORMALISED RMSE (rmse / σ)
    # σ per state in scaled space = std of training targets
    linear_pred_test_s  = linear_model.predict(X_te_s)
    linear_pred_raw     = scaler_y.inverse_transform(linear_pred_test_s)
    actual_raw          = scaler_y.inverse_transform(y_te_s)
    per_state_rmse_raw  = np.sqrt(
        np.mean((actual_raw - linear_pred_raw)**2, axis=0)
    )
    sigma_raw  = states_test_raw.std(axis=0)
    sigma_raw  = np.where(sigma_raw > 1e-8, sigma_raw, 1.0)
    norm_rmse  = per_state_rmse_raw / sigma_raw                  # (n_states,)

    well_fit_tol   = float(getattr(cfg.model, 'residual_gate_tol',   0.15))
    struggling_tol = float(getattr(cfg.model, 'residual_active_tol', 0.25))

    well_fit_mask   = norm_rmse < well_fit_tol
    struggling_mask = norm_rmse >= struggling_tol

    print(f"\n[gate] Per-state normalised RMSE (rmse/σ, physical units):")
    for vname, nrmse, wf in zip(output_vars, norm_rmse, well_fit_mask):
        tag = "ZEROED (well-fit)" if wf else "ACTIVE"
        print(f"  {vname:<22} {nrmse:.4f}  {tag}")

    n_well       = int(well_fit_mask.sum())
    n_struggling = int(struggling_mask.sum())

    print(f"\n[gate] Well-fit zeroed : {n_well}   "
          f"→ {[v for v,m in zip(output_vars, well_fit_mask) if m]}")
    
    print(f"[gate] Struggling active: {n_struggling} "
          f"→ {[v for v,m in zip(output_vars, struggling_mask) if m]}")

    # column gate: zero well-fit channels in training residuals
    residual_targets = residual_targets_full.copy()
    residual_targets[:, well_fit_mask] = 0.0

    # row gate: drop near-zero-residual (steady-state) samples
    active_cols  = ~well_fit_mask
    if active_cols.any():
        row_norm = np.linalg.norm(residual_targets_full[:, active_cols], axis=1)
    else:
        row_norm = np.linalg.norm(residual_targets_full, axis=1)

    # threshold at a percentile of the row norm distribution.
    row_pct      = float(getattr(cfg.model, 'residual_row_percentile', 40.0))
    row_tol      = float(np.percentile(row_norm, row_pct))

    active_rows  = row_norm >= row_tol
    n_active     = int(active_rows.sum())
    n_total      = len(active_rows)
    print(f"[gate] Row threshold (p{row_pct:.0f}): {row_tol:.5f}  "
          f"Active rows: {n_active:,}/{n_total:,} ({100*n_active/n_total:.1f}%)")

    residual_targets[~active_rows] = 0.0
    print(f"[Residual targets] shape: {residual_targets.shape}   "
          f"non-zero rows: {n_active:,}")

    _debug_ans = input(
        "\n[pipeline] Run in DEBUG mode? (faster, but undertrained)\n"
        "  1 = full Optuna (~15-20 min) || 2 = debug: "
    ).strip().lower()
    DEBUG_FAST_RUN = (_debug_ans == '2')

    if DEBUG_FAST_RUN:
        print("[DEBUG] Bypassing Optuna — fast single-run test model")
        base_mlp = MLPRegressor(
            hidden_layer_sizes  = (64, 64, 16),
            alpha               = 0.0072,
            batch_size          = 64,
            activation          = 'relu',
            max_iter            = 200,     
            early_stopping      = True,
            n_iter_no_change    = 10,
            random_state        = int(cfg.seed),
        )
        # single core fallback for rapid debugging
        mlp_model = MultiOutputRegressor(base_mlp, n_jobs=1)
        mlp_model.fit(X_tr_s, residual_targets)
    else:
        print("\n[pipeline] Optuna HPO search across active nodes...")
        mlp_model     = build_mlp_optuna(
            X_train   = X_tr_s, 
            y_train   = residual_targets, 
            scaler_y  = scaler_y, 
            cfg       = cfg,
            seed      = int(cfg.seed)
        )
    save_model(mlp_model, Path(cfg.paths.models) / "residual_model.pkl")
    print("[pipeline] Residual MLP training completed and artifact cached safely.")

    # evaluate combined model
    residual_pred   = mlp_model.predict(X_te_s)
    combined_pred   = linear_pred_test_s + residual_pred

    residual_rmse   = np.sqrt(np.mean((y_te_s - combined_pred)**2))
    improvement     = 100.0 * (linear_rmse - residual_rmse) / linear_rmse
    print(f"[Residual Gain] linear={linear_rmse:.5f}  "
          f"combined={residual_rmse:.5f}  gain={improvement:.2f}%")

    preds_mlp       = scaler_y.inverse_transform(combined_pred)
    actual_mlp      = scaler_y.inverse_transform(y_te_s)
    all_preds["MLP+Residual"] = preds_mlp



    # --------------------------------------------------
    # ── 8. benchmark sklearn models ───────────────────
    # --------------------------------------------------
    # removed for now


    # --------------------------------------------------
    # ── 9. MPC bundle ─────────────────────────────────
    # --------------------------------------------------

    mpc_bundle = run_mpc_train(df, output_vars, cfg.input_vars, cfg)



    # --------------------------------------------------
    # ── 10. save artifacts ────────────────────────────
    # --------------------------------------------------

    if linear_model is not None:
        compute_permutation_importance(linear_model, X_te_s, y_te_s, features)

    save_config(cfg, Path(cfg.paths.logs) / "config_snapshot.json")
    save_model(scaler_X, cfg.paths.feature_scaler)
    save_model(scaler_y, cfg.paths.target_scaler)
    save_model(mlp_model, cfg.paths.best_mlp_model)
    save_model(linear_model, Path(cfg.paths.models) / "linear_model.pkl")
    save_metrics(
    {
        "vehicle": vehicle_type,
        "models":
        {
            "linear":
                res_linear["overall"],

            "residual_gain_pct":
                float(improvement)
        }
    },
    cfg.paths.metrics_out
    )

    print(f"\n [evaluation] Permuation: feature importance for {linear_model}:")



    # --------------------------------------------------
    # ── 11. plots ─────────────────────────────────────
    # --------------------------------------------------

    actual_next = actual_mlp if actual_mlp is not None else actual_linear

    df_test     = df.iloc[len(X_train):].reset_index(drop=True)

    run_plots(
        df_test         = df_test,
        actual_next     = actual_next,
        preds_dict      = all_preds,
        state_vars      = output_vars,
        input_vars      = cfg.input_vars,
        cfg             = cfg,
        best_estimator  = mlp_model,
        X_train_scaled  = X_tr_s,
        y_train_scaled  = y_tr_s,
    )



    # --------------------------------------------------
    # ── 12. MPC closed-loop comparison ────────────────
    # --------------------------------------------------

    dT = df['dT'].mean() if 'dT' in df.columns else 0.02

    feature_spec = {
        "state_vars": output_vars,
        "input_vars": cfg.input_vars,
        "feature_list": features,
        "aux_vars": [],
        "dt": dT,   # or just 0.1 if you want fixed
    }

    # dynamic validation tracking simulation run
    print("\n[pipeline] ── Launching MPC Closed-Loop Simulation Validation ──")
    simulation_results  = run_mpc_comparison(
        cfg             = cfg,
        df_test         = df_test,
        state_vars      = output_vars,
        input_vars      = cfg.input_vars,
        feature_spec    = feature_spec,
        mlp_model       = linear_model,
        best_model_obj  = mlp_model,
        scaler_X        = scaler_X,
        scaler_y        = scaler_y,
        sigma_bounds    = sigma_bounds
    )

    ref_trajectory = mpc_bundle.get('ref_traj', np.zeros((len(df_test), len(output_vars))))
    simulation_dt  = float(mpc_bundle.get('dT', 0.05))

    # compile and export the interactive Plotly HTML dashboards to src/plot.py
    run_plotly_dashboard(
        results     = simulation_results,
        ref_traj    = ref_trajectory,
        state_vars  = output_vars,
        input_vars  = cfg.input_vars,
        dT          = simulation_dt,
        bat_mah     = float(getattr(cfg.mpc, 'battery_mah', 10000.0)),
        v_nominal   = float(getattr(cfg.mpc, 'v_nominal', 22.2)),
        save_dir    = Path(cfg.paths.plots)
    )

    print(f"\n[pipeline] Complete. Vehicle: {vehicle_type}")



    # --------------------------------------------------
    # ── 13. optimal hub placement ─────────────────────
    # --------------------------------------------------

    print("\n" + "="*60)
    print("[strategic planner] Initiating Facility Location Routing...")
    print("="*60)

    # initialize mock environment, network, and weather models
    t_start_strategic = time.perf_counter()

    # instantiate the trained offline evaluation pipeline mapping
    physics_weather = PhysicsInformedWeatherEngine(
        mlp         = mlp_model,
        linear      = linear_model,
        s_X         = scaler_X,
        s_y         = scaler_y,
        sigmas      = sigma_bounds,
        aero_config = AERO_PARAMS,
    )

    class GexfInfrastructureNetwork:
        def __init__(self, gexf_path, coords_csv_path, demand_csv_path):
            # parse the network layout directly using NetworkX
            self.G = nx.read_gexf(gexf_path)
            
            # parse explicit spatial node coordinates from CSV
            df_coords = pd.read_csv(coords_csv_path)
            self.node_positions = {}
            self.node_types = {}
            
            for _, row in df_coords.iterrows():
                name = str(row['Name']).strip()
                self.node_positions[name] = (float(row['x_miles']), float(row['y_miles']))
                self.node_types[name] = str(row['Type']).strip()

            # parse and capture the true Healthcare transaction demand matrix matrix
            self.Dmat = pd.read_csv(demand_csv_path, index_col=0)
            
            # expose candidate hubs lists as a formatted DataFrame for .iterrows() loops
            h_data = [
                {"Name": name, "x_miles": pos[0], "y_miles": pos[1]}
                for name, pos in self.node_positions.items() if self.node_types.get(name) == "CandidateHub"
            ]
            self.candidate_hubs = pd.DataFrame(h_data)

        def get_nodes(self, node_type):
            return [k for k, v in self.node_types.items() if v == node_type]

        def get_position(self, node_name):
            return self.node_positions.get(str(node_name).strip(), (0.0, 0.0))
        
        def route_via_hub(self, c, h, hosp):
            # generates Dijkstra flight paths directly across your active graph connections
            path_to_hub = nx.shortest_path(self.G, source=c, target=h, weight='distance')
            path_to_hosp = nx.shortest_path(self.G, source=h, target=hosp, weight='distance')
            return path_to_hub + path_to_hosp[1:]
        
    # file paths pointing to directory
    gexf_file   = "data/gis/CNO_graph_within_40mi.gexf"
    coords_file = "data/candidate_hubs/CNO_node_coordinates.csv"
    demand_file = "data/candidate_hubs/CNO_demand_matrix.csv"
    production_net = GexfInfrastructureNetwork(gexf_file, coords_file, demand_file)
    
    optimizer = HubOptimizer(
        network     = production_net, 
        weather     = physics_weather, 
        environment = Environment
    )
    
    # pass mission parameters down to discover the lowest execution Wh path choice
    print(f"[strategic planner] Evaluating {len(production_net.candidate_hubs)} candidates over wind rose cases...")

    # define target operational mode to trigger console prints:
    #   1. "discrete"  -> top raw independent locations
    #   2. "dispersed" -> spatially diverse infrastructure network (enforcing 25-mi clear zones)
    #   3. "continuous"-> un-gridded optimization with continuous 40-mi constraints

    ACTIVE_MODE      = cfg.active_strategic_mode
    TARGET_HUB_COUNT = cfg.target_hubs_count

    print(f"[strategic planner] Processing candidate mesh list [Mode={ACTIVE_MODE.upper()}]...")
    
    # pass the mode and target count into the unified HubOptimizer class wrapper
    optimal_placements_df   = optimizer.optimize(
        mode                = ACTIVE_MODE, 
        target_count        = TARGET_HUB_COUNT
    )
    # print the returned dataframe matrix to guarantee console visibility 
    print("\n" + "="*60)
    print(f" Final Hub Placement Results: {ACTIVE_MODE.upper()} Matrix")
    print("="*60)
    if isinstance(optimal_placements_df, pd.DataFrame) and not optimal_placements_df.empty:
        print(optimal_placements_df.head(TARGET_HUB_COUNT))
    else:
        print("[WARNING] Optimization output did not yield a valid printable DataFrame structure.")
    print("="*60 + "\n")

    # stop the execution clock immediately after the multi-commodity flow solver wraps up
    elapsed_strategic_sec = time.perf_counter() - t_start_strategic
    print("\n[success] Strategic Pipeline Integrated.")
    print(f"[timing] Strategic Hub Optimization completed in: {elapsed_strategic_sec:.3f} seconds")
    print("\n[pipeline] DATUM Core System Identification Pipeline Completed Safely.\n")


if __name__ == "__main__":
    main()


"""
citations:

- Hub Weber Facility location for Dijkstra:

@article{Aneja1994TechnicalN,
  title={Technical Note - Algorithms for Weber Facility Location in the Presence of Forbidden Regions and/or Barriers to Travel},
  author={Yash P. Aneja and Mahmut Parlar},
  journal={Transp. Sci.},
  year={1994},
  volume={28},
  pages={70-76},
  url={https://api.semanticscholar.org/CorpusID:30981798}
}


"""