with open("C:\\Users\\maart\\EigenMappen\\Studie\\geomatics\\Q2-2026\\GEO1003\\assignment-position-and-location-awereness\\assignemnt1a\\data\\gnss_log_2026_11_13_11_56_20.nmea", "r", encoding="utf-8") as file:
    line_number = 0
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

        # Docs: https://community.surveyinghub.com/t/nmea-gpgga-messages/58
        elif line.startswith("NMEA,$GNGGA"):
                    parts = line.strip().split(",")
                    lat = parts[1]
                    lon = parts[3]
                    # TO be added: height
                    # Might be a good hint: Height of geoid above WGS84 ellipsoid is an attribute
                    print(f"line {line_number}: lat {lat}, lon {lon}")

        elif line.startswith("NMEA,$GNGSA"):
            parts = line.strip().split(",")
            pdop = parts[-3] # Weird dat 14 niet werkt, maar dit lijkt voor nu wel te kloppen
            hdop = parts[-2]
            vdop = parts[-1]
            print(f"line {line_number}: pdop {pdop}, hdop {hdop}, vdop {vdop}")
        line_number += 1
