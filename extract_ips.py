#!/usr/bin/env python3
"""
Script to extract IP addresses/hosts from listed_iperf3_servers.csv
and convert them to a Python list.
"""

import csv


def extract_ips_from_csv(csv_file: str) -> list[str]:
    """Read CSV file and extract IP/HOST column into a list."""
    ips = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            ip_host = row.get('IP/HOST', '').strip()
            if ip_host:  # Skip empty entries
                ips.append(ip_host)
    return ips


def main():
    csv_file = 'listed_iperf3_servers.csv'
    ips = extract_ips_from_csv(csv_file)
    
    # Print as a Python list
    print("# List of iperf3 server IPs/hosts")
    print(f"IPERF3_SERVERS = {ips}")
    print(f"\n# Total servers: {len(ips)}")


if __name__ == '__main__':
    main()
