import io
import logging
from urllib.parse import urlencode
from urllib.request import urlopen

import matplotlib.pyplot as plt
from matplotlib.patches import Polygon

# Free the arrow keys (by default left/right = back/forward in the view history)
for _key in ("left", "right"):
    for _keymap in ("keymap.back", "keymap.forward"):
        if _key in plt.rcParams[_keymap]:
            plt.rcParams[_keymap].remove(_key)

# With adjustable="datalim" matplotlib widens one axis to keep equal scale
# (intended here, so the map fills the window) and logs a warning about it
logging.getLogger("matplotlib.axes._base").addFilter(
    lambda record: "fulfill fixed data aspect" not in record.getMessage()
)

PAN_STEP = 0.1    # fraction of the current view moved per arrow key press
ZOOM_FACTOR = 1.2  # zoom per scroll step / +/- key press

# OpenBasiskaart: OpenStreetMap based base map served in RD New (EPSG:28992)
OBK_WMS_URL = "https://www.openbasiskaart.nl/mapcache/wms"
OBK_LAYER = "osm-hq"
OBK_ATTRIBUTION = "Map: openbasiskaart.nl · Data © OpenStreetMap contributors"

def triangle_area(p0, p1, p2):
    """Signed area of triangle (p0, p1, p2) using the 2D cross product."""
    return 0.5 * ((p1[0] - p0[0]) * (p2[1] - p0[1]) - (p2[0] - p0[0]) * (p1[1] - p0[1]))


def fetch_openbasiskaart(bbox, width, height, layer=OBK_LAYER):
    """
    Download an OpenBasiskaart image for bbox = (xmin, ymin, xmax, ymax) in
    RD New (EPSG:28992). Returns an RGB(A) image array.
    """
    params = urlencode({
        "SERVICE": "WMS", "VERSION": "1.1.1", "REQUEST": "GetMap",
        "LAYERS": layer, "STYLES": "", "SRS": "EPSG:28992",
        "BBOX": ",".join(f"{v:.3f}" for v in bbox),
        "WIDTH": int(width), "HEIGHT": int(height), "FORMAT": "image/png",
    })
    with urlopen(f"{OBK_WMS_URL}?{params}", timeout=15) as response:
        return plt.imread(io.BytesIO(response.read()), format="png")


def add_basemap(ax, layer=OBK_LAYER, margin=0.5, max_pixels=2048):
    """
    Draw the OpenBasiskaart behind everything on `ax` (which must be in RD
    coordinates). The map covers the current view plus `margin` (fraction of
    the view) on every side, and is downloaded again after panning/zooming so
    it stays sharp. If the download fails the plot is shown without a map.
    """
    fig = ax.figure
    state = {"image": None, "busy": False}

    def refresh():
        if state["busy"]:
            return
        state["busy"] = True
        try:
            ax.apply_aspect()  # apply equal aspect first, so the limits are final
            xlim, ylim = ax.get_xlim(), ax.get_ylim()
            w, h = xlim[1] - xlim[0], ylim[1] - ylim[0]
            bbox = (xlim[0] - margin * w, ylim[0] - margin * h,
                    xlim[1] + margin * w, ylim[1] + margin * h)

            # Pixel size: match the screen resolution of the axes, capped
            extent_px = ax.get_window_extent()
            scale = 1 + 2 * margin
            px_w, px_h = extent_px.width * scale, extent_px.height * scale
            shrink = min(1.0, max_pixels / max(px_w, px_h))
            px_w, px_h = max(1, px_w * shrink), max(1, px_h * shrink)

            try:
                img = fetch_openbasiskaart(bbox, px_w, px_h, layer)
            except Exception as err:
                print(f"OpenBasiskaart could not be loaded: {err}")
                return

            if state["image"] is not None:
                state["image"].remove()
            state["image"] = ax.imshow(
                img, extent=(bbox[0], bbox[2], bbox[1], bbox[3]),
                origin="upper", zorder=0, interpolation="bilinear",
            )
            # imshow would otherwise change the view to the whole image
            ax.set_xlim(xlim)
            ax.set_ylim(ylim)
            fig.canvas.draw_idle()
        finally:
            state["busy"] = False

    # Reload the map shortly after the view stops changing
    timer = fig.canvas.new_timer(interval=300)
    timer.single_shot = True
    timer.add_callback(refresh)

    def on_view_change(_ax):
        if not state["busy"]:
            timer.stop()
            timer.start()

    ax.callbacks.connect("xlim_changed", on_view_change)
    ax.callbacks.connect("ylim_changed", on_view_change)

    ax.text(0.99, 0.01, OBK_ATTRIBUTION, transform=ax.transAxes, fontsize=6,
            ha="right", va="bottom", color="dimgrey", zorder=5,
            bbox=dict(facecolor="white", alpha=0.6, edgecolor="none", pad=1))
    # Fix the current view (computed from the data) before turning autoscale off
    ax.set_xlim(ax.get_xlim())
    ax.set_ylim(ax.get_ylim())
    ax.set_autoscale_on(False)
    refresh()
    ax._basemap_timer = timer  # keep a reference so the timer is not garbage collected
    return ax


