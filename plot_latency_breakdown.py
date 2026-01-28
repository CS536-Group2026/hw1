#!/usr/bin/env python3
"""
Script to plot a stacked bar chart showing the breakdown of latencies to each hop,
corresponding to each of the five chosen destination IP addresses.
Uses incremental RTT per hop (segment = RTT at hop N minus RTT at hop N-1).
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


def load_and_compute_incremental_rtt(csv_file: str = 'traceroute_results.csv') -> pd.DataFrame:
    """
    Load traceroute results and compute incremental RTT per hop for each destination.
    Incremental RTT at hop i = avg_rtt[i] - avg_rtt[i-1], with avg_rtt[0] = 0 for the first hop.

    Returns:
        DataFrame with index=destination_ip, columns=Hop_1, Hop_2, ... (incremental RTT in ms)
    """
    df = pd.read_csv(csv_file)
    if df.empty:
        return pd.DataFrame()

    # Sort by destination then hop_number
    df = df.sort_values(['destination_ip', 'hop_number'])

    records = []
    for dest_ip, group in df.groupby('destination_ip'):
        group = group.sort_values('hop_number')
        rtts = group['avg_rtt'].values
        prev_rtt = 0.0
        increments = []
        for rtt in rtts:
            inc = max(0.0, float(rtt) - prev_rtt)
            increments.append(inc)
            prev_rtt = float(rtt)
        records.append((dest_ip, increments))

    max_hops = max(len(r[1]) for r in records)
    col_names = [f'Hop {i + 1}' for i in range(max_hops)]

    rows = []
    for dest_ip, incs in records:
        row = incs + [0.0] * (max_hops - len(incs))
        rows.append(row)

    return pd.DataFrame(rows, index=[r[0] for r in records], columns=col_names)


def plot_latency_breakdown(
    csv_file: str = 'traceroute_results.csv',
    output_file: str = 'latency_breakdown.pdf',
):
    """
    Plot a stacked bar chart: one bar per destination IP, segments = incremental
    latency per hop (breakdown of latencies to each hop).
    """
    df = load_and_compute_incremental_rtt(csv_file)
    if df.empty:
        print("No data in traceroute_results.csv. Run find_rtt.py first.")
        return

    n_hops = df.shape[1]
    # Use a readable colormap: one color per hop (first hops cooler, last hops hotter)
    colors = plt.cm.viridis(np.linspace(0, 1, n_hops))

    fig, ax = plt.subplots(figsize=(10, 6))

    df.plot(kind='bar', stacked=True, ax=ax, color=colors, width=0.7, edgecolor='white', linewidth=0.5)

    ax.set_xlabel('Destination IP Address', fontsize=12)
    ax.set_ylabel('Round-Trip Time (ms)', fontsize=12)
    ax.set_title('Breakdown of Latencies to Each Hop by Destination', fontsize=14, fontweight='bold')
    ax.set_xticklabels(ax.get_xticklabels(), rotation=15, ha='right')
    ax.legend(title='Hop', bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=8, ncol=1)
    ax.grid(True, axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)

    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Stacked bar chart saved to {output_file}")


def main():
    plot_latency_breakdown()


if __name__ == '__main__':
    main()
