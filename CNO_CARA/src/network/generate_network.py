"""
src/network/generate_network.py

generates a network graph of hospitals, clinics, and candidate hubs

"""

import numpy    as np
import pandas   as pd
import networkx as nx

from itertools                  import permutations
from src.utils.config           import load_config
from evaluation.edge_evaluator  import EdgeEvaluator



# ----------------------------
# config
# ----------------------------
COORDS_CSV = "CNO_node_coordinates.csv"     # from earlier step
DEMAND_CSV = "CNO_demand_matrix.csv"        # used later in optimization
RANGE_MI   = 40.0                           # drone max leg distance
EDGE_CSV   = "CNO_edges_within_40mi.csv"
GRAPH_GEXF = "CNO_graph_within_40mi.gexf"   # graph connections data



# -------------------------------
# fixed hospital locations
# -------------------------------
offset = np.array([3.0, 3.0])
durant = np.array([0.0, 0.0]) + offset
D = 110.0                   # Durant <-> Talihina distance (mi)
theta = np.deg2rad(33.0)    # Talihina bearing from +x
talihina = durant + np.array([D*np.cos(theta), D*np.sin(theta)])  # (~95.26, 55.00)



# -------------------------------
# distances to each hospital (mi)
# -------------------------------
dists = {
    "Idabel": (104, 78),
    "Broken Bow": (107, 67),
    "Hugo": (57, 77),
    "Atoka": (38, 74),
    "McAlester": (79, 50),
    "Poteau": (145, 37),
    "Stigler": (134, 46),
}


# function: circle–circle intersection
def circle_circle_intersections(c1, r1, c2, r2):
    p0, p1 = np.asarray(c1), np.asarray(c2)
    d = np.linalg.norm(p1 - p0)
    if d == 0 or d > r1 + r2 or d < abs(r1 - r2):
        return []
    a = (r1**2 - r2**2 + d**2) / (2*d)
    h_sq = r1**2 - a**2
    if h_sq < 0:
        return []
    h = np.sqrt(h_sq)
    p2 = p0 + a*(p1 - p0)/d
    perp = np.array([-(p1 - p0)[1], (p1 - p0)[0]])/d
    return [p2 + h*perp, p2 - h*perp]



# -------------------------------
# clinic coords
# -------------------------------

coords = {"Durant": durant, "Talihina": talihina}
left_side = {"Stigler", "McAlester", "Atoka"}  # lower x for these
chosen = {}

for name, (rD, rT) in dists.items():
    pts = circle_circle_intersections(durant, rD, talihina, rT)
    if not pts:
        continue
    if name in left_side:
        p = pts[0] if pts[0][0] <= pts[1][0] else pts[1]
    else:
        p = pts[0] if pts[0][0] >= pts[1][0] else pts[1]
    coords[name] = p
    chosen[name] = p

# 20-mile grid of candidate hub sites (yellow circles) 
minx, miny = 0, -20    # start x at 0, y at -20
maxx, maxy = 140, 120  # end x at 120, y at 100

step = 20.0
xs = np.arange(minx, maxx, step)
ys = np.arange(miny, maxy, step)
GX, GY = np.meshgrid(xs, ys)
grid_points = np.column_stack([GX.ravel(), GY.ravel()])

print(f"Generated {grid_points.shape[0]} grid candidate points with 20-mile spacing.")



# ----------------------------
# load data
# ----------------------------

df_nodes = pd.read_csv(COORDS_CSV)
# load OD for later use in optimization
try:
    D = pd.read_csv(DEMAND_CSV, index_col=0)
except FileNotFoundError:
    D = None

# build a lookup for coordinates and types
coords = df_nodes.set_index("Name")[["x_miles", "y_miles"]].to_dict("index")
types  = df_nodes.set_index("Name")["Type"].to_dict()



# ----------------------------
# helper: euclidean distance
# ----------------------------

def dist_mi(a, b):
    ax, ay = coords[a]["x_miles"], coords[a]["y_miles"]
    bx, by = coords[b]["x_miles"], coords[b]["y_miles"]
    return float(np.hypot(ax - bx, ay - by))



# ----------------------------
# build directed graph
# ----------------------------

G = nx.DiGraph(name=f"Edges within {RANGE_MI} mi")

# add nodes with attributes
for name, row in df_nodes.set_index("Name").iterrows():
    G.add_node(
        name,
        x=float(row["x_miles"]),
        y=float(row["y_miles"]),
        type=str(row["Type"]),
    )

# add directed edges i->j if distance <= RANGE_MI (i != j)
cfg = load_config("base", "dataset", "model", "mpc")
rows = []

for i,j in permutations(G.nodes,2):
    d = dist_mi(i,j)
    if d > RANGE_MI:
        continue

    pos_coords = (coords[i]["x_miles"], coords[i]["y_miles"])

    metrics = EdgeEvaluator.evaluate(
        origin      = i,
        destination = j,
        position_coords=pos_coords
    )

    G.add_edge(
        i,
        j,
        distance        = d,
        weight          = metrics.cost,
        energy          = metrics.energy,
        risk            = metrics.risk,
        stability       = metrics.stability,
        control_effort  = metrics.control_effort,
        battery_margin  = metrics.battery_margin
    )

    rows.append({
        "origin":i,
        "destination":      j,
        "distance":         d,
        "weight":           metrics.cost,
        "energy":           metrics.energy,
        "risk":             metrics.risk,
        "stability":        metrics.stability,
        "control_effort":   metrics.control_effort,
        "battery_margin":   metrics.battery_margin,
        "feasible":         metrics.feasible
    })



# ----------------------------
# save outputs
# ----------------------------

# 1) edge list CSV
edges_df = pd.DataFrame(rows)
edges_df.to_csv(EDGE_CSV, index=False)

# 2) graph file
nx.write_gexf(G, GRAPH_GEXF)

print(f"Nodes: {G.number_of_nodes()}  |  Edges (<= {RANGE_MI} mi): {G.number_of_edges()}")
print(f"   - Saved edge list to: {EDGE_CSV}")
print(f"   - Saved graph to:     {GRAPH_GEXF}")