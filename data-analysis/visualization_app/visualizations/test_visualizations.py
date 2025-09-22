"""
Test Visualizations Module

This module contains visualization functions for analyzing a single test.
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

def plot_throughput_with_streams(selected_tests, params):
    """Plot throughput with HTTP streams"""
    # Get the first (and only) test
    test_name = list(selected_tests.keys())[0]
    test_data = selected_tests[test_name]["data"]

    interval = int(params.get("interval", 2))
    ymin = params.get("ymin", 20)
    ymax = params.get("ymax", 250)

    # Get the appropriate throughput data
    throughput_data = pd.DataFrame(test_data["throughput_results"][interval])

    # Create a new figure with two subplots with appropriate height ratios
    fig = Figure(figsize=(12, 8))
    gs = fig.add_gridspec(2, 1, height_ratios=[3, 1])
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1])
    fig.subplots_adjust(hspace=0.3)

    # Calculate REMA
    throughput_data['throughput_ema'] = throughput_data['throughput'].ewm(alpha=0.1, adjust=False).mean()

    # Plot throughput on the top subplot
    ax1.plot(throughput_data['time'], throughput_data['throughput_ema'],
            color='red', linestyle='--', label='REMA Throughput')
    ax1.set_xlabel('Time (in seconds)')
    ax1.set_ylabel('Throughput (in Mbps)')
    ax1.legend()
    ax1.set_ylim(ymin, ymax)

    # Create color map for unique socket IDs
    source_times = test_data["source_times"]
    begin_time = test_data["begin_time"]

    unique_sockets = set(info['socket'] for info in source_times.values() if info['socket'] is not None)
    colors = plt.cm.rainbow(np.linspace(0, 1, len(unique_sockets)))
    socket_colors = dict(zip(unique_sockets, colors))

    # Track which socket IDs we've already added to the legend
    legend_added = set()

    # Plot flow durations on bottom subplot
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

    ax2.set_xlabel('Time (in seconds)')
    ax2.set_ylabel('HTTP Stream ID')
    ax2.set_yticks(range(len(source_times)))
    ax2.set_yticklabels([f'Stream {id}' for id in source_times.keys()], fontsize=8)
    ax2.grid(True, axis='y', linestyle='--', alpha=0.3)
    ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

    # Align the x-axes of both plots
    ax1.set_xlim(ax2.get_xlim())

    # Set the figure title
    fig.suptitle(f"{test_name} - Throughput with HTTP Streams ({interval}ms interval)", fontsize=14)

    # Adjust layout for better spacing
    fig.tight_layout(rect=[0, 0, 0.85, 0.95])  # Make room for the legend and title

    return fig

def plot_throughput_by_flows(selected_tests, params):
    """Plot throughput with points colored by the number of flows"""
    # Get the first (and only) test
    test_name = list(selected_tests.keys())[0]
    test_data = selected_tests[test_name]["data"]

    interval = int(params.get("interval", 10))
    scatter = params.get("scatter", True)
    start_time = params.get("start_time", 0)
    end_time = params.get("end_time", 15)

    # Get the appropriate throughput data
    throughput_by_flows = test_data["throughput_by_flows"][interval]
    source_times = test_data["source_times"]
    begin_time = test_data["begin_time"]

    # Create a new figure with two subplots with appropriate height ratios
    fig = Figure(figsize=(12, 8))
    gs = fig.add_gridspec(2, 1, height_ratios=[3, 1])
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1])
    fig.subplots_adjust(hspace=0.3)

    # Define colors for different flow counts
    flow_colors = {
        1: 'purple',
        2: 'blue',
        3: 'green',
        4: 'orange',
        5: 'red',
        6: 'brown'
    }

    # Create a combined DataFrame with a 'flow_count' column
    combined_data = []
    for flow_count, throughput_list in throughput_by_flows.items():
        for entry in throughput_list:
            if start_time <= entry['time'] <= end_time:
                combined_data.append({
                    'time': entry['time'],
                    'throughput': entry['throughput'],
                    'flow_count': flow_count
                })

    combined_df = pd.DataFrame(combined_data).sort_values(by='time').reset_index(drop=True)
    combined_df['throughput_ema'] = combined_df['throughput'].ewm(alpha=0.1, adjust=False).mean()

    # Plot scatter points if requested
    if scatter:
        for flow_count in sorted(throughput_by_flows.keys()):
            mask = combined_df['flow_count'] == flow_count
            if mask.any():  # Only plot if there are points with this flow count
                ax1.scatter(
                    combined_df.loc[mask, 'time'],
                    combined_df.loc[mask, 'throughput'],
                    color=flow_colors.get(flow_count, 'gray'),
                    s=5,  # Slightly smaller points to avoid overwhelming the plot
                    alpha=0.8,  # Slightly transparent
                    label=f'{flow_count} Flows (data points)'
                )

    # Plot the REMA line as line segments with different colors
    for i in range(1, len(combined_df)):
        flow_count_prev = combined_df.iloc[i-1]['flow_count']
        flow_count_current = combined_df.iloc[i]['flow_count']

        if flow_count_prev != flow_count_current or i == len(combined_df) - 1:
            # Find all consecutive points with the same flow count
            segment_start = i-1
            while segment_start > 0 and combined_df.iloc[segment_start-1]['flow_count'] == flow_count_prev:
                segment_start -= 1

            segment = combined_df.iloc[segment_start:i]

            ax1.plot(
                segment['time'],
                segment['throughput_ema'],
                color=flow_colors.get(flow_count_prev, 'gray'),
                linewidth=1.5,
                linestyle='--',
            )

    # Add labels and axis limits
    ax1.set_xlabel('Time (in seconds)')
    ax1.set_ylabel('Throughput (in Mbps)')
    ax1.set_ylim(20, 250)
    ax1.set_xlim(start_time, end_time)

    # Create a custom legend for flow counts
    handles = []
    labels = []
    for flow_count in sorted(set(combined_df['flow_count'])):
        color = flow_colors.get(flow_count, 'gray')
        handles.append(plt.Line2D([0], [0], color=color, lw=3))
        labels.append(f'{flow_count} Flows')

    # Place the flow count legend in the upper right
    ax1.legend(handles=handles, labels=labels, loc='upper right')

    # Plot HTTP streams in bottom subplot
    unique_sockets = set(info['socket'] for info in source_times.values() if info['socket'] is not None)
    colors = plt.cm.rainbow(np.linspace(0, 1, len(unique_sockets)))
    socket_colors = dict(zip(unique_sockets, colors))

    legend_added = set()

    y_offset = 0
    for stream_id, info in source_times.items():
        start_sec = (info['times'][0] - begin_time) / 1000
        end_sec = (info['times'][1] - begin_time) / 1000

        if info['socket'] is not None:
            color = socket_colors[info['socket']]
            label = f'Socket {info["socket"]}'

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

    ax2.set_xlabel('Time (in seconds)')
    ax2.set_ylabel('HTTP Stream ID')
    ax2.set_yticks(range(len(source_times)))
    ax2.set_yticklabels([f'Stream {id}' for id in source_times.keys()], fontsize=8)
    ax2.grid(True, axis='y', linestyle='--', alpha=0.3)
    ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

    # Set the same x-axis limits for both plots
    ax1.set_xlim(start_time, end_time)
    ax2.set_xlim(start_time, end_time)

    # Set the figure title
    fig.suptitle(f"{test_name} - Throughput by Flow Count ({interval}ms interval)", fontsize=14)

    # Adjust layout for better spacing
    fig.tight_layout(rect=[0, 0, 0.85, 0.95])  # Make room for the legend and title

    return fig

def plot_latency_comparison(selected_tests, params):
    """Plot latency comparison"""
    # Get the first (and only) test
    test_name = list(selected_tests.keys())[0]
    test_data = selected_tests[test_name]["data"]

    idle_latencies = test_data["idle_latencies"]
    loaded_latencies = test_data["loaded_latencies"]

    if not idle_latencies and not loaded_latencies:
        return None

    # Create a figure with two subplots
    fig = Figure(figsize=(14, 7))
    ax1 = fig.add_subplot(1, 2, 1)
    ax2 = fig.add_subplot(1, 2, 2)

    # Plot scatter plot
    if idle_latencies:
        ax1.scatter(range(len(idle_latencies)), idle_latencies,
                  label='Idle Latency', alpha=0.7, color='blue')

    if loaded_latencies:
        ax1.scatter(range(len(loaded_latencies)), loaded_latencies,
                  label='Loaded Latency', alpha=0.7, color='red')

    ax1.set_xlabel('Stream Index')
    ax1.set_ylabel('Latency (ms)')
    ax1.set_title('Idle vs Loaded Latency Comparison')
    ax1.legend()

    # Plot histogram
    if idle_latencies:
        ax2.hist(idle_latencies, bins=20, alpha=0.7, label='Idle Latency', color='blue')
    if loaded_latencies:
        ax2.hist(loaded_latencies, bins=20, alpha=0.7, label='Loaded Latency', color='red')

    ax2.set_xlabel('Latency (ms)')
    ax2.set_ylabel('Frequency')
    ax2.set_title('Latency Distribution')
    ax2.legend()

    # Calculate and display metrics
    if idle_latencies and loaded_latencies:
        idle_mean = sum(idle_latencies) / len(idle_latencies)
        loaded_mean = sum(loaded_latencies) / len(loaded_latencies)
        latency_increase = loaded_mean - idle_mean
        latency_increase_percent = (latency_increase / idle_mean) * 100 if idle_mean > 0 else 0

        metrics_text = (
            f"Mean Idle Latency: {idle_mean:.2f}ms\n"
            f"Mean Loaded Latency: {loaded_mean:.2f}ms\n"
            f"Latency Increase: {latency_increase:.2f}ms ({latency_increase_percent:.1f}%)"
        )

        fig.text(0.5, 0.01, metrics_text, ha='center', fontsize=12, bbox=dict(facecolor='white', alpha=0.8))

    # Set the figure title
    fig.suptitle(f"{test_name} - Latency Analysis", fontsize=14)
    fig.tight_layout(rect=[0, 0.05, 1, 0.95])  # Adjust layout for the metrics text at bottom

    return fig

def plot_throughput_per_http_stream(selected_tests, params):
    """Plot per-HTTP stream visualization"""
    # Get the first (and only) test
    test_name = list(selected_tests.keys())[0]
    test_data = selected_tests[test_name]["data"]

    test_type = test_data["test_type"]
    byte_list = test_data["byte_list"]
    source_times = test_data["source_times"]
    begin_time = test_data["begin_time"]

    # Create a figure
    fig = Figure(figsize=(14, 8))
    ax = fig.add_subplot(1, 1, 1)

    # Prepare data based on test type
    if test_type == "upload":
        # Use the normalized current_position_list
        # This would normally come from hf.normalize_current_position_list,
        # but we've already done the normalization when loading the test
        normalized_data = byte_list
    else:  # download
        normalized_data = byte_list

    # Plot each HTTP stream
    colors = plt.cm.tab10(np.linspace(0, 1, len(normalized_data)))

    for i, stream in enumerate(normalized_data):
        stream_id = stream['id']
        progress = stream['progress']

        # Extract time and bytecount data
        times = [(p['time'] - begin_time) / 1000 for p in progress]  # Convert to seconds
        bytecounts = [p.get('bytecount', 0) for p in progress]

        # Plot the stream data
        ax.plot(times, bytecounts, label=f'Stream {stream_id}',
               color=colors[i], alpha=0.7, marker='o', markersize=3, linestyle='-')

    # Add labels and legend
    ax.set_xlabel('Time (seconds)')
    ax.set_ylabel('Bytecount')
    ax.set_title(f'Per-HTTP Stream Data ({test_type.title()} Test)')

    # Create a custom legend with fewer entries if there are many streams
    if len(normalized_data) > 10:
        # Show only a subset of streams in the legend
        handles, labels = ax.get_legend_handles_labels()
        ax.legend(handles[:10], labels[:10], loc='upper left',
                 title=f'Showing 10 of {len(normalized_data)} streams')
    else:
        ax.legend(loc='upper left')

    ax.grid(True, alpha=0.3)

    # Set the figure title
    fig.suptitle(f"{test_name} - HTTP Stream Analysis", fontsize=14)

    # Adjust layout for better spacing
    fig.tight_layout(rect=[0, 0, 0.9, 0.95])  # Make room for the legend and title

    return fig