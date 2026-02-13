"""
Create a bar chart showing bytes transferred between consecutive timestamps.

Each bar represents:
- X-axis: Time interval (start time of the interval)
- Y-axis: Number of bytes transferred during that interval
- Color: Number of flows contributing (color-coded)

Usage:
    python3 plot_bytecount_bar.py <path_to_byte_count.json>
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import argparse
import os
from . import plotting_utilities



def load_byte_count(file_path):
    """Load byte_count data from JSON file."""
    with open(file_path, 'r') as f:
        data = json.load(f)

    # Convert string keys to integers
    byte_count = {int(timestamp): value for timestamp, value in data.items()}
    return byte_count


def create_bytecount_bar_chart(byte_count, begin_time=None, title=None, save_path=None, max_time=None, source_times=None):
    """
    Create a bar chart where each bar represents bytes transferred in a time interval.

    Args:
        byte_count: Dictionary {timestamp: [bytes, num_flows]}
        begin_time: Starting timestamp for normalization
        title: Optional plot title
        save_path: Tuple of (base_path, filename) for saving, or None
        max_time: Optional maximum time to display (in seconds)
        source_times: Dictionary containing stream timing and socket information for Gantt chart
    """
    timestamps = sorted(byte_count.keys())
    if begin_time is None:
        begin_time = timestamps[0]

    max_flows = max(byte_count[ts][1] for ts in timestamps if byte_count[ts][1] > 0)

    # Define colors for different flow counts (cool to warm gradient)
    flow_colors = {
        0: '#CCCCCC',  # Gray for no flows
        1: '#0000FF',  # Blue
        2: '#00BFFF',  # DeepSkyBlue
        3: "#00B100",  # Green
        4: '#FFD700',  # Gold
        5: '#FF8C00',  # DarkOrange
        6: '#FF0000',  # Red
    }

    # Extend color mapping if needed
    if max_flows > 6:
        colors = plt.cm.coolwarm(np.linspace(0, 1, max_flows + 1))
        for i in range(max_flows + 1):
            flow_colors[i] = colors[i]

    # Prepare data for plotting
    bar_positions = []  # Start time of each interval
    bar_widths = []     # Duration of each interval (in seconds)
    bar_heights = []    # Bytes transferred
    bar_colors = []     # Color based on flow count

    for i in range(len(timestamps) - 1):
        current_ts = timestamps[i]
        next_ts = timestamps[i + 1]

        start_time = (current_ts - begin_time) / 1000  # Convert to seconds
        end_time = (next_ts - begin_time) / 1000
        interval_width = end_time - start_time

        # Apply max_time filter if specified
        if max_time is not None and start_time > max_time:
            break

        bytes_val, flow_count = byte_count[current_ts]

        bar_positions.append(start_time)
        bar_widths.append(interval_width)
        bar_heights.append(bytes_val)
        bar_colors.append(flow_colors.get(flow_count, '#CCCCCC'))

    # Create the plot with subplots if source_times provided
    if source_times:
        fig, (ax, ax2) = plt.subplots(2, 1, height_ratios=[3, 1], figsize=(14, 10))
    else:
        fig, ax = plt.subplots(figsize=(14, 6))

    # Create bars
    bars = ax.bar(bar_positions, bar_heights, width=bar_widths,
                  color=bar_colors, align='edge', edgecolor='black', linewidth=0.5)

    # Customize axes
    ax.set_xlabel('Time (seconds)', fontsize=12)
    ax.set_ylabel('Bytes Transferred', fontsize=12)

    if title:
        ax.set_title(title, fontsize=14, fontweight='bold')
    else:
        ax.set_title('Bytes Transferred per Time Interval (Color-coded by Flow Count)',
                     fontsize=14, fontweight='bold')

    # Create a custom legend for flow counts
    handles = []
    labels = []
    for i in range(1, max_flows + 1):
        color = flow_colors.get(i, 'gray')
        handles.append(plt.Line2D([0], [0], color=color, lw=3))
        labels.append(f'{i} Flow{"s" if i > 1 else ""}')

    # Place the flow count legend in the upper right
    ax.legend(handles=handles, labels=labels, bbox_to_anchor=(1.05, 1), loc='upper left')


    # Add grid for readability
    ax.grid(True, axis='y', alpha=0.3, linestyle='--')

    # Set x-limit if max_time specified
    if max_time is not None:
        ax.set_xlim(0, max_time)

    # Add HTTP Stream Gantt Chart if source_times is provided
    if source_times:
        # Create color map for unique socket IDs
        unique_sockets = set(info['socket'] for info in source_times.values() if info['socket'] is not None)
        colors = plt.cm.rainbow(np.linspace(0, 1, len(unique_sockets)))
        socket_colors = dict(zip(unique_sockets, colors))

        # Track which socket IDs we've already added to the legend
        legend_added = set()

        # Plot flow durations on the Gantt chart
        y_offset = 0
        for stream_id, info in source_times.items():
            start_sec = (info['times'][0] - begin_time) / 1000
            end_sec = (info['times'][1] - begin_time) / 1000

            # Choose color based on socket ID
            if info['socket'] is not None:
                color = socket_colors[info['socket']]
                label = f'Socket {info["socket"]}'

                # Only add to legend if we haven't seen this socket ID before
                if info['socket'] not in legend_added:
                    ax2.hlines(y=y_offset, xmin=start_sec, xmax=end_sec,
                              color=color, linewidth=2, label=label)
                    legend_added.add(info['socket'])
                else:
                    ax2.hlines(y=y_offset, xmin=start_sec, xmax=end_sec,
                              color=color, linewidth=2)
            else:
                color = 'gray'
                if 'no_socket' not in legend_added:
                    ax2.hlines(y=y_offset, xmin=start_sec, xmax=end_sec,
                              color=color, linewidth=2, label='No Socket')
                    legend_added.add('no_socket')
                else:
                    ax2.hlines(y=y_offset, xmin=start_sec, xmax=end_sec,
                              color=color, linewidth=2)

            y_offset += 1

        # Add labels, legend, and grid for the Gantt chart
        ax2.set_xlabel('Time (seconds)', fontsize=12)
        ax2.set_ylabel('HTTP Stream ID')
        ax2.set_yticks(range(len(source_times)))
        ax2.set_yticklabels([f'Stream {id}' for id in source_times.keys()], fontsize=8)
        ax2.grid(True, axis='y', linestyle='--', alpha=0.3)
        ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

        # Align the x-axes of both plots
        ax.set_xlim(ax2.get_xlim())

    plt.tight_layout()

    if save_path:
        base_path = save_path
        filename = "bytecount_bar_chart.png"
        plotting_utilities.save_figure(fig, base_path, filename)

    plt.show()


def main():
    parser = argparse.ArgumentParser(description='Create bar chart from byte_count data')
    parser.add_argument('byte_count_file', type=str, help='Path to byte_count.json file')
    parser.add_argument('--title', type=str, default=None, help='Plot title')
    parser.add_argument('--save', action='store_true', help='Save the plot')
    parser.add_argument('--stacked', action='store_true', help='Also create stacked version')
    parser.add_argument('--max-time', type=float, default=None,
                       help='Maximum time to display (in seconds)')
    parser.add_argument('--source-times', type=str, default=None,
                       help='Path to source_times.json file for Gantt chart')

    args = parser.parse_args()

    # Load data
    print(f"Loading byte_count data from: {args.byte_count_file}")
    byte_count = load_byte_count(args.byte_count_file)
    print(f"Loaded {len(byte_count)} timestamps")

    # Load source_times if provided
    source_times = None
    begin_time = None
    if args.source_times:
        print(f"Loading source_times data from: {args.source_times}")
        with open(args.source_times, 'r') as f:
            source_times_data = json.load(f)

        # Convert string keys to integers and extract begin_time
        source_times = {}
        for stream_id_str, info in source_times_data.items():
            if stream_id_str == 'begin_time':
                begin_time = info
            else:
                source_times[int(stream_id_str)] = info

        print(f"Loaded {len(source_times)} HTTP streams")
        if begin_time:
            print(f"Begin time: {begin_time}")

    # Determine save path
    save_path = None
    if args.save:
        base_dir = os.path.dirname(args.byte_count_file)
        filename = 'byte_count_bar_chart.png'
        save_path = (base_dir, filename)

    # Create bar chart
    create_bytecount_bar_chart(byte_count, begin_time=begin_time, title=args.title,
                               save_path=save_path, max_time=args.max_time,
                               source_times=source_times)


if __name__ == "__main__":
    main()
