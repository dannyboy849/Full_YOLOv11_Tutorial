"""
src/visualization/plots.py

organizes data into the shapes utils/plots.py expects,
then calls each plot function in sequence

four-panel energy figure:
  1. Instantaneous power [W]
  2. State of Charge [%]
  3. Cumulative energy [Wh]
  4. Estimated remaining endurance [min]

called by: DATUM.py  (after evaluate_model)

"""

import numpy                as np
import pandas               as pd
import random 
import networkx             as nx
import matplotlib           as mpl
import matplotlib.pyplot    as plt

from pathlib                    import Path
from network.network            import euclidean_distance, draw_unfeasible, filtered_hubs, UNFEASIBLE
from control.mpc_train          import _save, COLORS
from network.generate_network   import coords, chosen, grid_points, talihina, durant, G, pos


# ----------------------------
# style setup (LaTeX-like fonts)
# ----------------------------
mpl.rcParams.update({
    "text.usetex": False,
    "font.family": "serif",
    "font.serif": ["DejaVu Serif"],
    "axes.labelsize": 13,
    "axes.titlesize": 14,
    "legend.fontsize": 11,
})


def _plot_energy_full(results, dT, Tsim, bat_mah, v_nominal, save_dir):
    """
    four-panel energy figure:
      1. Instantaneous power [W]
      2. State of Charge [%]
      3. Cumulative energy [Wh]
      4. Estimated remaining endurance [min]
    """
    time        = np.arange(Tsim) * dT
    fig, axes   = plt.subplots(2, 2, figsize=(14, 8))
    axes        = axes.flatten()

    titles      = ['Instantaneous Power (W)', 'State of Charge (%)',
               'Cumulative Energy (Wh)',   'Est. Remaining Endurance (min)']
    keys        = ['power_hist', 'soc_hist', 'energy_hist', 'endurance_hist']
    scales      = [1.0, 100.0, 1/3600.0, 1/60.0]   # unit conversions

    # theoretical full endurance line
    Q_j         = bat_mah / 1000.0 * v_nominal * 3600.0

    for ax, title, key, sc in zip(axes, titles, keys, scales):

        for name, res in results.items():
            arr = res.get(key, np.zeros(1)) * sc
            n   = min(len(arr), Tsim)
            ax.plot(time[:n], arr[:n],
                    color=COLORS.get(name, 'purple'), lw=1.5, label=name)
        ax.set_title(title, fontsize=10)
        ax.set_xlabel('Time (s)', fontsize=9)
        ax.grid(True, alpha=0.35)
        ax.legend(fontsize=8)

    # annotate endurance panel with battery capacity
    axes[3].axhline(Q_j/60.0, color='red', lw=0.8, ls='--',
                    label=f'Full capacity ({bat_mah/1000:.0f}Ah)')
    axes[3].legend(fontsize=8)

    # print summary
    print(f"\n{'─'*55}")
    print(f"{'Controller':<26} {'ΔEndurance(min)':>16} {'Energy(Wh)':>12}")
    print(f"{'─'*55}")

    plt.suptitle(f'Energy Analysis — {bat_mah/1000:.0f}Ah / '
                 f'{v_nominal}V LiPo Battery', fontsize=12)
    plt.tight_layout()
    _save(fig, save_dir, 'MPC_energy_analysis')
    print("[hub_placement] Energy analysis plot saved.")



# --------------------------------------------------
# ── MPC tracking plots ───────────────────────────
# --------------------------------------------------

def _plot_tracking(results, ref_traj, state_vars, dT, Tsim, save_dir):
    n_show = len(state_vars) 
    time   = np.arange(Tsim) * dT
    fig, axes = plt.subplots(n_show, 1, figsize=(12, n_show*1.8), sharex=True)

    if n_show == 1:
        axes = [axes]

    for i in range(n_show):
        ax = axes[i]
        n_ref = min(len(ref_traj), Tsim)
        ax.plot(time[:n_ref], ref_traj[:n_ref, i],
                'r--', lw=1.5, label='Reference', alpha=0.7)
        
        for name, res in results.items():
            xh = res['x_hist']
            n  = min(len(xh), Tsim)
            
            if i < xh.shape[1]:
                ax.plot(time[:n], xh[:n, i],
                        color=COLORS.get(name, 'purple'),
                        lw=1.2, alpha=0.85, label=name)
        
        ax.set_ylabel(state_vars[i], fontsize=9)
        ax.grid(True, alpha=0.35)

        if i == 0:
            ax.legend(fontsize=8, loc='upper right', ncol=2)
    axes[-1].set_xlabel('Time (s)')
    plt.suptitle('HPO State Tracking', fontsize=12)
    plt.tight_layout()
    _save(fig, save_dir, 'MPC_state_tracking')
    print("[hub_placement] State tracking plot saved.")


    
