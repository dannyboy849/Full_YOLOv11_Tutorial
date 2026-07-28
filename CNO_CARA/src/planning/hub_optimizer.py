"""
src/planning/hub_optimizer.py

this uses Dijkstra's algorithm to find every possible hub placement
preferred over A* since it only finds the shortest

"""

import time
import math
import numpy        as np
import pandas       as pd
import networkx     as nx
import plotly.graph_objects as go

from hub_placement          import EdgeProxy  # Connects 2D map miles directly to FAA Lat/Lon grids
from scipy.optimize         import minimize
from planning.mcf_solver    import solve_mcf


def optimize_hub_placement_dispersed(network, weather, airspace, candidate_hubs, target_hub_count=7):
    """selects a spatially diverse subset of hubs enforcing a 40-mile zone"""
    hospitals = network.get_nodes(node_type="Hospital")
    clinics = network.get_nodes(node_type="Clinic")
    t_routing_start = time.perf_counter()
    
    print(f"[hub_placement] Executing Multi-Hub Allocation for {target_hub_count} spatially diverse sites...")
    candidate_costs = {}
    
    for _, hub_row in candidate_hubs.iterrows():
        hub_name = hub_row['Name']
        candidate_costs[hub_name] = {
            "total_energy_wh": 0.0, 
            "total_airspace_penalty": 0.0,
            "mean_tracking_risk": 0.0,
            "feasible": True, 
            "coords": (hub_row['x_miles'], hub_row['y_miles'])
        }

        risk_samples = []
        for clinic in clinics:
            for hospital in hospitals:
                try:
                    route = network.route_via_hub(clinic, hub_name, hospital)
                    trip_demand = network.Dmat.loc[clinic, hospital] if clinic in network.Dmat.index else 1.0
                    
                    edges = list(zip(route[:-1], route[1:]))
                    combined_trip_energy_wh = 0.0

                    for u, v in edges:
                        pos_u = network.get_position(u)
                        pos_v = network.get_position(v)
                        
                        # 1. Evaluate Local Airspace Restrictions via your FAA GIS Layer proxy
                        proxy_edge = EdgeProxy(pos_u[0], pos_v[0])
                        if airspace is not None:
                            airspace_report = airspace.evaluate(proxy_edge, vehicle_altitude_ft=400.0)
                            candidate_costs[hub_name]["total_airspace_penalty"] += airspace_report["penalty"] * trip_demand
                        
                        # 2. Evaluate Localized Wind Rose Scenarios and Frequencies
                        wind_cases = weather.representative_cases(position=pos_u)
                        case_energies = []
                        for vec in wind_cases:
                            leg_energy = weather.evaluate_mpc_edge_cost(
                                (u, v), vec, ["takeoff", "midflight", "cruise", "landing"]
                            )
                            case_energies.append(leg_energy)
                            
                        if not all(np.isfinite(case_energies)):
                            candidate_costs[hub_name]["feasible"] = False
                            break
                            
                        combined_trip_energy_wh += np.mean(case_energies)
                        risk_samples.append(float(np.linalg.norm(vec)))
                        
                    if not candidate_costs[hub_name]["feasible"]:
                        break
                        
                    candidate_costs[hub_name]["total_energy_wh"] += (combined_trip_energy_wh * trip_demand)
                    
                except nx.NetworkXNoPath:
                    candidate_costs[hub_name]["feasible"] = False
                    break
            if not candidate_costs[hub_name]["feasible"]:
                break

    valid_candidates = {k: v for k, v in candidate_costs.items() if v["feasible"]}
    selected_hubs = []
    MIN_DISTANCE_MILES = 30.0
    
    sorted_candidates = sorted(valid_candidates.items(), key=lambda item: item[1]["total_energy_wh"])
    
    for hub_name, data in sorted_candidates:
        if len(selected_hubs) >= target_hub_count:
            break
        x1, y1 = data["coords"]
        
        too_close = False
        for selected_name in selected_hubs:
            x2, y2 = valid_candidates[selected_name]["coords"]
            distance = math.sqrt((x1 - x2)**2 + (y1 - y2)**2)
            if distance < MIN_DISTANCE_MILES:
                too_close = True
                break
                
        if not too_close:
            selected_hubs.append(hub_name)
            
    final_rows = [
        {
            'Hub_Name': name,
            'x_miles': valid_candidates[name]["coords"][0],
            'y_miles': valid_candidates[name]["coords"][1],
            'Total_Daily_Energy_Wh': valid_candidates[name]["total_cost"]
        }
        for name in selected_hubs
    ]

    final_rows = []
    cumulative_energy = 0.0
    
    for rank_idx, name in enumerate(selected_hubs):
        local_energy = valid_candidates[name]["total_energy_wh"]
        cumulative_energy += local_energy # Cumulatively adding best to last
        
        final_rows.append({
            'Rank':                  rank_idx + 1,
            'Hub_Name':              name,
            'x_miles':               float(valid_candidates[name]["coords"][0]),
            'y_miles':               float(valid_candidates[name]["coords"][1]),
            'Incremental_Energy_Wh': float(local_energy),
            'Cumulative_Energy_Wh':  float(cumulative_energy),
            'Airspace_Penalty':      float(valid_candidates[name]["total_airspace_penalty"]),
            'Safety_Risk_Factor':    float(valid_candidates[name]["mean_tracking_risk"])
        })
    
    elapsed_routing = time.perf_counter() - t_routing_start
    print(f"[hub_placement] Finished dispersed sweeps in {elapsed_routing:.2f} seconds.")
    return pd.DataFrame(final_rows)


