"""
Comparison Visualizations Module

This module contains visualization functions for comparing multiple tests.
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import sys

# Add the parent directory to the path so we can import the processing modules
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

import helper_functions as hf

def plot_multi_test_throughput(selected_tests, params):
    """Compare throughput across multiple tests"""
    if len(selected_tests) < 2:
        return None

    interval = int(params.get("interval", 10))

    # Create a figure
    fig = Figure(figsize=(12, 8))
    ax = fig.add_subplot(1, 1, 1)

    # Use different colors for each test
    colors = plt.cm.tab10(np.linspace(0, 1, len(selected_tests)))

    # Plot each test's throughput
    for i, (test_name, test_info) in enumerate(selected_tests.items()):
        test_data = test_info["data"]

        # Get throughput data for the specified interval
        throughput_data = pd.DataFrame(test_data["throughput_results"][interval])

        # Calculate REMA
        throughput_data['throughput_ema'] = throughput_data['throughput'].ewm(alpha=0.1, adjust=False).mean()

        # Plot the throughput
        ax.plot(throughput_data['time'], throughput_data['throughput_ema'],
               label=test_name, color=colors[i], linewidth=2)

    # Add labels and legend
    ax.set_xlabel('Time (seconds)')
    ax.set_ylabel('Throughput (Mbps)')
    ax.set_title(f'Throughput Comparison ({interval}ms interval)')
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)

    # Set y-axis limits
    ax.set_ylim(0, 300)

    return fig

def compare_throughput_and_streams(selected_tests, params):
    """Compare throughput and HTTP streams from two tests"""
    # This visualization requires exactly 2 tests
    if len(selected_tests) != 2:
        return None

    interval = int(params.get("interval", 2))
    ymin = params.get("ymin", 20)
    ymax = params.get("ymax", 250)

    # Create a new figure with two subplots with appropriate height ratios
    fig = Figure(figsize=(14, 10))
    gs = fig.add_gridspec(2, 1, height_ratios=[3, 1])
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1])
    fig.subplots_adjust(hspace=0.3)

    # Define distinct colors for each test
    test_colors = {
        0: 'red',      # First test color
        1: 'blue'      # Second test color
    }

    # Track all stream offsets across both tests
    combined_streams = {}
    y_offset = 0
    legend_added = set()

    # Process each test
    for i, (test_name, test_info) in enumerate(selected_tests.items()):
        test_data = test_info["data"]
        test_color = test_colors[i]

        # Get throughput data and calculate REMA
        throughput_data = pd.DataFrame(test_data["throughput_results"][interval])
        throughput_data['throughput_ema'] = throughput_data['throughput'].ewm(alpha=0.1, adjust=False).mean()

        # Plot throughput on the top subplot
        ax1.plot(throughput_data['time'], throughput_data['throughput_ema'],
                color=test_color, linestyle='--', label=f'{test_name} REMA')

        # Get source times for HTTP streams
        source_times = test_data["source_times"]
        begin_time = test_data["begin_time"]

        # Create a color map for unique socket IDs within this test
        # We want the socket colors to follow the test color scheme
        unique_sockets = set(info['socket'] for info in source_times.values() if info['socket'] is not None)

        # Create a colormap that's based on the test's main color
        # Use lighter/darker shades of the test color for different sockets
        if test_color == 'red':
            cmap = plt.cm.Reds
        else:  # blue
            cmap = plt.cm.Blues

        socket_colors = {}
        for j, socket_id in enumerate(unique_sockets):
            # Use values from 0.5 to 0.9 to get visible colors (not too light or dark)
            color_val = 0.5 + (0.4 * j / max(1, len(unique_sockets) - 1))
            socket_colors[socket_id] = cmap(color_val)

        # Store stream info for the bottom subplot
        for stream_id, info in source_times.items():
            # Create a unique ID for each stream across both tests
            unique_id = f"{test_name}_{stream_id}"

            # Store the stream info with a reference to its test
            combined_streams[unique_id] = {
                'start_sec': (info['times'][0] - begin_time) / 1000,
                'end_sec': (info['times'][1] - begin_time) / 1000,
                'socket': info['socket'],
                'socket_colors': socket_colors,
                'test_name': test_name,
                'test_color': test_color,
                'y_offset': y_offset
            }
            y_offset += 1

    # Plot all HTTP streams in the bottom subplot
    for unique_id, stream_info in combined_streams.items():
        start_sec = stream_info['start_sec']
        end_sec = stream_info['end_sec']
        socket = stream_info['socket']
        socket_colors = stream_info['socket_colors']
        test_name = stream_info['test_name']
        test_color = stream_info['test_color']
        y_offset = stream_info['y_offset']

        if socket is not None:
            color = socket_colors.get(socket, test_color)
            label = f'{test_name} Socket {socket}'

            # Only add to legend if we haven't seen this combination before
            legend_key = f"{test_name}_{socket}"
            if legend_key not in legend_added:
                ax2.hlines(y=y_offset, xmin=start_sec, xmax=end_sec,
                          color=color, linewidth=2, label=label)
                legend_added.add(legend_key)
            else:
                ax2.hlines(y=y_offset, xmin=start_sec, xmax=end_sec,
                          color=color, linewidth=2)
        else:
            # Use a lighter shade of the test color for streams with no socket
            color = plt.cm.colors.to_rgba(test_color, alpha=0.5)
            label = f'{test_name} No Socket'

            legend_key = f"{test_name}_no_socket"
            if legend_key not in legend_added:
                ax2.hlines(y=y_offset, xmin=start_sec, xmax=end_sec,
                          color=color, linewidth=2, label=label)
                legend_added.add(legend_key)
            else:
                ax2.hlines(y=y_offset, xmin=start_sec, xmax=end_sec,
                          color=color, linewidth=2)

    # Configure axes
    ax1.set_xlabel('Time (in seconds)')
    ax1.set_ylabel('Throughput (in Mbps)')
    ax1.legend(loc='upper right')
    ax1.set_ylim(ymin, ymax)
    ax1.grid(True, alpha=0.3)

    ax2.set_xlabel('Time (in seconds)')
    ax2.set_ylabel('HTTP Stream ID')
    ax2.set_yticks(range(len(combined_streams)))
    ax2.set_yticklabels([stream_id for stream_id in combined_streams.keys()], fontsize=8)
    ax2.grid(True, axis='y', linestyle='--', alpha=0.3)
    ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

    # Find the overall time range
    all_times = []
    for info in combined_streams.values():
        all_times.extend([info['start_sec'], info['end_sec']])

    if all_times:
        time_range = [min(all_times), max(all_times)]
        ax1.set_xlim(time_range)
        ax2.set_xlim(time_range)

    # Set the figure title
    test_names = ", ".join(selected_tests.keys())
    fig.suptitle(f"Throughput Comparison: {test_names} ({interval}ms interval)", fontsize=14)

    # Adjust layout for better spacing
    fig.tight_layout(rect=[0, 0, 0.85, 0.95])  # Make room for the legend and title

    return fig