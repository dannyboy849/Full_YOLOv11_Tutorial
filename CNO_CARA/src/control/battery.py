"""
src/control/battery.py

coulomb-counting battery model for estimating SoC, energy, and endurance

"""

import numpy                as np

from sklearn.linear_model   import Ridge


class BatteryModel:
    """
    coulomb-counting battery

    parameters
    ----------
    capacity_mah : float   Rated capacity in mAh   (10,000 mAh)
    soc_min      : float   Hard lower SoC limit    (0.15 = 15 %)
    soc_rth      : float   Return-to-home trigger  (0.25 = 25 %)
    v_nominal    : float   Nominal pack voltage [V](22.2 V for 6S LiPo)
    """
    def __init__(self,
                 capacity_mah: float = 10000.0,
                 soc_min:      float = 0.15,
                 soc_rth:      float = 0.25,
                 v_nominal:    float = 22.2):

        self.capacity_ah        = capacity_mah / 1000.0   # convert to Ah
        self.capacity_coulomb   = self.capacity_ah * 3600.0
        self.soc_min            = soc_min
        self.soc_rth            = soc_rth
        self.v_nominal          = v_nominal
        self.capacity_j         = (
            self.capacity_ah *
            self.v_nominal *
            3600.0
        )
        self.reset()


    def reset(self, soc0: float = 1.0):
        self.soc          = soc0
        self.energy_j     = 0.0          # cumulative energy consumed [J]
        self.rth_triggered = False
        self._elapsed = 0.0


    def step(self, power_w: float, current_a: float, dT: float) -> dict:
        """
        Advance battery state by one timestep.

        power_w   : instantaneous power [W]  (V*I from telemetry or proxy)
        current_a : estimated draw [A]
        dT        : timestep [s]
        """
        # coulomb counting
        delta_soc = (current_a * dT) / (3600.0 * self.capacity_ah)
        self.soc = np.clip(self.soc - delta_soc, 0.0, 1.0)      

        # energy integration                         
        self.energy_j += float(power_w * dT)

        if self.soc <= self.soc_rth and not self.rth_triggered:
            self.rth_triggered = True
            print(f"[battery] RTH triggered — SoC={self.soc:.2%}")

        return {
            'soc':      self.soc,
            'energy_j': self.energy_j,
            'rth':      self.rth_triggered,
        }


    def endurance_remaining(self, avg_power_w: float) -> float:
        """estimated remaining flight time [s] at current avg power."""
        if avg_power_w <= 1e-6:
            return float('inf')
        return (self.soc * self.capacity_ah * 3600 * self.v_nominal) / avg_power_w


    def total_endurance(self, elapsed_time: float) -> float:
        """theoretical max endurance at current avg consumption [s]."""
        avg_p = self.energy_j / max(elapsed_time, 1e-6)

        return self.capacity_j / max(avg_p, 1e-6)


def estimate_w_diag(df, input_vars, current_col='bat_cur'):
    """
    estimates W_diag coefficients for quadratic current draw:
    current [A] ≈ Σ (W_i * normalized_u_i^2)
    """
    if current_col not in df.columns:
        # fallback: standard quadcopter proxy (~5A per motor at full throttle)
        return np.array([5.0] * len(input_vars))

    # normalize PWM 1000-2000 to 0.0-1.0
    U       = df[input_vars].values
    U_norm  = np.clip((U - 1000.0) / 1000.0, 0.0, 1.0)
    U_sq    = U_norm**2
    
    y       = df[current_col].values

    # fit quadratic model (no intercept because 0 throttle = 0 current)
    model   = Ridge(alpha=0.1, fit_intercept=False)
    model.fit(U_sq, y)

    # ensure weights are positive
    return np.maximum(model.coef_, 1e-6)


def estimate_power(u,
                   power_traj,
                   step_idx,
                   W_diag = None,
                   v_nominal = 22.2):
    """
    return (power_w, current_a) for one timestep.

    priority:
      1. logged telemetry in power_traj (P = V*I)
      2. quadratic proxy P = u^T W u  (W identified from log regression)
      3. fallback: uniform motor current model
    """
    # ── 1. real telemetry ─────────────────────
    if power_traj is not None and step_idx < len(power_traj):
        p = float(power_traj[step_idx])
        p = max(0.0, p)
        i = p / max(v_nominal, 1e-6)
        return p, i

    # ── 2. fallback to Quadratic Regression Weights ────────────
    u       = np.asarray(u, dtype=float)
    u_norm  = np.clip((u - 1000.0) / 1000.0, 0.0, 1.0)
    
    if W_diag is not None:
        # current = sum of (W_i * u_i^2)
        i = float(np.sum(W_diag * (u_norm**2)))
    else:
        # fallback if W_diag wasn't provided
        i = float(np.clip(np.linalg.norm(u_norm) * 3.0, 0.0, 40.0))
        
    p = v_nominal * i
    return p, i