#!/usr/bin/env python3
"""
Script to ping IP addresses/hosts from Python list
and report min, max, and average round-trip times.
"""
import pandas as pd
from icmplib import ping
from extract_ips import extract_ips_list, load_servers_dataframe
from geo_ips import ip_to_geo
import ipaddress

def ping_ip(ip: str) -> dict:
    """Ping an IP address/host and return round-trip time statistics."""
    
    try:
        ipaddress.ip_address(ip)
        response = ping(ip, count=10, interval=0.2, timeout=10, privileged=False)
        geo_data = ip_to_geo([ip])
        distance = geo_data.get(ip, {}).get('distance_km')
        return {
            'ip': ip,
            'min_rtt': response.min_rtt,
            'max_rtt': response.max_rtt,
            'avg_rtt': response.avg_rtt,
            'packet_loss': response.packet_loss,
            'geo_distance_km': distance,
            'error': None
        }
    except Exception as e:
        # Handle nonresponsive servers or other errors
        return {
            'ip': ip,
            'min_rtt': None,
            'max_rtt': None,
            'avg_rtt': None,
            'packet_loss': None,
            'geo_distance_km': None,
            'error': str(e)
        }
    
def ping_all_ips(ips: list[str]) -> list[dict]:
    """Ping all IP addresses/hosts in the list and return their statistics."""
    results = []
    for ip in ips:
        stats = ping_ip(ip)
        results.append(stats)
    return results


def main():
    csv_file = 'listed_iperf3_servers.csv'
    
    # Load into pandas DataFrame
    df = load_servers_dataframe(csv_file)
    
    # Extract IPs as a list
    ips = extract_ips_list(df)
    
    results = ping_all_ips(ips)
    for result in results:
        if result['error']:
            print(f"IP {result['ip']} - Error: {result['error']}")
        else:
            print(f"IP {result['ip']} - Min RTT: {result['min_rtt']} ms, Max RTT: {result['max_rtt']} ms, "
                  f"Avg RTT: {result['avg_rtt']} ms, Packet Loss: {result['packet_loss']}%, "
                  f"Geo Distance: {result['geo_distance_km']} km")

    # Convert results to DataFrame for better visualization if needed
    results_df = pd.DataFrame(results)
    print("\n# Ping Results DataFrame Preview:")
    print(results_df.head(10))
    print(f"\n# Ping Results DataFrame shape: {results_df.shape}")

if __name__ == '__main__':
    main()