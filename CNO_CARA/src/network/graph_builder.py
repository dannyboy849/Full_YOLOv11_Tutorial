"""
src/network/graph_builder.py

builds a directed graph of edges within range of candidate hubs

again, it uses Dijkstra to find points

"""

import pandas as pd

from src.network.network import nx


class GraphBuilder:

    def build(
        self,
        node_file,
        edge_file
    ):

        nodes = pd.read_csv(node_file)
        edges = pd.read_csv(edge_file)
        graph = nx.DiGraph(name="Edges within range")

        for _, row in nodes.iterrows():

            graph.add_node(
                row["Name"],
                type    = row["Type"],
                x       = row["x_miles"],
                y       = row["y_miles"]
            )

        for _, row in edges.iterrows():

            graph.add_edge(

                row["origin"],
                row["destination"],
                distance        = row["cost_miles"],
                weight          = row["cost_miles"],
                energy          = row.get("energy_wh",0.0),
                risk            = row.get("risk",0.0),
                stability       = row.get("stability",1.0),
                time            = row.get("flight_time",0.0),
                control_effort  = row.get("control_effort",0.0),
                battery_margin  = row.get("battery_margin",0.0)

            )
        return graph