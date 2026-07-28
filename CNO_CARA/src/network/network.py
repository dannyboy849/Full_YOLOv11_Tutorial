"""
src/network/network.py

builds a network graph of hospitals, clinics, and candidate hubs

"""

import math
import pandas       as pd
import networkx     as nx

from src.network    import network


# ----------------------------
# load files
# ----------------------------

def euclidean_distance(p1, p2):
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

    
class Network:

    def __init__(
        self,
        graph_file,
        edge_file,
        node_file,
        demand_file):

        self.nodes      = pd.read_csv(node_file)
        self.edges      = pd.read_csv(edge_file)
        self.Dmat       = pd.read_csv(demand_file, index_col=0)
        self.graph      = nx.read_gexf(graph_file)
        self.positions  = {row["Name"]: (row["x_miles"], row["y_miles"]) for _, row in self.nodes.iterrows()}


    def get_nodes(self, node_type=None):
        if node_type is None:
            return list(self.graph.nodes)

        return [
            n for n, d in self.graph.nodes(data=True)
            if d["type"] == node_type
        ]
    

    def get_node_dataframe(self, node_type=None):

        if node_type is None:
            return self.nodes

        return self.nodes[
            self.nodes["Type"] == node_type
        ]
    

    def get_node(self, name):
        return self.nodes[self.nodes["Name"] == name].iloc[0]
    

    def edge_metrics(
        self,
        origin,
        destination
    ):
        return self.graph[origin][destination]

    m = network.edge_metrics(
        "ClinicA",
        "Hub17"
    )

    print(
        m["energy"]
    )

    print(
        m["risk"]
    )


    def edge_cost(
        self,
        origin,
        destination,
        weights
    ):
        edge = self.graph[origin][destination]

        return (
            weights.energy * edge["energy"]
            +
            weights.risk * edge["risk"]
            +
            weights.time * edge["time"]
            +
            weights.control * edge["control_effort"]
            +
            weights.stability *
            (1-edge["stability"])
        )

    def feasible_candidate_hubs(self, origin, destination, max_leg=40):
        """
        returns a list of candidate hubs that are feasible for the given origin and destination
        a hub is considered feasible if it can be reached from the origin and can reach the destination
        within the specified maximum leg distance
        """
        feasible_hubs = []

        for hub in self.get_nodes("CandidateHub"):
            try:
                # check if the hub is reachable from the origin
                dist_to_hub = nx.shortest_path_length(self.graph, source=origin, target=hub, weight='weight')
                # check if the destination is reachable from the hub
                dist_to_destination = nx.shortest_path_length(self.graph, source=hub, target=destination, weight='weight')

                if dist_to_hub <= max_leg and dist_to_destination <= max_leg:
                    feasible_hubs.append(hub)
            except nx.NetworkXNoPath:
                # if there is no path to or from the hub, it is not feasible
                continue

        return feasible_hubs


    def shortest_path(self, origin, destination):
        """
        returns the shortest path from origin to destination using Dijkstra's algorithm.
        """
        try:
            path = nx.dijkstra_path(self.graph, origin, destination, weight='weight')
            return path
        except nx.NetworkXNoPath:
            print(f"No path found from {origin} to {destination}.")
            return None 


    def path_distance(self, path):
        total_distance = 0
        for i in range(len(path) - 1):
            total_distance += self.graph[path[i]][path[i + 1]]['weight']
        return total_distance


    def get_position(self, node):
        return self.positions.get(node)


    def neighbors(self, node):
        return list(self.graph.neighbors(node))


    def route_via_hub(self, origin, hub, destination):
        """
        returns the route from origin to destination via the specified hub
        the route is a list of nodes representing the path
        """
        try:
            # find the shortest path from origin to hub
            path_to_hub = nx.shortest_path(self.graph, source=origin, target=hub, weight='weight')
            # find the shortest path from hub to destination
            path_to_destination = nx.shortest_path(self.graph, source=hub, target=destination, weight='weight')
            
            # combine the two paths, ensuring not to duplicate the hub node
            full_route = path_to_hub + path_to_destination[1:]  # skip the hub in the second part
            
            return full_route
        except nx.NetworkXNoPath:
            print(f"No path found via hub {hub} from {origin} to {destination}.")
            return None
        

    def route_distance_via_hub(self, origin, hub, destination):
        """
        returns the distance of the route from origin to destination via the specified hub
        """
        route = self.route_via_hub(origin, hub, destination)
        return self.path_distance(route)


    def reachable(self, start,goal):
        """
        returns True if the goal is reachable from the start node within the graph.
        """
        try:
            nx.shortest_path(self.graph, source=start, target=goal, weight='weight')
            return True
        except nx.NetworkXNoPath:
            return False