def enable_navigation(ax):
    """
    Add keyboard and mouse navigation to a plot:
      - arrow keys:         move left / right / up / down
      - scroll wheel:       zoom in / out around the mouse cursor
      - '+' / '=' and '-':  zoom in / out around the centre of the view
      - 'r' or 'h':         reset to the original view (matplotlib default)
    Click-and-drag panning and box zoom are still available via the toolbar.
    """
    fig = ax.figure

    def zoom(scale, cx, cy):
        x0, x1 = ax.get_xlim()
        y0, y1 = ax.get_ylim()
        ax.set_xlim(cx - (cx - x0) * scale, cx + (x1 - cx) * scale)
        ax.set_ylim(cy - (cy - y0) * scale, cy + (y1 - cy) * scale)
        fig.canvas.draw_idle()

    def pan(dx_frac, dy_frac):
        x0, x1 = ax.get_xlim()
        y0, y1 = ax.get_ylim()
        dx, dy = (x1 - x0) * dx_frac, (y1 - y0) * dy_frac
        ax.set_xlim(x0 + dx, x1 + dx)
        ax.set_ylim(y0 + dy, y1 + dy)
        fig.canvas.draw_idle()

    def on_scroll(event):
        if event.inaxes is not ax:
            return
        scale = 1 / ZOOM_FACTOR if event.button == "up" else ZOOM_FACTOR
        zoom(scale, event.xdata, event.ydata)

    def on_key(event):
        moves = {
            "left": (-PAN_STEP, 0), "right": (PAN_STEP, 0),
            "up": (0, PAN_STEP), "down": (0, -PAN_STEP),
        }
        if event.key in moves:
            pan(*moves[event.key])
        elif event.key in ("+", "=", "-"):
            x0, x1 = ax.get_xlim()
            y0, y1 = ax.get_ylim()
            scale = ZOOM_FACTOR if event.key == "-" else 1 / ZOOM_FACTOR
            zoom(scale, (x0 + x1) / 2, (y0 + y1) / 2)

    fig.canvas.mpl_connect("scroll_event", on_scroll)
    fig.canvas.mpl_connect("key_press_event", on_key)
    return ax


def _new_axes():
    """Create a figure whose axes fill the whole window, with navigation enabled."""
    fig, ax = plt.subplots(figsize=(8, 8))
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    return enable_navigation(ax)


def _style_map_axes(ax, title):
    """
    Map style: no x/y axes and no white margins. The axes fill the whole
    figure (equal scale is kept by extending the data limits instead of
    shrinking the axes box), and the title is drawn inside the plot.
    """
    ax.set_aspect("equal", adjustable="datalim")
    ax.set_axis_off()

    old = getattr(ax, "_overlay_title", None)
    if old is not None:
        old.remove()
    ax._overlay_title = ax.text(
        0.5, 0.99, title, transform=ax.transAxes, fontsize=11,
        ha="center", va="top", zorder=6,
        bbox=dict(facecolor="white", alpha=0.75, edgecolor="none", pad=3),
    )
    manager = ax.figure.canvas.manager
    if manager is not None:
        manager.set_window_title(title)


def _save(ax, save_path):
    ax.figure.savefig(save_path, dpi=150, pad_inches=0)


def plot_projected_points(rd_points, ax=None, show=True, save_path=None, basemap=True):
    """
    Plot only the projected RD points (no polygon or triangles), each labelled
    with its point id.

    rd_points: list of (id, x, y, nap_height) as returned by project_csv_to_rdnap.
    """
    if ax is None:
        ax = _new_axes()

    xs = [p[1] for p in rd_points]
    ys = [p[2] for p in rd_points]
    ax.scatter(xs, ys, color="tab:blue", zorder=3)
    for point_id, x, y, _ in rd_points:
        ax.annotate(point_id, (x, y), textcoords="offset points", xytext=(4, 4), fontsize=8)

    _style_map_axes(ax, f"Projected points (EPSG:7415) — {len(rd_points)} points")
    if basemap:
        add_basemap(ax)

    if save_path:
        _save(ax, save_path)
    if show:
        plt.show()
    return ax


def plot_triangles(triangles, ax=None, show=True, save_path=None, title=None, basemap=True):
    """
    Plot a list of triangles, each a tuple of three (x, y) points (e.g. the
    output of `triangulate_ear_clipping`). Each triangle gets its own colour
    and is numbered in list order at its centroid.
    """
    if ax is None:
        ax = _new_axes()

    cmap = plt.get_cmap("tab20")
    for k, tri in enumerate(triangles):
        ax.add_patch(Polygon(
            tri, closed=True, facecolor=cmap(k % 20),
            edgecolor="grey", linewidth=0.6, alpha=0.5,
        ))
        cx = sum(p[0] for p in tri) / 3
        cy = sum(p[1] for p in tri) / 3
        ax.text(cx, cy, str(k + 1), fontsize=7, ha="center", va="center", color="dimgrey")

    # add_patch does not update the axis limits, so set them from the vertices
    ax.update_datalim([p for tri in triangles for p in tri])
    ax.autoscale_view()

    total = sum(abs(triangle_area(*tri)) for tri in triangles)
    _style_map_axes(ax, title or f"{len(triangles)} triangles, total area = {total:.2f} m²")
    if basemap:
        add_basemap(ax)

    if save_path:
        _save(ax, save_path)
    if show:
        plt.show()
    return ax
