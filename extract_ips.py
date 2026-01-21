#!/usr/bin/env python3
"""
Script to extract IP addresses/hosts from listed_iperf3_servers.csv
and convert them to a Python list and pandas DataFrame.
"""

import pandas as pd


def load_servers_dataframe(csv_file: str) -> pd.DataFrame:
    """Load CSV file into a pandas DataFrame."""
    df = pd.read_csv(csv_file)
    # Remove any rows with empty IP/HOST
    df = df[df['IP/HOST'].notna() & (df['IP/HOST'].str.strip() != '')]
    return df


def extract_ips_list(df: pd.DataFrame) -> list[str]:
    """Extract IP/HOST column as a Python list."""
    return df['IP/HOST'].tolist()


def main():
    csv_file = 'listed_iperf3_servers.csv'
    
    # Load into pandas DataFrame
    df = load_servers_dataframe(csv_file)
    
    # Extract IPs as a list
    ips = extract_ips_list(df)
    
    # Print as a Python list
    print("# List of iperf3 server IPs/hosts")
    print(f"IPERF3_SERVERS = {ips}")
    print(f"\n# Total servers: {len(ips)}")
    
    # Show DataFrame info
    print("\n# DataFrame Preview:")
    print(df.head(10))
    print(f"\n# DataFrame shape: {df.shape}")


if __name__ == '__main__':
    main()
