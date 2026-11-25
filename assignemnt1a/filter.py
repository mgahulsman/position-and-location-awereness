"""
Dilution of Precision (DOP) Reference & Interpretation.

Dilution of Precision (DOP) is a dimensionless multiplier describing how the
geometric arrangement of visible GNSS satellites affects positioning accuracy.
It depends purely on satellite geometry rather than signal strength or
atmospheric interference (Position Error ≈ DOP * UERE). Lower values indicate
better geometry and higher precision.

DOP Metrics (parsed from NMEA $GNGSA sentences):
    - PDOP (Position DOP): Overall 3D accuracy (sqrt(HDOP^2 + VDOP^2)).
    - HDOP (Horizontal DOP): 2D horizontal accuracy (latitude and longitude).
    - VDOP (Vertical DOP): 1D altitude accuracy; typically higher than HDOP
      because satellites are only observable above the horizon.
    - TDOP (Time DOP): Receiver clock synchronization precision.
    - GDOP (Geometric DOP): Combined 3D position and time precision
      (sqrt(PDOP^2 + TDOP^2)).

Interpretation Thresholds:
    - < 1: Ideal (maximum confidence; satellites spread evenly across the sky).
    - 1–2: Excellent (reliable for surveying, mapping, and open-sky tracking).
    - 2–5: Good (dependable for general navigation and standard GIS tasks).
    - 5–10: Moderate (noticeable precision drop; suitable for rough tracking).
    - 10–20: Poor (clustered satellite geometry, e.g., urban canyons).
    - > 20: Unusable (geometry too weak; fixes should be discarded).

$GN stands for smartphone measurement
$GNGSA: describe the geometry of all the satellites used in the fix, not of GPS alone
"""
from dataclasses import dataclass


@dataclass
class GPGSV:
    elevation: float
    azimuth: float


@dataclass
class GNGGA:
    lat: float
    lon: float


@dataclass
class GNGSA:
    pdop: float
    hdop: float
    vdop: float
    

def structure_data():
    # NOTE: this 
    with open("assignemnt1a\\data\\gnss_log_2026_11_13_11_56_20.nmea", "r", encoding="utf-8") as file:
        line_number = 0
        lat_lon_pairs: list[tuple[float, float]] = []

        GPGSV_list: list[GPGSV] = []
        GNGGA_list: list[GNGGA] = []
        GNGSA_list: list[GNGSA] = []
        
        for line in file:
            # Docs: https://community.surveyinghub.com/t/nmea-gpgsv-messages/61
            if line.startswith("NMEA,$GPGSV"):        
                        parts = line.strip().split(",")
                        elevation = parts[4]
                        if int(elevation) > 90:
                            raise ValueError("Wrong attribute, elevation has max. 90 degrees")
                        azimuth = parts[5]
                        in_range_azimuth = (0 <= int(azimuth) < 360)
                        if not in_range_azimuth:
                            raise ValueError("Wrong attribute, azimuth should be in between 0 and 360 degrees.")
                        print(f"line {line_number}: elevation {elevation}, azimuth {azimuth}")
                        GPGSV_list.append(GPGSV(elevation=elevation, azimuth=azimuth))

            # Docs: https://community.surveyinghub.com/t/nmea-gpgga-messages/58
            elif line.startswith("NMEA,$GNGGA"):
                        parts = line.strip().split(",")
                        lat = parts[3]
                        lon = parts[5]
                        lat_lon_pairs.append(((lat, lon)))
                        # TO be added: height
                        # Might be a good hint: Height of geoid above WGS84 ellipsoid is an attribute
                        print(f"line {line_number}: lat {lat}, lon {lon}")
                        GNGGA_list.append(GNGGA(lat=lat, lon=lon))

            elif line.startswith("NMEA,$GNGSA"):
                parts = line.strip().split(",")
                pdop = parts[-3] # Weird dat 14 niet werkt, maar dit lijkt voor nu wel te kloppen
                hdop = parts[-2]
                vdop = parts[-1]
                print(f"line {line_number}: pdop {pdop}, hdop {hdop}, vdop {vdop}")
                GNGSA_list.append(GNGSA(pdop=pdop, hdop=hdop, vdop=vdop))
            line_number += 1

        return (GPGSV_list, GNGGA_list, GNGSA_list) 

# use functions like this 
def extract_something():
    """
    Write a function like this to extract data from your file which you can use in your own part.
    """
    data = structure_data()
    # do something with the data and import this function in your own file
    return data

# try
extract_something()