import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Polygon

from part5_christo import polygon_area, project_csv_to_rdnap, triangle_area


def plot_projected_points_and_triangles(rd_points, ax=None, show=True, save_path=None):
    """
    Plot the projected RD points, the polygon they form and the fan of
    triangles (p0, p_i, p_i+1) used by `polygon_area`.

    Triangles whose signed area has the same sign as the total (they add area)
    are green; triangles with the opposite sign (they subtract the area that
    lies outside a non-convex polygon) are red. Overlaps show the cancelling.

    rd_points: list of (id, x, y, nap_height) as returned by project_csv_to_rdnap.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 8))

    ids = [p[0] for p in rd_points]
    xy = [(p[1], p[2]) for p in rd_points]
    p0 = xy[0]

    # Fan triangles. A triangle adds area when its signed area has the same
    # sign as the polygon's total (i.e. same orientation, cw or ccw).
    triangles = [[p0, xy[i], xy[i + 1]] for i in range(1, len(xy) - 1)]
    signed = [triangle_area(*tri) for tri in triangles]
    orientation = 1 if sum(signed) >= 0 else -1
    for tri, area in zip(triangles, signed):
        adds = area * orientation >= 0
        ax.add_patch(Polygon(
            tri, closed=True,
            facecolor="tab:green" if adds else "tab:red",
            edgecolor="grey", linewidth=0.6, alpha=0.25,
        ))

    # Polygon outline
    xs = [p[0] for p in xy] + [p0[0]]
    ys = [p[1] for p in xy] + [p0[1]]
    ax.plot(xs, ys, color="black", linewidth=1.5, label="Polygon outline")

    # Points and labels
    ax.scatter(xs[:-1], ys[:-1], color="tab:blue", zorder=3, label="Projected points")
    ax.scatter(*p0, color="tab:orange", s=80, zorder=4, label=f"Fan origin ({ids[0]})")
    for point_id, (x, y) in zip(ids, xy):
        ax.annotate(point_id, (x, y), textcoords="offset points", xytext=(4, 4), fontsize=8)

    handles, _ = ax.get_legend_handles_labels()
    handles += [
        Patch(facecolor="tab:green", alpha=0.25, label="Triangle, added (+)"),
        Patch(facecolor="tab:red", alpha=0.25, label="Triangle, subtracted (−)"),
    ]
    ax.legend(handles=handles, loc="best", fontsize=8)

    ax.set_title(f"Projected points (EPSG:7415) — area = {polygon_area(xy):.2f} m²")
    ax.set_xlabel("RD x [m]")
    ax.set_ylabel("RD y [m]")
    ax.set_aspect("equal")
    ax.ticklabel_format(useOffset=False, style="plain")
    ax.grid(True, linewidth=0.3)

    if save_path:
        ax.figure.savefig(save_path, dpi=150, bbox_inches="tight")
    if show:
        plt.show()
    return ax


if __name__ == "__main__":
    plot_projected_points_and_triangles(project_csv_to_rdnap())