# --------------------------------------------------
# ── error and motor plots ─────────────────────────
# --------------------------------------------------

def _save(fig, save_dir: Path, stem: str):

    for sub, ext in [('mpc_pdf', 'pdf'), ('mpc_png', 'png')]:
        d = save_dir / sub
        d.mkdir(parents=True, exist_ok=True)
        fig.savefig(d / f'{stem}.{ext}', dpi=600, bbox_inches='tight')
    plt.close(fig)


def _plot_rmse_table(results, ref_traj, state_vars):
    """print per-state RMSE table to console."""
    header = f"\n{'Method':<26}" + "".join(f"{s:>12}" for s in state_vars) \
             + f"{'Overall':>12}"
    print("="*len(header))
    print(header)
    print("="*len(header))

    for name, res in results.items():
        xh = res['x_hist']
        n  = min(len(xh), len(ref_traj))
        err_norm = (xh[:n] - ref_traj[:n])
        per_state = [
            float(np.sqrt(np.mean((xh[:n, j] - ref_traj[:n, j])**2)))
            for j in range(len(state_vars))
        ]
        overall = np.sqrt(np.mean(np.linalg.norm(err_norm, axis=1)**2))
        row = f"{name:<26}" + "".join(f"{v:>12.4f}" for v in per_state) \
            + f"{overall:>12.4f}"
        print(row)
    print("="*len(header))


def plot_wind_risk(
    wind_speed,
    risk_hist
):
    """plot wind risk over time."""
    time = np.arange(len(risk_hist))
    plt.figure(figsize=(10, 4))
    plt.plot(time, risk_hist, label='Wind Risk', color='orange')
    plt.axhline(0.0, color='gray', lw=0.5, ls='--')
    plt.title(f'Wind Risk Over Time (wind speed={wind_speed:.1f} m/s)')
    plt.xlabel('Time step')
    plt.ylabel('Risk')
    plt.grid(True, alpha=0.35)
    plt.legend()
    plt.tight_layout()
    plt.show()
    print("[hub_placement] Wind risk plot saved.")


def _plot_motors(results, input_vars, dT, Tsim, save_dir):
    """plot motor PWM commands for each controller side-by-side."""
    # use HPO as the primary; fallback to HPO-no-tight
    primary = results.get('HPO', results.get('HPO (no optimization)'))

    if primary is None:
        return
    u_dat  = primary['u_hist']
    n_u    = u_dat.shape[1]
    time   = np.arange(min(len(u_dat), Tsim)) * dT
    colors = ['steelblue', 'seagreen', 'firebrick', 'darkorchid']
    ncols  = 2
    nrows  = (n_u + 1) // ncols

    fig, axes = plt.subplots(nrows, ncols, figsize=(12, nrows*2.5),
                              sharex=True)
    axes = axes.flatten()

    for i in range(n_u):
        label = input_vars[i] if i < len(input_vars) else f'Motor {i+1}'
        n = min(len(u_dat), Tsim)
        axes[i].plot(time[:n], u_dat[:n, i],
                     color=colors[i % len(colors)], lw=1.2,
                     label='HPO')
        axes[i].set_ylabel(label, fontsize=8)
        axes[i].set_ylim([800, 2200])
        axes[i].axhline(1000, color='gray', lw=0.5, ls=':')
        axes[i].axhline(2000, color='gray', lw=0.5, ls=':')
        axes[i].axhline(1400, color='orange', lw=0.5, ls='--',
                         label='hover est.')
        axes[i].grid(True, alpha=0.35)
        axes[i].legend(fontsize=7)

    for j in range(n_u, len(axes)):
        axes[j].set_visible(False)
    axes[min(n_u-1, len(axes)-1)].set_xlabel('Time (s)')
    plt.suptitle('Motor PWM Commands', fontsize=11)
    plt.tight_layout()
    _save(fig, save_dir, 'MPC_motor_commands')
    print("[hub_placement] Motor commands plot saved.")
    


