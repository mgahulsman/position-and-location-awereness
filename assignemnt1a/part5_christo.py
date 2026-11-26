import csv
from pathlib import Path

import pyproj
from pyproj import Transformer

# Allow PROJ to download the RDNAPTRANS2018 grids (rdtrans2018 + nlgeo2018).
# Without them PROJ silently falls back to a "ballpark" transformation that
# leaves the height unchanged (no geoid correction) and is ~1 cm off in RD.
# Grids are cached locally after the first download.
pyproj.network.set_network_enabled(True)

CSV_PATH = Path(__file__).parent / "RTK_measurements" / "emma.csv"

# EPSG:4937 = ETRS89 geographic 3D (lat, lon, ellipsoidal height)
# EPSG:7415 = Amersfoort / RD New + NAP height (x, y, NAP height)
_ETRS89_TO_RDNAP = Transformer.from_crs("EPSG:4937", "EPSG:7415", always_xy=True)


def project_csv_to_rdnap(csv_path=CSV_PATH):
    """
    Read a ';'-separated csv with rows `id;lat;lon;h;` in EPSG:4937 and
    project every point to RD New + NAP (EPSG:7415).

    Returns a list of (id, x, y, nap_height) tuples, in the order of the csv.
    """
    points = []
    with open(csv_path, newline="", encoding="utf-8") as file:
        reader = csv.reader(file, delimiter=";")
        next(reader, None)  # skip the first row (VRS reference point)
        for row in reader:
            if len(row) < 4 or not row[0].strip():
                continue
            point_id = row[0].strip()
            lat, lon, h = float(row[1]), float(row[2]), float(row[3])
            # always_xy=True -> input order is (lon, lat, h), output (x, y, H)
            x, y, nap = _ETRS89_TO_RDNAP.transform(lon, lat, h)
            points.append((point_id, x, y, nap))
    return points


def triangle_area(p0, p1, p2):
    """Signed area of triangle (p0, p1, p2) using the 2D cross product."""
    return 0.5 * ((p1[0] - p0[0]) * (p2[1] - p0[1]) - (p2[0] - p0[0]) * (p1[1] - p0[1]))


def polygon_area(points):
    """
    Area of the polygon formed by consecutive points [(x, y), ...].

    The polygon is split into a fan of triangles (p0, p_i, p_i+1) all sharing
    the first vertex. Signed triangle areas are summed so that triangles lying
    outside a non-convex polygon cancel out; the absolute value is the area.
    """
    if len(points) < 3:
        raise ValueError("A polygon needs at least 3 points")
    p0 = points[0]
    total = 0.0
    for i in range(1, len(points) - 1):
        total += triangle_area(p0, points[i], points[i + 1])
    return abs(total)


if __name__ == "__main__":
    rd_points = project_csv_to_rdnap()
    for point_id, x, y, nap in rd_points:
        print(f"{point_id:>10}: x={x:.3f} y={y:.3f} NAP={nap:.3f}")

    polygon = [(x, y) for _, x, y, _ in rd_points]
    print(f"\nPolygon area ({len(polygon)} points): {polygon_area(polygon):.3f} m^2")

    # Imported here because part5_visualization imports from this file
    from part5_visualization import plot_projected_points_and_triangles
    plot_projected_points_and_triangles(rd_points)
