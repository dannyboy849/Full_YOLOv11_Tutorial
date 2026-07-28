"""
mission.py

defines the mission object shared between the strategic planner,
DATUM controller, and simulation engine

the Mission object contains the current mission state, planned
trajectory, selected launch hub, weather assumptions, and mission
progress
"""


import numpy as np

from enum         import Enum
from __future__   import annotations
from dataclasses  import dataclass, field


class MissionStatus(Enum):
    PLANNING    = "planning"
    READY       = "ready"
    RUNNING     = "running"
    REPLANNING  = "replanning"
    COMPLETE    = "complete"
    ABORTED     = "aborted"


@dataclass
class Mission:

    # user request
    origin:      str
    destination: str

    # hub information
    selected_hub: str | None = None

    # generated route
    route_nodes: list = field(default_factory=list)


    waypoints: np.ndarray = field(
        default_factory=lambda: np.empty((0,3))
    )


    reference_trajectory: np.ndarray = field(
        default_factory=lambda: np.empty((0,0))
    )

    # mission metrics
    expected_distance:  float       = 0.0

    expected_energy:    float       = 0.0

    expected_time:      float       = 0.0

    expected_risk:      float       = 0.0

    selected_hub_score: float       = 0.0

    candidate_hubs:     list        = field(default_factory=list)

    replan_reason:      str | None  = None


    # weather
    historical_weather: object | None = None

    current_weather:    object | None = None


    # battery
    initial_soc: float = 1.0

    minimum_soc: float = 0.30


    # runtime state
    current_waypoint: int = 0

    status: MissionStatus = MissionStatus.PLANNING


    # helper functions
    def start(self):

        self.status = MissionStatus.RUNNING


    def complete(self):

        self.status = MissionStatus.COMPLETE


    def abort(self):

        self.status = MissionStatus.ABORTED


    def request_replan(self):

        self.status = MissionStatus.REPLANNING


    def next_waypoint(self):

        if self.current_waypoint < len(self.waypoints)-1:

            self.current_waypoint += 1

        return self.current_reference()


    def current_reference(self):

        if len(self.reference_trajectory) == 0:

            return None

        idx = min(

            self.current_waypoint,

            len(self.reference_trajectory)-1

        )

        return self.reference_trajectory[idx]


    @property
    def finished(self):

        return self.status in (

            MissionStatus.COMPLETE,

            MissionStatus.ABORTED

        )