"""
src/prepare.py
loads raw CSV, sets up features (yaw sin/cos, delta targets, dT),
drops bad rows, and returns clean DataFrames + column lists

called by: DATUM.py

new additions 4/7/26:
energy-awareness, power_w, flight_phase, and gyro acceleration
"""

import numpy    as np
import pandas   as pd

from types      import SimpleNamespace


# --------------------------------------------------
# ── power state  ──────────────────────────────────
# --------------------------------------------------

def add_power_feature(df: pd.DataFrame) -> pd.DataFrame:
    """
    adds 'power_w' = bat_volt * bat_current (Watts)
    falls back if columns are missing

    ArduPilot column names: BAT.Volt, BAT.Curr
    CSV uses: bat_volt, bat_curr
    """
    # common column name variants
    volt_candidates = ['bat_volt', 'BAT.Volt', 'BATT.Volt', 'voltage']
    curr_candidates = ['bat_cur', 'bat_curr','bat_current', 'BAT.Curr', 'BATT.Curr', 'current']

    volt_col = next((c for c in volt_candidates if c in df.columns), None)
    curr_col = next((c for c in curr_candidates if c in df.columns), None)

    if volt_col and curr_col:
        df['power_w'] = (
            pd.to_numeric(df[volt_col], errors='coerce') *
            pd.to_numeric(df[curr_col], errors='coerce')
        ).fillna(0.0)
        print(f"[prepare] Power Range: "
            f"{df['power_w'].min():.1f} -- {df['power_w'].max():.1f} W")
    else:
        df['power_w'] = 0.0
        print("[prepare] power_w: battery columns not found → set to 0. "
            f"Available cols with 'bat'/'volt': "
            f"{[c for c in df.columns if any(k in c.lower() for k in ['bat','volt','curr'])]}")

    return df



# --------------------------------------------------
# ── flight phase classifier  ──────────────────────
# --------------------------------------------------

def _classify_phase(
    alt: pd.Series,
    cr: pd.Series,
    x_speed: pd.Series,
    window: int = 5,
) -> pd.Series:
    
    """
    0 = Ground (Zero risk, controller can warm-start / sleep)
    1 = Takeoff / Hover-Climb (High structural load, transient risks)
    2 = VTOL Cruise / Loiter (Medium-low risk, nominal bounds)
    3 = Fixed-Wing Forward Flight (High speed, aerodynamic lift, distinct tuning)
    4 = Landing / Approach (High dynamic risk, ground effect zone)
    """

    # 1. smooth out noise to avoid erratic phase flipping
    cr_smooth = cr.rolling(window, center=True, min_periods=1).mean()
    alt_smooth = alt.rolling(window, center=True, min_periods=1).mean()

    # 2. derive statistical thresholds from real flight bounds
    sigma = cr.std()
    climb_thresh = 0.5 * sigma      # upward trend
    descent_thresh = -0.5 * sigma   # downward trend

    # initialize all as unclassified (-1) to guarantee strict evaluation
    phase = pd.Series(-1, index=alt.index, dtype=np.int8)


    # --------------------------------------------------
    # ── masks ─────────────────────────────────────────
    # --------------------------------------------------
    """
    it's important to note two distinct profiles: fixed-wing and cruise. 
    fixed-wing means that it is acting as a traditional plane, 
    where the lift motors are completely shut off and use aerodynamics for lift

    cruise is the fallback, where the lift motors are actively being used
    """ 


    # --- phase 0: Ground ---
    # must be close to zero altitude, and not actively climbing/descending
    ground_mask = (alt_smooth < 1.5) & (cr_smooth.abs() < 0.3)
    phase[ground_mask] = 0

    # --- phase 3: fixed-Wing forward flight ---
    # high speed and high altitude take absolute priority over vertical rates
    
    fixed_wing_mask = (phase == -1) & (x_speed.abs() > 22.0) & (alt_smooth > 15.0)
    phase[fixed_wing_mask] = 3

    # --- phase 1: takeoff / vertical climb ---
    # positive vertical rate while not on the ground or in forward flight
    takeoff_mask = (phase == -1) & (cr_smooth > climb_thresh)
    phase[takeoff_mask] = 1

    # --- phase 4: landing / transition & descent ---
    # negative vertical rate while descending back toward the terrain
    landing_mask = (phase == -1) & (cr_smooth < descent_thresh)
    phase[landing_mask] = 4

    # --- phase 2: Cruise / Hover-Loiter ---
    # anything remaining at altitude that isn't speeding forward or moving vertically
    cruise_mask = (phase == -1) & (alt_smooth >= 1.5)
    phase[cruise_mask] = 2

    # fallback safety catch
    phase[phase == -1] = 2

    # --- debug and distribution analysis ---
    counts = phase.value_counts().sort_index()
    labels = {0: 'ground', 1: 'takeoff', 2: 'cruise', 3: 'fixed_wing', 4: 'landing'}
    print("[prepare] Flight phase distribution:")
    for k, v in counts.items():
        pct = 100 * v / len(phase)
        print(f"  {labels.get(k, k):<10} {v:>5} rows  ({pct:.1f}%)")

    return phase


