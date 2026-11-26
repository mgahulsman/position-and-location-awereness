import csv
import json
import os
import subprocess
from urllib.request import Request, urlopen

from geometry import Point

NSGI_URL = "https://api.transformation.nsgi.nl/v2/transform"


def read_csv(csv_path):
    # returns names and (lat, lon, h) of the points, skipping the first row (VRS point)
    names, coords = [], []
    with open(csv_path) as f:
        reader = csv.reader(f, delimiter=";")
        next(reader)
        for row in reader:
            if len(row) < 4:
                continue
            names.append(row[0])
            coords.append((float(row[1]), float(row[2]), float(row[3])))
    return names, coords


def proj_transform(coords, source="EPSG:4937", target="EPSG:7415"):
    # Uses the cs2cs program from PROJ (https://proj.org, install with `brew install proj`).
    # EPSG:4937 = ETRS89 (lat, lon, h), EPSG:7415 = RD New + NAP (x, y, H).
    # PROJ_NETWORK=ON lets PROJ download the RDNAPTRANS2018 grids if they are missing,
    # otherwise the NAP height is wrong.
    text = "\n".join(f"{a} {b} {c}" for a, b, c in coords) + "\n"
    env = dict(os.environ, PROJ_NETWORK="ON")
    result = subprocess.run(["cs2cs", "-f", "%.6f", source, target],
                            input=text, capture_output=True, text=True, env=env, check=True)
    return [tuple(float(v) for v in line.split()) for line in result.stdout.splitlines()]


def nsgi_transform(coords, source="4937", target="7415", api_key=None):
    # Uses the NSGI Coordinate Transformation API (RDNAPTRANS2018):
    # https://www.nsgi.nl/coordinatenstelsels-en-transformaties/tools/transformatie-api
    # Needs an API key, request one at
    # https://formulieren.kadaster.nl/aanvragen-coordinatentransformatie-api
    # and set it as the NSGI_API_KEY environment variable (or pass api_key).
    # coords are (lat, lon, h); GeoJSON wants (lon, lat, h) so they are swapped here.
    api_key = api_key or os.environ.get("NSGI_API_KEY")
    if not api_key:
        raise RuntimeError("no API key: set the NSGI_API_KEY environment variable")

    # all points in one FeatureCollection, so only one request
    body = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat, h]},
             "properties": {"i": i}}
            for i, (lat, lon, h) in enumerate(coords)
        ],
    }
    request = Request(NSGI_URL, data=json.dumps(body).encode(), method="POST", headers={
        "apikey": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "content-crs": f"http://www.opengis.net/def/crs/EPSG/0/{source}",
        "accept-crs": f"http://www.opengis.net/def/crs/EPSG/0/{target}",
    })
    with urlopen(request, timeout=30) as response:
        result = json.load(response)

    features = sorted(result["features"], key=lambda f: f["properties"]["i"])
    return [tuple(f["geometry"]["coordinates"]) for f in features]


def project_csv_to_rdnap(csv_path, method="proj"):
    # returns a list of Points in RD New, z = NAP height
    # method: "proj" (local cs2cs) or "nsgi" (transformation API)
    names, coords = read_csv(csv_path)
    transform = {"proj": proj_transform, "nsgi": nsgi_transform}[method]
    return [Point(x, y, nap, name) for name, (x, y, nap) in zip(names, transform(coords))]