# -------------------------------
# clinic plots 
# -------------------------------

plt.figure(figsize=(7,7))

# Hospitals
plt.scatter(coords["Durant"][0], coords["Durant"][1], c="red", s=100, label="Hospitals")
plt.scatter(coords["Talihina"][0], coords["Talihina"][1], c="red", s=100)
plt.text(coords["Durant"][0]+2, coords["Durant"][1]+2, "Durant", fontsize=10)
plt.text(coords["Talihina"][0]+2, coords["Talihina"][1]+2, "Talihina", fontsize=10)

# Clinics
added = False
for name, p in chosen.items():
    if not added:
        plt.scatter(p[0], p[1], c="purple", s=70, label="Clinics")
        added = True
    else:
        plt.scatter(p[0], p[1], c="purple", s=70)
    plt.text(p[0]+2, p[1]+2, name, fontsize=9)

# Candidate hub grid (yellow open circles)
plt.scatter(
    grid_points[:,0],
    grid_points[:,1],
    c='goldenrod',      # dark yellow fill
    s=35,               # slightly smaller, tweak if needed
    label="Candidate hubs (20-mile grid)"
)

# Reference line between hospitals
plt.plot([durant[0], talihina[0]], [durant[1], talihina[1]], "--", lw=1)

plt.axis("equal")
plt.grid(True)
plt.xlabel("x (miles)")
plt.ylabel("y (miles)")
plt.title("Hospitals, Clinics, an"
          "d Potential Hubs")
plt.legend(loc='upper left', frameon='false')
# plt.show()


# Build coordinate table
node_type = []
x_list, y_list, name_list = [], [], []

for name, p in coords.items():
    if name in ["Durant", "Talihina"]:
        t = "Hospital"
    else:
        t = "Clinic"
    name_list.append(name)
    x_list.append(p[0])
    y_list.append(p[1])
    node_type.append(t)

# Optionally, add candidate hubs
for i, p in enumerate(grid_points):
    name_list.append(f"Hub_{i+1}")
    x_list.append(p[0])
    y_list.append(p[1])
    node_type.append("CandidateHub")

df_coords = pd.DataFrame({
    "Name": name_list,
    "Type": node_type,
    "x_miles": x_list,
    "y_miles": y_list
})

df_coords.to_csv("CNO_node_coordinates.csv", index=False)
print("✅ Saved coordinates to CNO_node_coordinates.csv")


# Example: expected daily specimen trips (clinic -> hospital)
clinic_demands = {
    "Idabel": {"Durant": 5, "Talihina": 2},
    "Broken Bow": {"Durant": 4, "Talihina": 3},
    "Hugo": {"Durant": 6, "Talihina": 1},
    "Atoka": {"Durant": 3, "Talihina": 3},
    "McAlester": {"Durant": 2, "Talihina": 5},
    "Poteau": {"Durant": 1, "Talihina": 4},
    "Stigler": {"Durant": 2, "Talihina": 3},
}

# Build OD matrix
clinics = [n for n in coords if n not in ["Durant", "Talihina"]]
hospitals = ["Durant", "Talihina"]
nodes = hospitals + clinics
D = pd.DataFrame(0, index=nodes, columns=nodes)

for c in clinics:
    for h in hospitals:
        d = clinic_demands[c][h]
        D.loc[c, h] = d       # clinic -> hospital
        D.loc[h, c] = d       # hospital -> clinic (return trip)

D.to_csv("CNO_demand_matrix.csv")
print("✅ Saved OD matrix to CNO_demand_matrix.csv")



# --------------------------------------------------
# ── hub placement plots ───────────────────────────
# --------------------------------------------------

# Data
data = [(4, 7903), (5, 6904), (6, 6773), (7, 6530),
        (8, 6512), (9, 6468), (10, 6451),
        (11, 6443), (12, 6440)]

# Separate x and y
N = [x for x, _ in data]
cost = [y for _, y in data]

# Plot
plt.figure(figsize=(7,5))
plt.plot(N, cost, marker='o', linewidth=2)