def add_flight_phase(df: pd.DataFrame) -> pd.DataFrame:
    """
    adds 'flight_phase' integer column (0=ground, 1=takeoff, 2=cruise, 3=fixed_wing, 4=landing)
    requires bar_alt and bar_cr columns
    """
    if 'bar_alt' not in df.columns or 'bar_cr' not in df.columns or 'x_speed' not in df.columns:
        print("[prepare] flight_phase: one or more required columns missing — skipped.")
        df['flight_phase'] = 2   # assume cruise
        return df

    df['flight_phase'] = _classify_phase(df['bar_alt'], df['bar_cr'], df['x_speed'])
    return df
    


# --------------------------------------------------
# ── phase-aware Q weights for MPC ─────────────────
# --------------------------------------------------

def get_phase_Q_weights(phase: int, base_Q: list,
                        phase_weights: dict) -> list:
    """
    returns phase-specific Q weights for the MPC cost function

    phase_weights from mpc.yaml:
    phase_weights:
        takeoff:  {Q_alt: 15.0, gamma: 0.5}
        cruise:   {Q_alt: 10.0, gamma: 2.0}
        landing:  {Q_alt: 20.0, gamma: 0.5}

    only alt index (0) is modified
    """
    phase_map = {0: 'ground', 1: 'takeoff', 2: 'cruise', 3: 'landing'}
    label = phase_map.get(phase, 'cruise')
    pw = phase_weights.get(label, {})

    Q = list(base_Q)
    if 'Q_alt' in pw:
        Q[0] = float(pw['Q_alt'])   # bar_alt is index 0
    return Q


def get_phase_gamma(phase: int, phase_weights: dict,
                    default_gamma: float = 1.0) -> float:
    """returns the energy penalty weight gamma for the current flight phase"""
    phase_map = {0: 'ground', 1: 'takeoff', 2: 'cruise', 3: 'landing'}
    label = phase_map.get(phase, 'cruise')
    return float(phase_weights.get(label, {}).get('gamma', default_gamma))



# --------------------------------------------------
# ── prepare MPC data ──────────────────────────────
# --------------------------------------------------

