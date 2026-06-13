#!/usr/bin/env python3
"""
Script to plot average percent of maxflow data grouped by server and test direction.
Usage: python plot_average_throughput.py <path_to_csv> [--save]

For sake of time, this script was largely writen with the help of AI
"""
import sys
import argparse
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description='Plot average percent of maxflow data grouped by server and test direction.'
    )
    parser.add_argument('csv_file', help='Path to the CSV file')
    parser.add_argument('--save', action='store_true',
                        help='Save the plot to the current directory instead of displaying it')

    args = parser.parse_args()
    csv_file = args.csv_file

    # Read the CSV file
    try:
        df = pd.read_csv(csv_file)
    except FileNotFoundError:
        print(f"Error: File '{csv_file}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        sys.exit(1)

    # Verify required columns exist
    required_columns = ['server', 'test_direction', 'percent_bytes_all_flows_contributing']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        print(f"Error: Missing required columns: {missing_columns}")
        print(f"Available columns: {df.columns.tolist()}")
        sys.exit(1)

    # Group by server and test_direction, then calculate the average
    grouped = df.groupby(['server', 'test_direction'])['percent_bytes_all_flows_contributing'].mean().reset_index()

    # Pivot the data to have download and upload as separate columns
    pivot_data = grouped.pivot(index='server', columns='test_direction', values='percent_bytes_all_flows_contributing')

    # Define server order explicitly
    server_order = ['merit', 'michwave', 'webnx', 'dallas', 'denver', 'rackoona', 'lansing', 'fairbanks', 'spacelink']

    # Define server name abbreviations
    server_abbrev = {
        'merit': 'ME',
        'michwave': 'MI',
        'webnx': 'WE',
        'dallas': 'DA',
        'denver': 'DE',
        'rackoona': 'RA',
        'lansing': 'LA',
        'fairbanks': 'FA',
        'spacelink': 'SP'
    }

    # Reindex to match the specified order (only include servers that exist in the data)
    existing_servers = [s for s in server_order if s in pivot_data.index]
    pivot_data = pivot_data.reindex(existing_servers)

    # Create the plot
    fig, ax = plt.subplots(figsize=(10, 6))

    # Set up bar positions
    servers = [server_abbrev.get(s, s.capitalize()) for s in pivot_data.index.tolist()]
    x = np.arange(len(servers))
    width = 0.35

    # Create bars
    download_bars = ax.bar(x - width/2, pivot_data.get('download', [0]*len(servers)),
                           width, label='Download', color='skyblue')
    upload_bars = ax.bar(x + width/2, pivot_data.get('upload', [0]*len(servers)),
                         width, label='Upload', color='lightcoral')

    # Customize the plot
    ax.set_ylabel('% Maxflow data', fontsize=20)
    ax.set_xlabel('Servers', fontsize=20)
    ax.set_xticks(x)
    ax.set_xticklabels(servers, fontsize=20)
    ax.legend(loc='upper left', bbox_to_anchor=(1, 1), fontsize=20)
    ax.set_ylim(0, 100)

    # Add grid for easier reading
    ax.yaxis.grid(True, alpha=0.3)
    ax.set_axisbelow(True)

    # Tight layout with rect to make room for legend
    plt.tight_layout(rect=[0, 0, 0.85, 1])

    # Save or show the plot
    if args.save:
        # Get the directory where this script is located
        script_dir = Path(__file__).parent
        output_file = script_dir / 'average_throughput.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Plot saved to: {output_file}")
    else:
        plt.show()

    # Print summary statistics
    print("\n=== Summary Statistics ===")
    print("\nAverage % of maxflow data by server and test direction:")
    print(pivot_data.to_string())
    print(f"\nTotal servers: {len(servers)}")


if __name__ == "__main__":
    main()
