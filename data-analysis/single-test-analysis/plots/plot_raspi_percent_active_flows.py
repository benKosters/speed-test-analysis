#!/usr/bin/env python3
"""
Plot the percent time all flows are active for multi-connection tests across different servers.
"""

import sys
import pandas as pd
import matplotlib.pyplot as plt
import argparse


def main():
    parser = argparse.ArgumentParser(
        description='Plot percent time all flows are active by server'
    )
    parser.add_argument('csv_file', help='Path to the CSV file containing the data')
    parser.add_argument('--output', '-o', help='Output file path (default: show plot)', default=None)

    args = parser.parse_args()

    # Read the CSV file
    df = pd.read_csv(args.csv_file)

    # Filter for download tests only and multi-connection type
    df = df[df['test_direction'] == 'download'].copy()
    df = df[df['connection_type'] == 'multi'].copy()

    # Check if data exists
    if df.empty:
        print("Error: No data found with test_direction='download' and connection_type='multi'")
        sys.exit(1)

    # Create the bar plot
    axis_fontsize = 20
    tick_fontsize = 20

    fig, ax = plt.subplots(figsize=(12, 6))

    # Plot bars (all multi-connection, so use blue)
    bars = ax.bar(range(len(df)),
                   df['percent_time_all_flows_contributing'],
                   color='cornflowerblue',
                   edgecolor='black',
                   linewidth=0.5)

    # Set x-axis labels to server names
    ax.set_xticks(range(len(df)))
    ax.set_xticklabels(df['server'], rotation=45, ha='right', fontsize=tick_fontsize)

    # Set y-axis to percentage scale
    ax.set_ylim(0, 100)
    ax.tick_params(axis='y', labelsize=tick_fontsize)
    ax.set_ylabel('Percent Time\nAll Flows Are Active', fontsize=axis_fontsize)
    ax.set_xlabel('Server', fontsize=axis_fontsize)

    # Add percentage formatting to y-axis
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{int(y)}%'))

    # Add grid for better readability
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)

    # Adjust layout to prevent label cutoff
    plt.tight_layout()

    # Save or show the plot
    if args.output:
        plt.savefig(args.output, dpi=300, bbox_inches='tight')
        print(f"Plot saved to {args.output}")
    else:
        plt.show()


if __name__ == '__main__':
    main()