def prepare_mpc_data(df: pd.DataFrame, cfg: SimpleNamespace):

    """
    parameters
    ----------
    df  : raw DataFrame loaded from CSV
    cfg : merged config namespace (needs cfg.input_vars, cfg.output_vars,
          cfg.time_col)

    this returns:
    -------
    df              : cleaned DataFrame
    features        : list of input feature column names
    output_vars     : list of state column names
    target_deltas   : list of Δ-target column names
    """

    input_vars  = cfg.input_vars
    output_vars = list(cfg.output_vars)
    if "att_act_yaw" in output_vars:
        output_vars.remove("att_act_yaw")
        output_vars.extend([
            "yaw_sin",
            "yaw_cos"
        ])
    aux_vars    = cfg.aux_vars
    time_col    = cfg.time_col



    # --------------------------------------------------
    # ── sort and calculate dT ─────────────────────────
    # --------------------------------------------------

    df = df.sort_values(time_col).reset_index(drop=True)
    df["dT"] = df[time_col].diff().bfill()



    # --------------------------------------------------
    # ── drop rows w/ missing core columns ─────────────
    # --------------------------------------------------

    # drop pre-arm
    motor_cols = [c for c in input_vars if c in df.columns]
    n_before = len(df)
    df = df[df[motor_cols].max(axis=1) > 1050].reset_index(drop=True)
    print(f"[prepare] Pre-arm filter: dropped {n_before - len(df)} rows, "
        f"{len(df)} remaining")
    
    # drop rows with missing core columns
    core_cols = [c for c in input_vars + output_vars if c in df.columns]
    n_before = len(df)
    df = df.dropna(subset=core_cols).reset_index(drop=True)
    print(f"[prepare] Dropped {n_before - len(df):,} rows (missing core cols). "
          f"Remaining: {len(df):,}")

    if len(df) == 0:
        raise ValueError("No data remains after dropping rows with missing core columns.")



    # --------------------------------------------------
    # ── yaw sin/cos ───────────────────────────────────
    # --------------------------------------------------

    yaw_rad = np.radians(df["att_act_yaw"])
    df["yaw_sin"] = np.sin(yaw_rad)
    df["yaw_cos"] = np.cos(yaw_rad)



    # --------------------------------------------------
    # ── energy-awareness  ─────────────────────────────
    # --------------------------------------------------
    # power state
    df = add_power_feature(df)

    # normalize altitude
    if 'bar_alt' in df.columns:
        alt0 = df['bar_alt'].iloc[0]
        df['bar_alt'] = df['bar_alt'] - alt0
        print(f"[prepare] bar_alt normalized (offset {alt0:.3f}) → "
            f"range [{df['bar_alt'].min():.2f}, {df['bar_alt'].max():.2f}]")
    # flight phase
    df = add_flight_phase(df)



    # --------------------------------------------------
    # ── wind maps ────────────────────────────────────
    # --------------------------------------------------

    DIR_MAP = {
        "N": 0,
        "NE": 45,
        "E": 90,
        "SE": 135,
        "S": 180,
        "SW": 225,
        "W": 270,
        "NW": 315
    }

    STRENGTH_MAP = {
        "Light": 1,
        "Moderate": 2,
        "Fresh": 3,
        "Strong": 4,
        "Gale": 5
    }

    df["windDirection_deg"] = (
        df["windDirection"]
        .astype(str)
        .str.strip()
        .map(DIR_MAP)
    )

    df["windStrength_idx"] = (
        df["windStrength"]
        .astype(str)
        .str.strip()
        .map(STRENGTH_MAP)
    )

    theta = np.deg2rad(df["windDirection_deg"])

    df["wind_x"] = (
        df["windSpeed"]
        * np.cos(theta)
    )

    df["wind_y"] = (
        df["windSpeed"]
        * np.sin(theta)
    )



    # --------------------------------------------------
    # ── normalized attitudes ────────────────────────────
    # --------------------------------------------------
    if 'att_act_roll' in df.columns:
        roll_offset = df['att_act_roll'].median()
        df['att_act_roll'] = df['att_act_roll'] - roll_offset
        df['att_act_roll'] = ((df['att_act_roll'] + 180) % 360) - 180

    if 'att_act_yaw' in df.columns:
        # Yaw: just wrap to [-180, 180], don't subtract offset
        df['att_act_yaw'] = ((df['att_act_yaw'] + 180) % 360) - 180

    if 'att_act_pitch' in df.columns:
        # Pitch is already in normal convention, just clip
        df['att_act_pitch'] = df['att_act_pitch'].clip(-60.0, 60.0)

    print(f"[prepare] Attitude ranges after normalization:")

    for col in ['att_act_roll', 'att_act_pitch', 'att_act_yaw']:
        if col in df.columns:
            print(f"  {col}: [{df[col].min():.2f}, {df[col].max():.2f}]")


    # --------------------------------------------------
    # ── delta targets  ────────────────────────────────
    # --------------------------------------------------

    #  that is, Δx = x_{k+1} − x_k
    for var in output_vars:
        df[f"{var}_next"]  = df[var].shift(-1)
        df[f"delta_{var}"] = df[f"{var}_next"] - df[var]

    state_features = output_vars
    features = (input_vars + state_features + aux_vars + ["dT"])
    target_deltas = [f"delta_{v}" for v in output_vars]

    print("\n===== REQUIRED COLS =====")
    print("Features:", len(features))
    print("Targets :", len(target_deltas))

    # leakage guard
    assert not any(f.endswith("_next") for f in features), \
        "Leakage: a '_next' column snuck into FEATURES"



    # --------------------------------------------------
    # ── numeric and final NaN drop ────────────
    # --------------------------------------------------

    all_cols = features + target_deltas
    df[all_cols] = df[all_cols].apply(pd.to_numeric, errors="coerce")

    for c in features:
        n = df[c].isna().sum()

        if n > 0:
            print(
                f"{c}: {n}/{len(df)} NaNs"
            )

    df = df.dropna(subset=all_cols).reset_index(drop=True)
    print(f"[prepare] Final row count after delta NaN drop: {len(df):,}")



    print("After final drop:", len(df))
    print("Feature matrix shape:")
    print(df[features].shape)
    print("Target matrix shape:")
    print(df[target_deltas].shape)


    return df, features, output_vars, target_deltas