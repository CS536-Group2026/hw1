#!/usr/bin/env python3
"""
Script to find round-trip times to intermediate hops using traceroute.
Picks 5 random IP addresses and traces the path to each destination.
"""

import subprocess
import re
import random
import csv
import sys
import platform
from typing import List, Dict, Tuple, Optional
from extract_addrs import load_servers_dataframe, extract_addrs_list


def run_traceroute(ip: str, max_hops: int = 30, timeout: int = 1) -> str:
    """
    Run traceroute command for the given IP address.
    
    Args:
        ip: Destination IP address
        max_hops: Maximum number of hops to trace
        timeout: Timeout in milliseconds for each hop
    
    Returns:
        Raw traceroute output as string
    """
    system = platform.system().lower()
    
    try:
        if system == 'windows':
            # Windows tracert command
            cmd = ['tracert', '-h', str(max_hops), '-w', str(timeout), ip]
        else:
            # Unix/Linux traceroute command
            cmd = ['traceroute', '-m', str(max_hops), '-w', str(timeout // 1000), ip]
        
        print(f"Running traceroute to {ip}...")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120  # Overall timeout of 2 minutes
        )
        return result.stdout
    
    except subprocess.TimeoutExpired:
        print(f"Warning: Traceroute to {ip} timed out")
        return ""
    except FileNotFoundError:
        print(f"Error: Traceroute command not found. Make sure it's installed.")
        return ""
    except Exception as e:
        print(f"Error running traceroute to {ip}: {e}")
        return ""


def parse_traceroute_windows(output: str, destination_ip: str) -> List[Dict[str, any]]:
    """
    Parse Windows tracert output.
    
    Windows tracert format:
    1    <1 ms    <1 ms    <1 ms  192.168.1.1
    2     *        *        *     Request timed out.
    3    10 ms    11 ms    12 ms  10.0.0.1
    
    Args:
        output: Raw traceroute output
        destination_ip: Destination IP being traced
    
    Returns:
        List of hop dictionaries with hop_number, hop_ip, and rtt values
    """
    hops = []
    lines = output.split('\n')
    
    # Pattern to match tracert lines with IP addresses and RTT values
    # Matches lines like: "  1    <1 ms    <1 ms    <1 ms  192.168.1.1"
    # or "  3    10 ms    11 ms    12 ms  10.0.0.1 [10.0.0.1]"
    hop_pattern = re.compile(
        r'^\s*(\d+)\s+' +  # Hop number
        r'(?:(<?\d+)\s*ms|[\*\?])\s+' +  # First RTT (or * for timeout)
        r'(?:(<?\d+)\s*ms|[\*\?])\s+' +  # Second RTT
        r'(?:(<?\d+)\s*ms|[\*\?])\s+' +  # Third RTT
        r'(?:([^\s]+(?:\s+\[[^\]]+\])?))?',  # IP or hostname
        re.IGNORECASE
    )
    
    # Alternative pattern for timeout lines
    timeout_pattern = re.compile(
        r'^\s*(\d+)\s+[\*\?]\s+[\*\?]\s+[\*\?]\s+(?:Request timed out|[\*\?])',
        re.IGNORECASE
    )
    
    for line in lines:
        # Try to match normal hop line
        match = hop_pattern.match(line)
        if match:
            hop_num = int(match.group(1))
            rtt1 = match.group(2)
            rtt2 = match.group(3)
            rtt3 = match.group(4)
            hop_addr = match.group(5) if match.group(5) else None
            
            # Extract IP address if present
            if hop_addr:
                # Clean up hostname/IP (remove brackets and extra text)
                hop_addr = hop_addr.strip()
                # Extract IP from format like "hostname [ip]"
                ip_match = re.search(r'\[([^\]]+)\]', hop_addr)
                if ip_match:
                    hop_addr = ip_match.group(1)
                elif ' ' in hop_addr:
                    # If there's a space, take the last part (likely IP)
                    parts = hop_addr.split()
                    # Try to find which part looks like an IP
                    for part in reversed(parts):
                        if re.match(r'\d+\.\d+\.\d+\.\d+', part):
                            hop_addr = part
                            break
                
                # Parse RTT values (filter out None and convert)
                rtts = []
                for rtt in [rtt1, rtt2, rtt3]:
                    if rtt:
                        # Handle "<1" format
                        if rtt.startswith('<'):
                            rtts.append(0.5)  # Use 0.5 ms for <1 ms
                        else:
                            try:
                                rtts.append(float(rtt))
                            except ValueError:
                                pass
                
                # Only add hop if we have valid RTT values
                if rtts and hop_addr:
                    avg_rtt = sum(rtts) / len(rtts)
                    min_rtt = min(rtts)
                    max_rtt = max(rtts)
                    
                    hops.append({
                        'destination_ip': destination_ip,
                        'hop_number': hop_num,
                        'hop_ip': hop_addr,
                        'min_rtt': min_rtt,
                        'max_rtt': max_rtt,
                        'avg_rtt': avg_rtt
                    })
    
    return hops


def parse_traceroute_unix(output: str, destination_ip: str) -> List[Dict[str, any]]:
    """
    Parse Unix/Linux traceroute output.
    
    Unix traceroute format:
    1  192.168.1.1 (192.168.1.1)  0.5 ms  0.3 ms  0.2 ms
    2  * * *
    3  10.0.0.1 (10.0.0.1)  10.1 ms  10.2 ms  10.3 ms
    
    Args:
        output: Raw traceroute output
        destination_ip: Destination IP being traced
    
    Returns:
        List of hop dictionaries with hop_number, hop_ip, and rtt values
    """
    hops = []
    lines = output.split('\n')
    
    # Pattern to match traceroute lines
    hop_pattern = re.compile(
        r'^\s*(\d+)\s+' +  # Hop number
        r'(?:([^\s\(]+)\s+)?' +  # Optional hostname
        r'(?:\(([^\)]+)\))?' +  # IP in parentheses
        r'(.+)$'  # Rest of line with RTTs
    )
    
    for line in lines:
        match = hop_pattern.match(line)
        if match:
            hop_num = int(match.group(1))
            hostname = match.group(2)
            ip_addr = match.group(3)
            rtt_part = match.group(4)
            
            # If line has only asterisks, skip it
            if '*' in line and not ip_addr:
                continue
            
            # Extract RTT values
            rtt_matches = re.findall(r'([\d\.]+)\s*ms', rtt_part)
            
            if rtt_matches and ip_addr:
                rtts = [float(r) for r in rtt_matches]
                avg_rtt = sum(rtts) / len(rtts)
                min_rtt = min(rtts)
                max_rtt = max(rtts)
                
                hops.append({
                    'destination_ip': destination_ip,
                    'hop_number': hop_num,
                    'hop_ip': ip_addr,
                    'min_rtt': min_rtt,
                    'max_rtt': max_rtt,
                    'avg_rtt': avg_rtt
                })
    
    return hops


def parse_traceroute_output(output: str, destination_ip: str) -> List[Dict[str, any]]:
    """
    Parse traceroute output based on the operating system.
    
    Args:
        output: Raw traceroute output
        destination_ip: Destination IP being traced
    
    Returns:
        List of hop dictionaries
    """
    if not output:
        return []
    
    system = platform.system().lower()
    
    if system == 'windows':
        return parse_traceroute_windows(output, destination_ip)
    else:
        return parse_traceroute_unix(output, destination_ip)


def select_random_ips(num_ips: int = 5) -> List[str]:
    """
    Select random IP addresses from the iperf3 server list.
    
    Args:
        num_ips: Number of random IPs to select
    
    Returns:
        List of IP addresses
    """
    print("Loading iperf3 server list...")
    df = load_servers_dataframe()
    addrs = extract_addrs_list(df)
    
    # Filter to get only valid IPs (not hostnames)
    # Simple check: contains dots and starts with a digit
    ip_pattern = re.compile(r'^\d+\.\d+\.\d+\.\d+$')
    valid_ips = [addr for addr in addrs if ip_pattern.match(addr)]
    
    print(f"Found {len(valid_ips)} valid IP addresses")
    
    # Select random IPs
    num_to_select = min(num_ips, len(valid_ips))
    selected = random.sample(valid_ips, num_to_select)
    
    print(f"Selected {num_to_select} random IPs: {selected}")
    return selected


def write_results_to_csv(hops: List[Dict[str, any]], output_file: str = 'p1/traceroute_results.csv'):
    """
    Write traceroute results to CSV file.
    
    Args:
        hops: List of hop dictionaries
        output_file: Output CSV filename
    """
    if not hops:
        print("No hops to write to CSV")
        return
    
    # Define CSV columns
    fieldnames = ['destination_ip', 'hop_number', 'hop_ip', 'min_rtt', 'max_rtt', 'avg_rtt']
    
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(hops)
    
    print(f"\nResults written to {output_file}")
    print(f"Total hops recorded: {len(hops)}")


def main():
    """Main function to run traceroute analysis."""
    print("=" * 70)
    print("Traceroute RTT Analyzer")
    print("=" * 70)
    
    # Select 5 random IPs
    try:
        selected_ips = select_random_ips(num_ips=5)
    except Exception as e:
        print(f"Error selecting IPs: {e}")
        return 1
    
    if not selected_ips:
        print("No valid IPs found")
        return 1
    
    # Run traceroute for each IP and collect results
    all_hops = []
    successful_traces = 0
    
    for i, ip in enumerate(selected_ips, 1):
        print(f"\n[{i}/{len(selected_ips)}] Tracing route to {ip}")
        print("-" * 70)
        
        output = run_traceroute(ip)
    
        if output:
            hops = parse_traceroute_output(output, ip)
            
            if hops:
                print(f"Found {len(hops)} responsive hops")
                all_hops.extend(hops)
                successful_traces += 1
                
                # Print summary for this destination
                hop_summary = ', '.join([f"{h['hop_number']}:{h['hop_ip']}" for h in hops[:5]])
                if len(hops) > 5:
                    hop_summary += "..."
                print(f"Hops: {hop_summary}")
            else:
                print(f"Warning: No responsive hops found for {ip}")
        else:
            print(f"Warning: Failed to trace route to {ip}")
    
    # Write results to CSV
    print("\n" + "=" * 70)
    print(f"Traceroute completed for {successful_traces}/{len(selected_ips)} destinations")
    
    if all_hops:
        write_results_to_csv(all_hops, '/p1/traceroute_results.csv')
        
        # Print statistics
        print(f"\nStatistics:")
        print(f"  Total responsive hops: {len(all_hops)}")
        print(f"  Average RTT across all hops: {sum(h['avg_rtt'] for h in all_hops) / len(all_hops):.2f} ms")
        print(f"  RTT range: {min(h['min_rtt'] for h in all_hops):.2f} - {max(h['max_rtt'] for h in all_hops):.2f} ms")
    else:
        print("No responsive hops found across all destinations")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