# this is still buggy, but underway. prints out non-real number (likely euclidean issue)
# also, not needed for Phase 1 of the project, tbd for Phase 2
def continuous_network_loss(coords, network, weather):
    """objective function forcing 40-mile constraints over fractional coordinates"""
    hubs = coords.reshape(-1, 2)
    total_system_wh = 0.0

    hospitals = network.get_nodes(node_type="Hospital")
    clinics = network.get_nodes(node_type="Clinic")

    node_locs = {
        "Durant": (3.0, 3.0), "Talihina": (95.253, 62.910),
        "Idabel": (105.532, -14.409), "Broken Bow": (109.859, -2.478),
        "Hugo": (59.402, -5.234), "Atoka": (28.334, 31.322),
        "McAlester": (45.686, 69.474), "Poteau": (131.553, 70.074), "Stigler": (86.231, 108.016)
    }
    
    for clinic in clinics:
        c_pos = node_locs.get(clinic, (50.0, 50.0))
        for hospital in hospitals:
            h_pos = node_locs.get(hospital, (50.0, 50.0))
            trip_demand = network.Dmat.loc[clinic, hospital] if clinic in network.Dmat.index else 1.0

            if trip_demand == 0:
                continue
            distances_to_hubs = [math.sqrt((hub[0] - c_pos[0])**2 + (hub[1] - c_pos[1])**2) for hub in hubs]
            best_idx = np.argmin(distances_to_hubs)
            assigned_hub = hubs[best_idx]
         
            leg_1_dist = distances_to_hubs[best_idx]
            leg_2_dist = math.sqrt((assigned_hub[0] - h_pos[0])**2 + (assigned_hub[1] - h_pos[1])**2)
            
            if leg_1_dist > 40.0 or leg_2_dist > 40.0:
                return 1e12  
                
            wind_cases = weather.representative_cases(position=assigned_hub)

            case_energies = []
            for vec in wind_cases:
                wh_1 = weather.evaluate_mpc_edge_cost((clinic, f"ch_{best_idx}"), vec, ["cruise"])
                wh_2 = weather.evaluate_mpc_edge_cost((f"ch_{best_idx}", hospital), vec, ["cruise"])
                case_energies.append(wh_1 + wh_2)
                
            total_system_wh += np.mean(case_energies) * trip_demand

    return total_system_wh



# --------------------------------------------------
# ── main system  ──────────────────────────────────
# --------------------------------------------------

