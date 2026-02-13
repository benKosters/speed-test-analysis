"""
Generate a heatmap visualization of byte_count data showing:
- X-axis: Time (normalized to seconds)
- Y-axis: Number of contributing flows
- Color intensity: Bytes transferred at that timestamp and flow count

Usage:
    python3 plot_time_interval_bins.py <path_to_byte_count.json>
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Rectangle
import argparse
import os


def load_byte_count(file_path):
    """Load byte_count data from JSON file."""
    with open(file_path, 'r') as f:
        data = json.load(f)

    # Convert string keys to integers
    byte_count = {int(timestamp): value for timestamp, value in data.items()}
    return byte_count


def create_heatmap(byte_count, begin_time=None, title=None, save_path=None):
    """
    Create a heatmap showing bytes transferred at each timestamp grouped by flow count.

    Args:
        byte_count: Dictionary {timestamp: [bytes, num_flows]}
        begin_time: Starting timestamp for normalization (if None, uses min timestamp)
        title: Optional plot title
        save_path: Optional path to save the figure
    """
    # Extract timestamps and normalize to seconds
    timestamps = sorted(byte_count.keys())
    if begin_time is None:
        begin_time = timestamps[0]

    times_sec = [(ts - begin_time) / 1000 for ts in timestamps]

    # Find max number of flows
    max_flows = max(byte_count[ts][1] for ts in timestamps)

    if max_flows == 0:
        print("No flows found in data!")
        return

    # Create data matrix: rows = flow counts, columns = time bins
    # We'll bin the data into time intervals for better visualization
    time_bin_size = 0.01  # 10ms bins
    max_time = max(times_sec)
    num_time_bins = int(max_time / time_bin_size) + 1

    # Initialize matrix: rows for each flow count (1 to max_flows)
    heatmap_data = np.zeros((max_flows, num_time_bins))

    # Fill the matrix
    for ts, (bytes_val, flow_count) in byte_count.items():
        if flow_count == 0:
            continue  # Skip timestamps with no flows

        time_sec = (ts - begin_time) / 1000
        time_bin = int(time_sec / time_bin_size)

        if time_bin < num_time_bins:
            # Add bytes to the appropriate flow count row (1-indexed to 0-indexed)
            heatmap_data[flow_count - 1, time_bin] += bytes_val

    # Create the plot
    fig, ax = plt.subplots(figsize=(14, 6))

    # Create heatmap using imshow
    # Use log scale for better visualization of varying byte amounts
    # Add 1 to avoid log(0)
    heatmap_display = np.log10(heatmap_data + 1)

    im = ax.imshow(heatmap_display, aspect='auto', cmap='YlOrRd',
                   origin='lower', interpolation='nearest',
                   extent=[0, max_time, 0.5, max_flows + 0.5])

    # Add colorbar
    cbar = plt.colorbar(im, ax=ax, label='log₁₀(Bytes + 1)')

    # Customize axes
    ax.set_xlabel('Time (seconds)', fontsize=12)
    ax.set_ylabel('Number of Contributing Flows', fontsize=12)
    ax.set_yticks(range(1, max_flows + 1))
    ax.set_yticklabels([f'{i} flow{"s" if i > 1 else ""}' for i in range(1, max_flows + 1)])

    if title:
        ax.set_title(title, fontsize=14, fontweight='bold')
    else:
        ax.set_title('Byte Transfer Heatmap: Flow Concurrency vs Time', fontsize=14, fontweight='bold')

    # Add grid for readability
    ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Heatmap saved to: {save_path}")

    plt.show()


def create_stacked_area_heatmap(byte_count, begin_time=None, title=None, save_path=None):
    """
    Create a stacked area chart showing bytes transferred over time, separated by flow count.

    Args:
        byte_count: Dictionary {timestamp: [bytes, num_flows]}
        begin_time: Starting timestamp for normalization
        title: Optional plot title
        save_path: Optional path to save the figure
    """
    timestamps = sorted(byte_count.keys())
    if begin_time is None:
        begin_time = timestamps[0]

    times_sec = [(ts - begin_time) / 1000 for ts in timestamps]
    max_flows = max(byte_count[ts][1] for ts in timestamps)

    # Organize data by flow count
    flow_data = {i: [] for i in range(1, max_flows + 1)}
    time_points = []

    for ts in timestamps:
        time_sec = (ts - begin_time) / 1000
        bytes_val, flow_count = byte_count[ts]

        time_points.append(time_sec)

        # Add bytes to appropriate flow count, 0 for others
        for i in range(1, max_flows + 1):
            if i == flow_count:
                flow_data[i].append(bytes_val)
            else:
                flow_data[i].append(0)

    # Create stacked area plot
    fig, ax = plt.subplots(figsize=(14, 6))

    # Define colors (cool to warm gradient)
    colors = plt.cm.coolwarm(np.linspace(0, 1, max_flows))

    # Stack the data
    flow_arrays = [flow_data[i] for i in range(1, max_flows + 1)]
    ax.stackplot(time_points, *flow_arrays, labels=[f'{i} flows' for i in range(1, max_flows + 1)],
                 colors=colors, alpha=0.7)

    ax.set_xlabel('Time (seconds)', fontsize=12)
    ax.set_ylabel('Bytes Transferred', fontsize=12)

    if title:
        ax.set_title(title, fontsize=14, fontweight='bold')
    else:
        ax.set_title('Bytes Over Time by Flow Count (Stacked)', fontsize=14, fontweight='bold')

    ax.legend(loc='upper right', fontsize=10)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        save_path_stacked = save_path.replace('.png', '_stacked.png')
        plt.savefig(save_path_stacked, dpi=300, bbox_inches='tight')
        print(f"Stacked area chart saved to: {save_path_stacked}")

    plt.show()


def main():
    parser = argparse.ArgumentParser(description='Create heatmap visualizations from byte_count data')
    parser.add_argument('byte_count_file', type=str, help='Path to byte_count.json file')
    parser.add_argument('--title', type=str, default=None, help='Plot title')
    parser.add_argument('--save', action='store_true', help='Save the plot')
    parser.add_argument('--stacked', action='store_true', help='Also create stacked area chart')

    args = parser.parse_args()

    # Load data
    print(f"Loading byte_count data from: {args.byte_count_file}")
    byte_count = load_byte_count(args.byte_count_file)
    print(f"Loaded {len(byte_count)} timestamps")

    # Determine save path
    save_path = None
    if args.save:
        base_dir = os.path.dirname(args.byte_count_file)
        save_path = os.path.join(base_dir, 'byte_count_heatmap.png')

    # Create heatmap
    create_heatmap(byte_count, title=args.title, save_path=save_path)

    # Optionally create stacked area chart
    if args.stacked:
        create_stacked_area_heatmap(byte_count, title=args.title, save_path=save_path)


if __name__ == "__main__":
    main()
