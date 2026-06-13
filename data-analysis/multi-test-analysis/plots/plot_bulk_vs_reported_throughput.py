#!/usr/bin/env python3
"""
Script to plot bulk throughput vs Ookla reported throughput,
grouped by test direction (upload/download) and server.

Usage:
    python plot_bulk_vs_reported_throughput.py <core_csv_file>

Due to tightness of time, this script was written with the assistance of AI.
"""

import math
import sys
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path


def load_data(csv_file):
    """Load CSV file and return DataFrame."""
    try:
        df = pd.read_csv(csv_file)
        return df
    except FileNotFoundError:
        print(f"Error: File '{csv_file}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        sys.exit(1)


def validate_columns(df):
    """Validate that required columns exist in the DataFrame."""
    required_columns = ['bulk_throughput_mbps', 'ookla_reported_throughput',
                       'test_direction', 'server']
    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        print(f"Error: Missing required columns: {missing_columns}")
        print(f"Available columns: {list(df.columns)}")
        sys.exit(1)


def plot_grouped_bars(df, output_path=None):
    """
    Create grouped bar chart comparing bulk throughput vs reported throughput.
    """
    # Prepare data for plotting
    grouped = df.groupby(['test_direction', 'server']).agg({
        'bulk_throughput_mbps': 'mean',
        'ookla_reported_throughput': 'mean'
    }).reset_index()

    # Get unique test directions
    test_directions = grouped['test_direction'].unique()

    # Create figure with subplots
    fig, axes = plt.subplots(1, len(test_directions),
                             figsize=(6 * len(test_directions), 6))
    if len(test_directions) == 1:
        axes = [axes]

    for idx, direction in enumerate(test_directions):
        ax = axes[idx]
        direction_data = grouped[grouped['test_direction'] == direction]

        x = range(len(direction_data))
        width = 0.35

        ax.bar([i - width/2 for i in x],
               direction_data['bulk_throughput_mbps'],
               width, label='Bulk Throughput', alpha=0.8, color='lightskyblue')
        ax.bar([i + width/2 for i in x],
               direction_data['ookla_reported_throughput'],
               width, label='Ookla Reported', alpha=0.8, color = 'indianred')

        ax.set_xlabel('Server', fontsize=11)
        ax.set_ylabel('Throughput (Mbps)', fontsize=11)
        ax.set_ylim(0, math.ceil(max(grouped['bulk_throughput_mbps'].max(), grouped['ookla_reported_throughput'].max()) + 200))
        ax.set_title(f'{direction.capitalize()}', fontsize=12, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(direction_data['server'], rotation=45, ha='right')

        ax.legend()

        ax.grid(True, alpha=0.3, axis='y')

    plt.suptitle('Mean Throughput by Server and Test Direction',
                 fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Plot saved to: {output_path}")

    plt.show()


def main():
    if len(sys.argv) < 2:
        print("Usage: python plot_bulk_vs_reported_throughput.py <csv_file>")
        sys.exit(1)

    csv_file = sys.argv[1]

    # Load and validate data
    print(f"Loading data from: {csv_file}")
    df = load_data(csv_file)
    validate_columns(df)

    print(f"Data loaded: {len(df)} rows")
    print(f"Test directions: {df['test_direction'].unique()}")
    print(f"Servers: {df['server'].unique()}")

    # Generate output path
    input_path = Path(csv_file)
    output_bars = input_path.parent / f"{input_path.stem}_bar_plot.png"

    # Create both visualizations
    print("\nGenerating scatter plot comparison...")

    print("\nGenerating grouped bar chart...")
    plot_grouped_bars(df, output_bars)

    print("\nDone!")


if __name__ == "__main__":
    main()