class HubOptimizer:

    def __init__(self, network, weather, environment):
        self.network = network
        self.weather = weather
        self.environment = environment
        self.filtered_names = self.environment.filter_candidate_hubs(self.network)

    def optimize(self, mode="dispersed", target_count=7):
        t_global_start = time.perf_counter()

        if mode == "dispersed":
            valid_rows = []
            for name in self.filtered_names:
                if hasattr(self.network, 'candidate_hubs'):
                    df_src = self.network.candidate_hubs
                    matching_data = df_src[df_src['Name'] == name]
                    if not matching_data.empty:
                        valid_rows.append(matching_data.iloc[0].to_dict())
            
            df_validated_candidates = pd.DataFrame(valid_rows)
            if df_validated_candidates.empty:
                print("[STRATEGIC ERROR] Zero candidate hubs parsed inside environment parameters.")
                return pd.DataFrame()

            ranked = optimize_hub_placement_dispersed(self.network, self.weather, df_validated_candidates)

            try:
                selected_distribution = solve_mcf(network=self.network.G, ranked_hubs=ranked)
                print("[STRATEGIC PLANNER] Multi-Commodity Flow routing solver executed successfully.")
            except KeyError:
                selected_distribution = ranked

            # generate interactive infrastructure network plot
            print("[STRATEGIC PLANNER] Exporting interactive facility grid layout...")
            pos_map = self.network.node_positions
            type_map = self.network.node_types
            top_hubs = list(ranked.head(target_count)["Hub_Name"].values) if not ranked.empty else []

            node_groups = {
                "Hospital":     {"x": [], "y": [], "text": [], "color": "crimson", "size": 14, "symbol": "square"},
                "Clinic":       {"x": [], "y": [], "text": [], "color": "teal",    "size": 11, "symbol": "circle"},
                "Candidate":    {"x": [], "y": [], "text": [], "color": "darkgray","size": 8,  "symbol": "diamond"},
                "Optimal Site": {"x": [], "y": [], "text": [], "color": "gold",    "size": 15, "symbol": "star"}
            }

            for node_name, pos in pos_map.items():
                raw_type = type_map.get(node_name, "CandidateHub")
                g_key = "Hospital" if raw_type == "Hospital" else ("Clinic" if raw_type == "Clinic" else ("Optimal Site" if node_name in top_hubs else "Candidate"))
                node_groups[g_key]["x"].append(pos[0])
                node_groups[g_key]["y"].append(pos[1])
                node_groups[g_key]["text"].append(f"{node_name} ({g_key})")

            fig_net = go.Figure()
            for label, group in node_groups.items():
                if group["x"]:
                    fig_net.add_trace(go.Scatter(
                        x=group["x"], y=group["y"], mode='markers+text' if label != "Candidate" else 'markers',
                        text=group["text"] if label != "Candidate" else None, textposition="top center",
                        hoverinfo="text", name=label,
                        marker=dict(color=group["color"], size=group["size"], symbol=group["symbol"], line=dict(width=1, color="black"))
                    ))

            # no-fly zones
            no_fly_rects = [(0, 20, 60, 100), (20, 80, 80, 100)]
            for xmin, xmax, ymin, ymax in no_fly_rects:
                fig_net.add_shape(type="rect", x0=xmin, x1=xmax, y0=ymin, y1=ymax, fillcolor="gray", opacity=0.35, line=dict(width=1, color="black", dash="dash"), layer="below")

            fig_net.update_layout(title=f"CARA Network: Mode={mode.upper()} Optimization", xaxis=dict(title="X (Miles)", gridcolor="lightgray"), yaxis=dict(title="Y (Miles)", gridcolor="lightgray"), plot_bgcolor="white", width=1100, height=850)
            fig_net.write_html("plots/network/strategic_hub_allocation_grid.html")
            return selected_distribution

        else:
            print(f"[Continuous-Opt] Locating {target_count} un-gridded hubs...")
            
            # seed initialization coordinates spread evenly across the geographic span
            np.random.seed(42)
            initial_guess = np.random.uniform(10.0, 110.0, size=(target_count, 2)).flatten()
            
            # establish boundary boxes to clip variables inside regional borders
            spatial_bounds = [(0.0, 140.0), (-20.0, 120.0)] * target_count
            
            # run the continuous gradient descent minimization solver
            res = minimize(
                fun=continuous_network_loss, x0=initial_guess,
                args=(self.network, self.weather),
                method='L-BFGS-B', bounds=spatial_bounds, options={'maxiter': 50}
            )
            
            optimized_coords = res.x.reshape(-1, 2)
            hospitals = self.network.get_nodes(node_type="Hospital")
            clinics = self.network.get_nodes(node_type="Clinic")
            
            hub_isolated_costs = {f"Continuous_Hub_{i+1}": 0.0 for i in range(target_count)}
            node_locs = {
                "Durant": (3.0, 3.0), "Talihina": (95.253, 62.910),
                "Idabel": (105.532, -14.409), "Broken Bow": (109.859, -2.478),
                "Hugo": (59.402, -5.234), "Atoka": (28.334, 31.322),
                "McAlester": (45.686, 69.474), "Poteau": (131.553, 70.074), "Stigler": (86.231, 108.016)
            }      

            # run one final evaluation pass to distribute exact costs to the nearest assigned hub
            for clinic in clinics:
                c_pos = node_locs.get(clinic, (50.0, 50.0)) 
                for hospital in hospitals:
                    h_pos = node_locs.get(hospital, (50.0, 50.0))
                    trip_demand = self.network.Dmat.loc[clinic, hospital] if clinic in self.network.Dmat.index else 1.0
                    
                    distances = [
                        math.sqrt((h[0] - c_pos[0])**2 + (h[1] - c_pos[1])**2) +  # Leg 1: Clinic to Hub
                        math.sqrt((h[0] - h_pos[0])**2 + (h[1] - h_pos[1])**2)    # Leg 2: Hub to Hospital
                        for h in optimized_coords
                    ]
                    
                    best_idx = np.argmin(distances)
                    assigned_hub_name = f"Continuous_Hub_{best_idx+1}"
                    assigned_hub_pos = optimized_coords[best_idx]
                    
                    wind_cases = self.weather.representative_cases(position=assigned_hub_pos)
                    case_energies = []
                    for vec in wind_cases:
                        wh_1 = self.weather.evaluate_mpc_edge_cost((clinic, assigned_hub_name), vec, ["cruise"])
                        wh_2 = self.weather.evaluate_mpc_edge_cost((assigned_hub_name, hospital), vec, ["cruise"])
                        case_energies.append(wh_1 + wh_2)
                        
                    # attribute the flight energy directly to the chosen infrastructure node
                    hub_isolated_costs[assigned_hub_name] += np.mean(case_energies) * trip_demand

            # reconstruct the final clean DataFrame with distinct, un-cloned energy costs
            final_rows = [
                {
                    "Hub_Name": f"Continuous_Hub_{i+1}",
                    "x_miles": float(optimized_coords[i][0]),
                    "y_miles": float(optimized_coords[i][1]),
                    "Total_Daily_Energy_Wh": float(hub_isolated_costs[f"Continuous_Hub_{i+1}"])
                }
                for i in range(target_count)
            ]
            
            df_continuous = pd.DataFrame(final_rows).sort_values(by='Total_Daily_Energy_Wh').reset_index(drop=True)
            total_optimizer_time = time.perf_counter() - t_global_start

            print(f"[TIMING] Hub Optimization (CONTINUOUS) completed in: {total_optimizer_time:.2f} seconds.")
            fig_net.update_layout(title=f"CARA Network: Mode={mode.upper()} Optimization", xaxis=dict(title="X (Miles)", gridcolor="lightgray"), yaxis=dict(title="Y (Miles)", gridcolor="lightgray"), plot_bgcolor="white", width=1100, height=850)
            fig_net.write_html("plots/network/strategic_hub_allocation_grid.html")
            return df_continuous