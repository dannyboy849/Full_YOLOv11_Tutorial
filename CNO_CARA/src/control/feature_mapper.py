"""
src/feature_mapper.py
"""

import numpy    as np

from casadi     import vertcat


# --------------------------------------------------
# ── feature mapper ──────────────────——────────────
# --------------------------------------------------

class FeatureMapper:

    def __init__(self, feature_spec):
        self.feature_list   = feature_spec["feature_list"]
        self.state_vars     = feature_spec["state_vars"]
        self.input_vars     = feature_spec["input_vars"]
        self.aux_vars       = feature_spec["aux_vars"]


    def build(self, x, u, aux):
        feat = {}

        for i, k in enumerate(self.state_vars):
            feat[k] = x[i]

        for i, k in enumerate(self.input_vars):
            feat[k] = u[i]

        for k, v in aux.items():
            feat[k] = v

        return vertcat(*[feat.get(f, 0.0) for f in self.feature_list])
