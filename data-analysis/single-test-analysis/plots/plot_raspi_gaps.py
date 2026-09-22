#!/usr/bin/env python3
"""
Plot event occurrences from byte_count.json file as vertical lines.
Usage: python3 plot_raspi_gaps.py <path_to_byte_count.json> [--source-times <path_to_source_times.json>]
"""

import json
import sys
import argparse
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

def load_and_process_data(json_path):
    """Load JSON file and normalize timestamps to seconds."""
    with open(json_path, 'r') as f:
        data = json.load(f)

    # Convert string keys to integers
    byte_count = {int(timestamp): value for timestamp, value in data.items()}

    # Get timestamps and determine begin_time
    timestamps = sorted(byte_count.keys())
    begin_time = timestamps[0]

    # Normalize timestamps and categorize by packet count
    events = {}
    for timestamp_ms in timestamps:
        values = byte_count[timestamp_ms]
        # Normalize: subtract begin_time and convert to seconds
        timestamp_sec = (timestamp_ms - begin_time) / 1000.0
        num_active_sockets = values[1]  # Second element is packet count

        if num_active_sockets not in events:
            events[num_active_sockets] = []
        events[num_active_sockets].append(timestamp_sec)

    return events, begin_time

def plot_events(events, begin_time=None, output_file='event_plot.png', source_times=None):
    """
    Create a compact vertical line plot showing event occurrences.

    Args:
        events: Dictionary of {num_active_sockets: [timestamps]}
        begin_time: Starting timestamp for normalization (for Gantt chart)
        output_file: Path to save the output image
        source_times: Optional dictionary containing stream timing and socket information for Gantt chart
    """
    # Sizing parameters
    fig_width = 10
    fig_height = 3
    line_width = 1
    label_fontsize = 20
    tick_fontsize = 12
    legend_fontsize = 16
    legend_alpha = 0.9
    legend_x_offset = 1.05
    legend_y_position = 1
    save_dpi = 300 # resolution of image

    flow_color_map = {
        1: 5,
        2: 11,
        3: 10,
        4: 8,
        5: 2,
        6: 1
    }

    paired_colormap = plt.cm.Paired
    colors = {flow: paired_colormap(idx / 11.0) for flow, idx in flow_color_map.items()}
    colors[0] = 'gray'  # Gray for 0 flows

    # Create the plot with subplots if source_times provided
    gantt_height = 2  # Height in inches for the Gantt chart
    if source_times:
        # Use actual heights to keep occurrence plot consistent
        fig, (ax, ax2) = plt.subplots(2, 1, height_ratios=[fig_height, gantt_height],
                                      figsize=(fig_width, fig_height + gantt_height))
    else:
        fig, ax = plt.subplots(figsize=(fig_width, fig_height))

    # Plot vertical lines for each event spanning full height
    for num_active_sockets, timestamps in sorted(events.items()):
        color = colors.get(num_active_sockets, '#808080')  # Default to gray if not in colors
        for ts in timestamps:
            ax.axvline(x=ts, ymin=0, ymax=1, color=color, linewidth=line_width)

    # Configure axes
    if source_times is None:
        ax.set_xlabel('Time (seconds)', fontsize=label_fontsize)
    ax.set_ylabel('Netlog Event\nOccurrences', fontsize=label_fontsize)
    ax.tick_params(axis='both', which='major', labelsize=tick_fontsize)

    # Set y-axis limits to make it compact
    ax.set_ylim(0, 1)
    ax.set_yticks([])

    # Create legend
    legend_elements = [mpatches.Patch(facecolor=colors.get(num_active_sockets, '#808080'),
                                      label=f'{num_active_sockets} Flow' if num_active_sockets == 1 else f'{num_active_sockets} Flows')
                      for num_active_sockets in sorted(events.keys()) if num_active_sockets > 0]
    ax.legend(handles=legend_elements, bbox_to_anchor=(legend_x_offset, legend_y_position),
              loc='upper left', fontsize=legend_fontsize, framealpha=legend_alpha)

    # Add HTTP Stream Gantt Chart if source_times is provided - Grouped by Socket
    if source_times:
        # Group streams by socket ID
        socket_groups = {}
        for stream_id, info in source_times.items():
            socket_id = info['socket'] if info['socket'] is not None else 'no_socket'
            if socket_id not in socket_groups:
                socket_groups[socket_id] = []
            socket_groups[socket_id].append({
                'stream_id': stream_id,
                'start': (info['times'][0] - begin_time) / 1000,
                'end': (info['times'][1] - begin_time) / 1000
            })

        # Create color map for unique socket IDs
        unique_sockets = [s for s in socket_groups.keys() if s != 'no_socket']
        gantt_colors = plt.cm.Paired(np.linspace(0, 1, len(unique_sockets)))
        socket_colors = dict(zip(unique_sockets, gantt_colors))
        socket_colors['no_socket'] = 'gray'

        # Plot each socket group on its own row
        y_offset = 0
        sorted_sockets = sorted([s for s in socket_groups.keys() if s != 'no_socket']) + (['no_socket'] if 'no_socket' in socket_groups else [])

        for socket_id in sorted_sockets:
            streams = socket_groups[socket_id]
            color = socket_colors[socket_id]

            # Plot all streams for this socket on the same row
            for stream in streams:
                ax2.hlines(y=y_offset, xmin=stream['start'], xmax=stream['end'],
                          color=color, linewidth=2)

            y_offset += 1

        # Add labels, legend, and grid for the Gantt chart
        ax2.set_xlabel('Time (seconds)', fontsize=label_fontsize)
        ax2.set_ylabel('Active\nSockets', fontsize=label_fontsize)
        ax2.set_yticks([])
        ax2.grid(True, axis='y', linestyle='--', alpha=0.3)

        # Create legend for sockets
        socket_handles = []
        socket_labels = []
        for socket_id in sorted_sockets:
            color = socket_colors[socket_id]
            socket_handles.append(plt.Line2D([0], [0], color=color, lw=2))
            socket_labels.append(f'Socket {socket_id}' if socket_id != 'no_socket' else 'No Socket')

        ax2.legend(handles=socket_handles, labels=socket_labels, bbox_to_anchor=(legend_x_offset, legend_y_position), loc='upper left', fontsize=legend_fontsize, framealpha=legend_alpha)

        # Align the x-axes of both plots
        ax.set_xlim(ax2.get_xlim())

    # Adjust layout to prevent label cutoff
    plt.tight_layout()

    # Save and show
    plt.savefig(output_file, dpi=save_dpi, bbox_inches='tight')
    print(f"Plot saved to {output_file}")
    plt.show()