plt.xlabel("Number of Hubs (N)")
plt.ylabel("Traversal Cost of the Optimal Selection")
plt.title("Traversal Cost vs. Number of Hubs")
plt.grid(True, linestyle="--", alpha=0.5)

plt.tight_layout()
plt.savefig("cost_vs_hubs.png", dpi=300, bbox_inches="tight")
plt.savefig("cost_vs_hubs.pdf", bbox_inches="tight")
plt.show()


fig, ax = plt.subplots(figsize=(9, 9))

draw_unfeasible(ax, UNFEASIBLE)


# Draw edges (black thin lines)
# nx.draw_networkx_edges(G, pos, edge_color="black", width=0.5, arrows=False, alpha=0.6)

# Draw nodes
nx.draw_networkx_nodes(G, pos, nodelist=hospitals, node_color="red", node_size=110, label="Hospitals")
nx.draw_networkx_nodes(G, pos, nodelist=clinics, node_color="purple", node_size=50, label="Clinics")
# nx.draw_networkx_nodes(G, pos, nodelist=hubs, node_color="goldenrod", node_size=40, label="Candidate Hubs")
# nx.draw_networkx_nodes(G, pos, nodelist=filtered_hubs, node_color="goldenrod", node_size=40, label="Candidate Hubs", ax=ax)

# Optional: label a few key nodes (e.g., hospitals and clinics)
for name in hospitals + clinics:
    x, y = pos[name]
    ax.text(x + 2, y + 2, name, fontsize=12)

# plt.axis("equal")
ax.grid(True)

# plt.title("CNO Drone Network (≤40-mile connectivity)")
ax.set_title("Locations of Clinics and Hospitals")
# plt.legend(loc="upper left", bbox_to_anchor=(1.02, 1), frameon=False)
ax.legend(loc="upper left")

# plt.axis("equal")
ax.set_xlabel("x (miles)")
ax.set_ylabel("y (miles)")

plt.locator_params(axis='both', nbins=8)
plt.tick_params(labelsize=12)

ax.set_xlim(-10, 150)
ax.set_ylim(-25, 120)

#Turn ticks ON explicitly
ax.tick_params(axis='both', which='both',
               bottom=True, top=False,
               left=True, right=False,
               labelbottom=True, labelleft=True)

# Let matplotlib choose nice tick locations
ax.xaxis.set_major_locator(plt.MaxNLocator(8))
ax.yaxis.set_major_locator(plt.MaxNLocator(8))

# plt.axis("equal")
ax.grid(True)
# plt.tight_layout()
fig.savefig("initial_points.png", dpi=300, bbox_inches="tight")
plt.show()


# Files
COORDS_CSV = "CNO_node_coordinates.csv"
GRAPH_GEXF = "CNO_graph_within_40mi.gexf"
SEL_HUBS   = "MCF_selected_hubs.csv"
NZFLOWS    = "MCF_nonzero_flows.csv"

# Load
df_nodes = pd.read_csv(COORDS_CSV)
G = nx.read_gexf(GRAPH_GEXF)
pos = {row["Name"]: (row["x_miles"], row["y_miles"]) for _, row in df_nodes.iterrows()}
types = {row["Name"]: row["Type"] for _, row in df_nodes.iterrows()}

sel = pd.read_csv(SEL_HUBS)["SelectedHubs"].tolist()
flows = pd.read_csv(NZFLOWS)  # columns: commodity, i, j, flow, cost_miles

# Aggregate flow per (i,j) across commodities
edge_flow = flows.groupby(["i","j"])["flow"].sum().reset_index()

# Node groups
hospitals = [n for n in G.nodes if types.get(n) == "Hospital"]
clinics   = [n for n in G.nodes if types.get(n) == "Clinic"]
hubs_all  = [n for n in G.nodes if types.get(n) == "CandidateHub"]
hubs_sel  = [n for n in hubs_all if n in sel]
hubs_uns  = [n for n in hubs_all if n not in sel]

# Plot
plt.figure(figsize=(9,9))

# Draw only edges with positive total flow (black), thickness ∝ flow
for _, r in edge_flow.iterrows():
    i, j, f = r["i"], r["j"], r["flow"]
    if i in pos and j in pos:
        x = [pos[i][0], pos[j][0]]
        y = [pos[i][1], pos[j][1]]
        lw = 0.5 + 1.5 * (f / edge_flow["flow"].max())  # scale width
        plt.plot(x, y, color="black", linewidth=lw, alpha=0.7)

