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
import socket

def resolve_hostname(host: str) -> str:
    """Resolve hostname to IP address. Returns the IP if already an IP, or resolves hostname."""
    try:
        # Check if it's already an IP address
        ipaddress.ip_address(host)
        return host
    except ValueError:
        # It's a hostname, resolve it
        try:
            resolved_ip = socket.gethostbyname(host)
            return resolved_ip
        except socket.gaierror as e:
            raise ValueError(f"Could not resolve hostname '{host}': {e}")

def ping_ip(ip_or_host: str) -> dict:
    """Ping an IP address/hostname and return round-trip time statistics."""
    
    try:
        # Ping the hostname/IP (ping can handle both)
        response = ping(ip_or_host, count=10, interval=0.2, timeout=10, privileged=False)
        
        # Resolve hostname to IP for geolocation (ip_to_geo needs IP addresses)
        resolved_ip = ip_or_host  # Default to original if resolution fails
        distance = None
        location = None
        
        try:
            resolved_ip = resolve_hostname(ip_or_host)
            geo_data = ip_to_geo([resolved_ip])
            distance = geo_data.get(resolved_ip, {}).get('distance_km')
            location = geo_data.get(resolved_ip, {}).get('location')
        except Exception as geo_error:
            # If geolocation fails, continue without it
            print(f"Warning: Could not get geolocation for {ip_or_host}: {geo_error}")
        
        return {
            'ip': ip_or_host,
            'resolved_ip': resolved_ip,
            'min_rtt': response.min_rtt,
            'max_rtt': response.max_rtt,
            'avg_rtt': response.avg_rtt,
            'packet_loss': response.packet_loss,
            'geo_distance_km': distance,
            'location': location,
            'error': None
        }
    except Exception as e:
        # Handle nonresponsive servers or other errors
        return {
            'ip': ip_or_host,
            'resolved_ip': None,
            'min_rtt': None,
            'max_rtt': None,
            'avg_rtt': None,
            'packet_loss': None,
            'geo_distance_km': None,
            'location': None,
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
    
    # Save results to CSV file
    output_csv = 'ping_results.csv'
    results_df.to_csv(output_csv, index=False)
    print(f"\n# Results saved to {output_csv}")

if __name__ == '__main__':
    main()