def main():
    parser = argparse.ArgumentParser(description='Create event occurrence plot from byte_count data')
    parser.add_argument('byte_count_file', type=str, help='Path to byte_count.json file')
    parser.add_argument('--source-times', type=str, default=None,
                       help='Path to source_times.json file for Gantt chart')
    parser.add_argument('--output', type=str, default='event_plot.png',
                       help='Output file path (default: event_plot.png)')

    args = parser.parse_args()

    try:
        # Load byte_count data
        print(f"Loading byte_count data from: {args.byte_count_file}")
        events, begin_time = load_and_process_data(args.byte_count_file)
        print(f"Loaded {sum(len(timestamps) for timestamps in events.values())} events")

        # Load source_times if provided
        source_times = None
        if args.source_times:
            print(f"Loading source_times data from: {args.source_times}")
            with open(args.source_times, 'r') as f:
                source_times_data = json.load(f)

            # Convert string keys to integers and extract begin_time if present
            source_times = {}
            for stream_id_str, info in source_times_data.items():
                if stream_id_str == 'begin_time':
                    begin_time = info  # Override with source_times begin_time if present
                else:
                    source_times[int(stream_id_str)] = info

            print(f"Loaded {len(source_times)} HTTP streams")

        # Create plot
        plot_events(events, begin_time=begin_time, output_file=args.output, source_times=source_times)

    except FileNotFoundError as e:
        print(f"Error: File not found - {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON - {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
