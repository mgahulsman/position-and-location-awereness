from filter import extract_lists, nmea_to_degrees

elaz_list, latlon_list, DOP_list = extract_lists("assignemnt1a\\RTK_measurements\\part 1 bouwpub 1m.nmea")

latsum = 0
lonsum = 0
total = 0

for point in latlon_list:
    latsum += nmea_to_degrees(point.lat)
    lonsum += nmea_to_degrees(point.lon)
    total += 1

latavg = latsum / total
lonavg = lonsum / total

print("the average lat and lon are", latavg, lonavg)