# Nodes
plt.scatter([pos[n][0] for n in hospitals], [pos[n][1] for n in hospitals],
            c="red", s=110, label="Hospitals")
plt.scatter([pos[n][0] for n in clinics], [pos[n][1] for n in clinics],
            c="purple", s=80, label="Clinics")

# # Unselected hubs (dark yellow small)
# plt.scatter([pos[n][0] for n in hubs_uns], [pos[n][1] for n in hubs_uns],
#             c="goldenrod", s=35, label="Candidate hubs")

# Selected hubs (bigger with black edge)
plt.scatter([pos[n][0] for n in hubs_sel], [pos[n][1] for n in hubs_sel],
            c="goldenrod", edgecolors="black", linewidths=0.7, s=120, label="Selected hubs")

# Label hospitals/clinics lightly
for n in hospitals + clinics:
    x, y = pos[n]
    plt.text(x+2, y+2, n, fontsize=12)

plt.gca().set_aspect("equal", adjustable="box")


plt.grid(True)
plt.xlabel("x (miles)", fontsize=14)
plt.ylabel("y (miles)", fontsize=14)
plt.title("Optimal flows and selected hubs",  fontsize=14)
plt.legend(loc="upper left", fontsize=14)
plt.tight_layout()
plt.xlim(-10, 150)
plt.ylim(-25, 120)
plt.savefig("optimal_flows_N_4.png", dpi=300, bbox_inches="tight")
plt.show()

random.seed(42)  # reproducible sampling (recommended for papers)

num_samples = 7
num_hubs_to_plot = 8

for i in range(num_samples):
    sampled_hubs = random.sample(filtered_hubs, num_hubs_to_plot)

    # ---- Save sample to CSV for later use ----
    df_sample = pd.DataFrame({
        "Name": sampled_hubs,
        "x_miles": [pos[n][0] for n in sampled_hubs],
        "y_miles": [pos[n][1] for n in sampled_hubs],
    })
    df_sample.to_csv(f"sampled_hubs_{i+1}.csv", index=False)



    # ---- Plot ----
    fig, ax = plt.subplots(figsize=(9, 9))

    draw_unfeasible(ax, UNFEASIBLE)

    # Nodes currently visible in this figure
    current_nodes = hospitals + clinics + sampled_hubs

    # Draw edges if distance < 50 miles
    for idx1 in range(len(current_nodes)):
        for idx2 in range(idx1 + 1, len(current_nodes)):
            n1 = current_nodes[idx1]
            n2 = current_nodes[idx2]

            if euclidean_distance(pos[n1], pos[n2]) < 45:
                x_values = [pos[n1][0], pos[n2][0]]
                y_values = [pos[n1][1], pos[n2][1]]

                ax.plot(x_values, y_values,
                        color="black",
                        linewidth=0.7,
                        alpha=0.5,
                        zorder=1)

    nx.draw_networkx_nodes(G, pos, nodelist=hospitals, node_color="red", node_size=110, label="Hospitals", ax=ax)
    nx.draw_networkx_nodes(G, pos, nodelist=clinics,   node_color="purple", node_size=50, label="Clinics", ax=ax)
    # nx.draw_networkx_nodes(G, pos, nodelist=sampled_hubs, node_color="goldenrod", node_size=80,
    #                        label="Sampled Candidate Hubs", ax=ax)
    nx.draw_networkx_nodes(G, pos, nodelist=sampled_hubs, node_color="goldenrod", node_size=80,
                             label="Hubs", ax=ax)
    for name in hospitals + clinics:
        x, y = pos[name]
        ax.text(x + 2, y + 2, name, fontsize=12)

    # ax.set_title(f"Selection {i+1} of Candidate Hubs")
    ax.set_xlabel("x (miles)")
    ax.set_ylabel("y (miles)")

    # Use same limits as initial plot for visual comparability (recommended)
    ax.set_xlim(-10, 150)
    ax.set_ylim(-25, 120)

    ax.xaxis.set_major_locator(plt.MaxNLocator(8))
    ax.yaxis.set_major_locator(plt.MaxNLocator(8))
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend(loc="upper left")

    fig.savefig(f"initial_points_sample_{i+1}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)