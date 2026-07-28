"""
src/network/candidate.py

defines the CandidateHub dataclass for representing potential hub locations

"""

from dataclasses import dataclass


@dataclass(slots=True)
class CandidateHub:

    name: str

    x: float

    y: float

    expected_energy: float = 0.0

    expected_time: float = 0.0

    expected_risk: float = 0.0

    expected_stability: float = 1.0

    expected_control_effort: float = 0.0

    battery_margin: float = 0.0

    score: float = 0.0