"""
src/network/network.py

connects hospitals, clinics, and candidate hubs into a network graph

"""

import matplotlib         as mpl

from network.network              import Network
from planning.mission             import Mission
from environment.environment      import Environment
from planning.hub_optimizer       import HubOptimizer
from weather.historical_weather   import HistoricalWeather


mpl.rcParams.update({
    "text.usetex": False,
    "font.family": "serif",
    "font.serif": ["DejaVu Serif"],  # matplotlib’s built-in LaTeX-like font
    "axes.labelsize": 13,
    "axes.titlesize": 14,
    "legend.fontsize": 11,
})

network = Network(
    graph_file  = "data/network/graph.gexf",
    edge_file   = "data/network/edges.csv",
    node_file   = "data/network/nodes.csv",
    demand_file = "data/network/demand_matrix.csv")


environment = Environment(
    unfeasible_rects=[
        (0, 20, 60, 100),
        (20, 80, 80, 100),
    ]
)


weather = HistoricalWeather(    )


hub_optimizer = HubOptimizer(
    network,
    weather,
    environment
)


mission = Mission(
    origin      = "Broken Bow",
    destination = "Durant",
)


selected_hub            = hub_optimizer.optimize(mission)
mission.selected_hub    = selected_hub


# run_controller(mission)