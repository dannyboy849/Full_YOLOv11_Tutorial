"""
planning/airspace.py

Strategic Airspace Evaluation Module

Phase 1
-------
Evaluates strategic routing penalties associated with controlled
airspace, airport influence regions, and obstacle clearance.

Designed so that FAA GIS layers can replace the manually-defined
regions without changing HubOptimizer.
"""

from __future__  import annotations

import numpy     as np

from typing      import Dict, List
from dataclasses import dataclass


# ---------------------------------------------------------
# Configuration Containers
# ---------------------------------------------------------


@dataclass
class AirspaceRegion:

    name: str

    latitude: float
    longitude: float

    radius_miles: float

    airspace_class: str

    ceiling_ft_msl: float
    floor_ft_agl: float

    obstacle_height_ft: float

@dataclass
class AirspaceEvaluator:

    DEFAULT_CLASS_WEIGHTS = {

        "G": 0.0,

        "E": 2.0,

        "D": 8.0,

        "C": 20.0,

        "B": 50.0,

        "Restricted": 100.0,

        "Prohibited": 500.0,
    }


    def __init__(self,cfg=None):
        self.cfg = cfg

        self.class_weights = self.DEFAULT_CLASS_WEIGHTS.copy()

        self.regions = self._load_default_regions()


    # -----------------------------------------------------

    def _load_default_regions(self) -> List[AirspaceRegion]:
        """
        Initial Oklahoma study regions.

        These are placeholders intended to be replaced
        by FAA GIS layers.
        """

        return [

            AirspaceRegion(
                name="Durant",

                latitude=33.942,

                longitude=-96.394,

                radius_miles=5.0,

                airspace_class="E",

                ceiling_ft_msl=18000,

                floor_ft_agl=700,

                obstacle_height_ft=1700,
            ),

            AirspaceRegion(
                name="McAlester",

                latitude=34.883,

                longitude=-95.783,

                radius_miles=5.5,

                airspace_class="D",

                ceiling_ft_msl=4000,

                floor_ft_agl=0,

                obstacle_height_ft=1900,
            ),

            AirspaceRegion(
                name="Idabel",

                latitude=33.909,

                longitude=-94.858,

                radius_miles=4.5,

                airspace_class="E",

                ceiling_ft_msl=18000,

                floor_ft_agl=700,

                obstacle_height_ft=1650,
            ),

            AirspaceRegion(
                name="Broken Bow",

                latitude=34.012,

                longitude=-94.755,

                radius_miles=4.0,

                airspace_class="G",

                ceiling_ft_msl=18000,

                floor_ft_agl=0,

                obstacle_height_ft=1600,
            ),
        ]

    # -----------------------------------------------------

    @staticmethod
    def _distance_miles(lat1, lon1, lat2, lon2):

        """
        Great-circle approximation.
        """

        earth_radius = 3958.8

        lat1 = np.radians(lat1)
        lon1 = np.radians(lon1)

        lat2 = np.radians(lat2)
        lon2 = np.radians(lon2)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = (
            np.sin(dlat / 2.0) ** 2
            + np.cos(lat1)
            * np.cos(lat2)
            * np.sin(dlon / 2.0) ** 2
        )

        return (
            2.0
            * earth_radius
            * np.arcsin(np.sqrt(a))
        )

    # -----------------------------------------------------

    def _clearance_penalty(
        self,
        vehicle_altitude_ft,
        obstacle_height_ft,
    ):

        clearance = (
            vehicle_altitude_ft
            - obstacle_height_ft
        )

        if clearance >= 500:
            return 0.0

        elif clearance >= 200:
            return 20.0

        elif clearance >= 100:
            return 100.0

        return 500.0


    def evaluate(
        self,
        edge,
        vehicle_altitude_ft=400.0,
    ) -> Dict:

        latitude = edge.mid_lat
        longitude = edge.mid_lon

        best = {

            "region": None,

            "airspace_level": "G",

            "crossing_distance": 0.0,

            "minimum_clearance": np.inf,

            "penalty": 0.0,
        }

        for region in self.regions:

            distance = self._distance_miles(

                latitude,

                longitude,

                region.latitude,

                region.longitude,
            )

            if distance > region.radius_miles:
                continue

            crossing = (
                region.radius_miles
                - distance
            )

            clearance = (
                vehicle_altitude_ft
                - region.obstacle_height_ft
            )

            self.airspace_penalty_gain = 1.0

            penalty = self.airspace_penalty_gain(
                self.class_weights[
                    region.airspace_class
                ]

                * crossing

                + self._clearance_penalty(
                    vehicle_altitude_ft,
                    region.obstacle_height_ft,
                )
            )

            if penalty > best["penalty"]:

                best = {

                    "region": region.name,

                    "airspace_level": region.airspace_class,

                    "crossing_distance": crossing,

                    "minimum_clearance": clearance,

                    "penalty": penalty,
                }

        return best