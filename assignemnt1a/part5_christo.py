from pathlib import Path

import matplotlib.pyplot as plt

from geometry import Polygon, Triangulation
from part5_visualization import plot_projected_points, plot_triangles
from projection import project_csv_to_rdnap

CSV_PATH = Path(__file__).parent / "RTK_measurements" / "emma.csv"


def polygon_area(polygon):
    return sum(t.area() for t in Triangulation.triangulate(polygon))


def polygon_perimeter(polygon):
    return sum(edge.length() for edge in polygon.edges())


if __name__ == "__main__":
    points = project_csv_to_rdnap(CSV_PATH, method="proj")  # or method="nsgi" for the NSGI API
    for p in points:
        print(f"{p.name}: x={p.x:.3f} y={p.y:.3f} NAP={p.z:.3f}")

    polygon = Polygon(points)
    print(f"\narea: {polygon_area(polygon):.3f} m2")
    print(f"perimeter: {polygon_perimeter(polygon):.3f} m")
    print(f"average height: {sum(p.z for p in polygon.points) / len(polygon.points):.3f} m NAP")

    # one plt.show() for both plots, calling it twice gives a SystemError on mac
    triangles = Triangulation.triangulate(polygon)
    plot_projected_points([(p.name, p.x, p.y, p.z) for p in points], show=False)
    plot_triangles([t.coords() for t in triangles], title="Delaunay triangulation", show=False)
    plt.show()
