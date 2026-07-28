"""
src/planning/mcf_solver.py

this solves the multi-commodity flow problem for hub placement optimization

"""

import pulp   as pl
import pandas as pd


# sets

def solve_mcf(network, ranked_hubs):

    N       = network.nodes["Name"].tolist()
    types   = dict(zip(network.nodes["Name"], network.nodes["Type"]))
    H       = [n for n in N if types[n] == "CandidateHub"]
    R       = [n for n in N if types[n] in ("Hospital", "Clinic")]
    # arc set and costs
    E       = [(row.origin, row.destination) for _, row in network.edges.iterrows()]
    c       = {(row.origin, row.destination): float(row.cost_miles) for _, row in network.edges.iterrows()}

    # --------------------------
    # build commodities K from D matrix:
    # clinic -> hospital and hospital -> clinic (return)
    # strictly positive demands
    # --------------------------
    K   = []
    Dk  = {}
    for o in N:
        for d in N:
            if o == d:
                continue
            dem = float(network.Dmat.loc[o, d]) if (o in network.Dmat.index and d in network.Dmat.columns) else 0.0
            if dem > 0:
                K.append((o, d))
                Dk[(o, d)] = dem



    # --------------------------
    # model
    # --------------------------
    m = pl.LpProblem("Hub_Placement_MCF", pl.LpMinimize)

    # decision vars
    y = {i: pl.LpVariable(f"y_{i}", lowBound=0, upBound=1, cat=pl.LpBinary) for i in H}
    # required nodes fixed active: represent as constants via a helper (lambda returns 1)


    def y_active(i):
        return 1 if i in R else y[i]

    # flow variables f[k,i,j] for all commodities k and arcs (i,j)
    f = {}
    for (ok, dk) in K:
        for (i, j) in E:
            f[(ok, dk, i, j)] = pl.LpVariable(f"f_{ok}__{dk}__{i}_{j}", lowBound=0, cat=pl.LpContinuous)

    # objective: sum_k sum_(i,j) c_ij f^k_{ij}
    m += pl.lpSum(c[(i, j)] * f[(ok, dk, i, j)] for (ok, dk) in K for (i, j) in E)

    # hub budget
    m += pl.lpSum(y[i] for i in H) <= network.HUB_BUDGET, "Hub_Budget"

    # flow balance per commodity
    # sum_in - sum_out = {-Dk at source, +Dk at sink, 0 otherwise}
    for (ok, dk) in K:
        D = Dk[(ok, dk)]
        for i in N:
            inflow  = pl.lpSum(f[(ok, dk, j, i)] for (j, i2) in E if i2 == i)
            outflow = pl.lpSum(f[(ok, dk, i, j)] for (i2, j) in E if i2 == i)
            rhs = 0
            if i == ok: rhs = -D
            elif i == dk: rhs = D
            m += (inflow - outflow == rhs), f"FlowBal_{ok}_{dk}_{i}"

    # low-activation linking (tight big-M: Dk)
    for (ok, dk) in K:
        D = Dk[(ok, dk)]
        for (i, j) in E:
            # f^k_{ij} <= Dk * y_i  and  <= Dk * y_j
            # (y_i/y_j = 1 for hospitals/clinics; binary only for hubs)
            m += f[(ok, dk, i, j)] <= D * (y_active(i)), f"LinkY_i_{ok}_{dk}_{i}_{j}"
            m += f[(ok, dk, i, j)] <= D * (y_active(j)), f"LinkY_j_{ok}_{dk}_{i}_{j}"

    # Optional: forbid pass-through at clinics/hospitals (if desired)
    # Uncomment to only allow transit via hubs (origins/dests still okay)
    # for i in R:
    #     for (ok, dk) in K:
    #         if i not in (ok, dk):
    #             inflow  = pl.lpSum(f[(ok, dk, j, i)] for (j, i2) in E if i2 == i)
    #             outflow = pl.lpSum(f[(ok, dk, i, j)] for (i2, j) in E if i2 == i)
    #             m += inflow + outflow == 0, f"NoTransit_{ok}_{dk}_{i}"

    # solve
    m.solve(pl.PULP_CBC_CMD(msg=True))

    print("Status:", pl.LpStatus[m.status])
    print("Objective (miles * flow):", pl.value(m.objective))


    # write results

    # selected hubs
    sel_hubs = []
    for i in H:
        if pl.value(y[i]) > 0.5:
            sel_hubs.append(i)
    pd.Series(sel_hubs, name="SelectedHubs").to_csv("MCF_selected_hubs.csv", index=False)
    print("Selected hubs:", sel_hubs)

    # nonzero flows (compact)
    rows = []
    for (ok, dk) in K:
        for (i, j) in E:
            val = pl.value(f[(ok, dk, i, j)])
            if val is not None and val > 1e-6:
                rows.append({"commodity": f"{ok}->{dk}", "i": i, "j": j, "flow": val, "cost_miles": c[(i, j)]})
    pd.DataFrame(rows).to_csv("MCF_nonzero_flows.csv", index=False)
    print("Saved: MCF_selected_hubs.csv, MCF_nonzero_flows.csv")