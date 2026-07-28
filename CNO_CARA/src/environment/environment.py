"""
src/network/environment.py

builds a network graph of hospitals, clinics, and candidate hubs


"""

from matplotlib.patches import Rectangle


# unfeasible rectangles: (xmin, xmax, ymin, ymax)
NO_FLY_ZONES = [
    (0, 20, 60, 100),
    (20, 80, 80, 100),
]


def in_any_unfeasible(x, y, rects):
    for xmin, xmax, ymin, ymax in rects:
        if (xmin <= x <= xmax) and (ymin <= y <= ymax):
            return True
    return False


class Environment:

    def filter_candidate_hubs(network):
        filtered = []

        for hub in network.get_nodes("CandidateHub"):

            x, y = network.get_position(hub)

            if not in_any_unfeasible(x, y, NO_FLY_ZONES):
                filtered.append(hub)

        return filtered


    def draw_unfeasible(ax, rects):
        for idx, (xmin, xmax, ymin, ymax) in enumerate(rects):

            # draw shaded rectangle
            ax.add_patch(
                Rectangle(
                    (xmin, ymin),
                    xmax - xmin,
                    ymax - ymin,
                    fill        = True,
                    alpha       = 0.6,
                    linewidth   = 1.2,
                    edgecolor   = "black",
                    facecolor   = "gray",
                    zorder      = 0
                )
            )

            # decide rotation: second rectangle vertical
            rotation = 90 if idx == 0 else 1

            ax.text(
                (xmin + xmax) / 2,
                (ymin + ymax) / 2,
                "Infeasible Region",
                ha                  = "center",
                va                  = "center",
                rotation            = rotation,
                fontsize            = 11,
                bbox                = dict(facecolor="white", alpha=0.6, edgecolor="none")
            )