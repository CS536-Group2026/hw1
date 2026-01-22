#!/usr/bin/env python3
"""
Script to map IP addresses to their geographical locations using a GeoIP database.
Provides distance between West Lafayette, IN and the IP locations, in km

You need to "pip install requests"
"""
 
from collections import defaultdict
import requests
import time

    
# This function maps IPs to geo locations, including distance calculation from us to them
# 
# Example element
# IP 103.146.200.98: {'country': 'Papua New Guinea', 'regionName': 'National Capital', 'city': 'Port Moresby', 'lat': -9.43529, 3 # 'lon': 147.18, 'my_lat': 40.4444, 'my_lon': -86.9256, 'my_city': 'West Lafayette', 'my_region': 'Indiana', 'my_country': 'United # States', 'distance_km': 13691.116359279862}
# 
def ip_to_geo(ips):
    print("Mapping IP to geo location...")

    # Haversine formula to calculate distance between two lat/lon points in km
    # https://en.wikipedia.org/wiki/Haversine_formula
    def get_distance_km(my_lat, my_lon, dest_lat, dest_lon):
        from math import radians, sin, cos, sqrt, atan2
        R = 6371.0  # Earth radius in km

        # Convert degrees to radians
        my_lat, my_lon = radians(my_lat), radians(my_lon)
        dest_lat, dest_lon = radians(dest_lat), radians(dest_lon)

        # Haversine formula
        dlon = dest_lon - my_lon  # Δλ = λ₂ - λ₁
        dlat = dest_lat - my_lat  # Δφ = φ₂ - φ₁


        hav_dlat = sin(dlat / 2)**2 # hav(Δφ)
        hav_dlon = sin(dlon / 2)**2 # hav(Δλ)
        hav_angle = hav_dlat + cos(my_lat) * cos(dest_lat) * hav_dlon

        angle = 2 * atan2(sqrt(hav_angle), sqrt(1 - hav_angle)) # angle = 2 * arcsin(√hav(angle))

        distance = R * angle # This will get distance in km
        return distance

    # Request ip info from ip-api.com, it sleeps 1.5 sec to avoid rate limitation, it returns json data
    def request_api_info(ip):
        url = f'http://ip-api.com/json/{ip}'
        try:
            response = requests.get(url)
            data = response.json()
            return data
        except Exception as e:
            print(f"Error fetching data for IP {ip}: {e}")
            return None
        finally:
            # Avoid limitation rate
            time.sleep(1.5) 

    # Get our own IP geo location, it uses ipify.org to get public IP
    def get_my_public_ip():
        try:
            response = requests.get('https://api.ipify.org', timeout=5)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"Failed to get public IP: {e}")
            return None
    
    # Get ip using our function
    my_ip = get_my_public_ip()
    if my_ip is None:
        print("We need a valid public IP to calculate distance.")
        return None
    # Get geo info for our public IP
    my_geo = request_api_info(my_ip)
    
    if my_geo is None or my_geo['status'] != 'success':
        print("We need geo info for our public IP.")
        return None
    
    if 'lat' not in my_geo or 'lon' not in my_geo:
        print("We need coordinates for our public IP.")
        return None
    
    my_lat = my_geo['lat']
    my_lon = my_geo['lon']
    my_city = my_geo.get('city', 'West Lafayette')
    my_region = my_geo.get('regionName', 'IN')
    my_country = my_geo.get('country', 'USA')
    print(f"Our location: {my_city}, {my_region}, {my_country} ({my_lat}, {my_lon})")

    # Start processing IPs
    print("##############")
    print("Processing IPs...")

    # Dictionary to hold IP to geo info mapping [ip -> {geo info}]
    # ip should be unique
    map = defaultdict(dict)

    # Populate the map
    for ip in ips:
        if ip is None: continue
        data = request_api_info(ip)
        if data and data['status'] == 'success':
            if ip in map: continue  # Skip if already processed
            map[ip]['country'] = data.get('country', 'N/A')
            map[ip]['regionName'] = data.get('regionName', 'N/A')
            map[ip]['city'] = data.get('city', 'N/A')
            map[ip]['lat'] = data.get('lat', 'N/A')
            map[ip]['lon'] = data.get('lon', 'N/A')

            # Get distance from West Lafayette, IN to IP location
            map[ip]['my_lat'] = my_lat
            map[ip]['my_lon'] = my_lon
            map[ip]['my_city'] = my_city
            map[ip]['my_region'] = my_region
            map[ip]['my_country'] = my_country
            distance = get_distance_km(my_lat, my_lon, map[ip]['lat'], map[ip]['lon'])
            map[ip]['distance_km'] = distance
            print(f"IP {ip}: {map[ip]}")
        else:
            print(f"Failed to get data for IP {ip}: {data.get('message', 'error')}")
            return None
    print("##############")
    print("Total IPs processed:", len(map))
    return map




def main():
    # Getting ip from extract_ips.py
    from extract_ips import extract_ips_list, load_servers_dataframe
    csv_file = 'listed_iperf3_servers.csv'
    ips = extract_ips_list(load_servers_dataframe(csv_file))

    # Map IPs to geo locations, call this function to get all info
    ip_to_geo(ips)




if __name__ == '__main__':
    main()