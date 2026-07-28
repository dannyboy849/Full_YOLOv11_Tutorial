"""
src/utils/vehicle.py

UAS-type selection and motor/input configuration
prompts user at runtime OR reads from cfg.vehicle_type if its already set

supports: quadcopter, hexacopter, vtol
"""

import profile

from types import SimpleNamespace


# --------------------------------------------------
# ── UAS profiles ──────────────────────────────────
# --------------------------------------------------
# each profile defines:
#   motor_channels : list of PWM output column names in the CSV
#   n_motors       : int
#   has_transition : bool  (VTOL only. considers hover vs fixed-wing mode)
#   extra_inputs   : non-motor control channels (tilt servo)


VEHICLE_PROFILES = {
    "quadcopter": {
        "motor_channels": ["RCOU_1", "RCOU_2", "RCOU_3", "RCOU_4"],
        "n_motors":       4,
        "u_min": [1000]*4,
        "u_max": [2000]*4,
        "has_transition": False,
        "motor_types": [
            "lift",
            "lift",
            "lift",
            "lift"
        ],
    },

    "vtol": {
        "motor_channels": ["RCOU_1", "RCOU_2", "RCOU_3", 
                           "RCOU_4", "RCOU_5"],
        "n_motors":       5,
        "u_min": [1000]*5,
        "u_max": [2000]*5,
        "has_transition": True,
        "motor_types": [
            "pusher",
            "lift",
            "lift",
            "lift",
            "lift"
        ],

    },

    "hexacopter": {
        "motor_channels": ["RCOU_1", "RCOU_2", "RCOU_3",
                           "RCOU_4", "RCOU_5", "RCOU_6"],
        "n_motors":       6,
        "u_min": [1000]*6,
        "u_max": [2000]*6,
        "has_transition": False,
        "motor_types": [
            "lift",
            "lift",
            "lift",
            "lift",
            "lift",
            "lift"
        ],
    },
}


AERO_PARAMS = {
    'vehicle': {'profile': 'ONSSI-320', 'mass_kg': 21.5, 'mean_chord_m': 0.34},
    'fw': {'cd0': 0.0201743, 'k': 0.0296506, 'eta': 0.75, 'uses_reynolds': True, 'reynolds_ref': 537739.8},
    'vtol': {
        'model': 'phys_v1', 
        'p_idle_w': 620.116, 
        'k_lift_w': 266.363, 
        'k_lift_v_w_per_ms': 3.988e-09, 
        'k_drag_w_per_ms3': 1.865e-17, 
        'k_push_w': 142.102,
        'lift_exp': 1.0, 
        'lift_min': 0.2991, 
        'lift_span': 0.6122
    },
    'battery': {'capacity_ah': 27.0, 'voltage_nominal_v': 44.4, 'avionics_power_w': 50.0, 'wing_area_m2': 0.8, 'rho_kgm3': 1.225, 'mu_pa_s': 1.81e-5},
    'rft_scenario': {'target_ground_speed_mps': 21.0, 'vtol_lift_proxy': 0.25, 'vtol_airspeed_mps': 5.0, 'vtol_pusher_proxy': 0.0}
}

MENU = {
    "1": "quadcopter",
    "2": "hexacopter",
    "3": "vtol",
}


def select_vehicle(cfg: SimpleNamespace) -> str:

    """
    return UAS-type string
    uses cfg.vehicle_type if set and valid, otherwise prompts the user
    """

    preset = getattr(cfg, "vehicle_type", None)
    if preset and preset.lower() in VEHICLE_PROFILES:
        print(f"[vehicle] Using vehicle type from config: {preset.lower()}")
        return preset.lower()

    print("This script supports Quadrotor, Hexacopter, and VTOL configurations.")
    print("\n" + "="*50)
    print("  Select vehicle type:")
    print("    1 — Quadcopter")
    print("    2 — Hexacopter")
    print("    3 — VTOL")
    print("="*50)
    while True:
        choice = input("  Enter 1, 2, or 3: ").strip()
        if choice in MENU:
            vtype = MENU[choice]
            print(f"[vehicle] Selected: {vtype}")
            return vtype
        print("  Invalid choice. Please enter 1, 2, or 3.")


def get_vehicle_profile(vehicle_type: str) -> dict:
    if vehicle_type not in VEHICLE_PROFILES:
        raise ValueError(f"Unknown vehicle type: '{vehicle_type}'. "
                         f"Choose from: {list(VEHICLE_PROFILES)}")
    return VEHICLE_PROFILES[vehicle_type]


def apply_vehicle_to_cfg(cfg, vehicle_type):

    """
    overwrites cfg.input_vars and cfg.vehicle_profile with UAV-specific
    motor channels + any extra input channels
    """

    profile = VEHICLE_PROFILES[vehicle_type]

    cfg.mpc.u_min = profile["u_min"]
    cfg.mpc.u_max = profile["u_max"]

    cfg.input_vars = profile["motor_channels"]

    cfg.vehicle_profile = SimpleNamespace(
        **profile
    )

    cfg.vehicle_type = vehicle_type

    print(f"[vehicle] Input channels ({len(cfg.input_vars)}): {cfg.input_vars}")
    return cfg