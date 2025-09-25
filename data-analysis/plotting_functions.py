"""
The functions defined in this file are ucan be called to plot various graphs to vizualize important data collected from Netlog data (mostly throughput).

The following functions are defined:
1) ensure_plot_dir: Ensures that the plot directory exists - used when we need to save the plots to their corresponding tests
2) save_figure: Saves the figure to the plot_images directory if it doesn't already exist

3) traditional_rema_throughput_plot: Legacy method of plotting throughput used by A and A -- this is not anymore, but kept just in case
4) plot_subsection_of_throughput: Plots a subsection of the throughput data for a specific time interval
5) plot_throughput_and_http_streams: Plots the throughput data with HTTP streams in a Gantt chart on a plot beneath it

6) plot_throughput_scatter_max_flows_only: Plots the throughput data with a scatter plot overlay, but only for points where num_flows are contributing to the bytecount
7) plot_throughput_scatter_max_and_one_fewer_flows: Plots the throughput data with a scatter plot overlay, but only for points where num_flows and num_flows - 1 are contributing to the bytecount
8) plot_throughput_rema_separated_by_flows: Plots the throughput data with a scatter plot overlay, classified by the number of flows contributing(ALL flows represented)

9) plot_rema_per_http_stream: Plots the REMA lines for each HTTP stream, useful for visualizing spikes in the bytecount
10) plot_aggregated_bytecount: Plots only the aggregated bytecounts across all HTTP streams for a clean view of total system throughput
"""


import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import argparse
import os
import json
import sys
import argparse

"""
Helper functions for saving these plots...
#FIXME - move these to helper_functions.py?
"""
def ensure_plot_dir(base_path):
    #If the plot_images directory does not exist in the directory that the test resides in, create it
    plot_dir = os.path.join(base_path, "plot_images")
    if not os.path.exists(plot_dir):
        os.makedirs(plot_dir)
        print(f"Created directory: {plot_dir}")
    return plot_dir

def save_figure(fig, base_path, filename):
    #Save a figure to the plot_images directory if it doesn't already exist.
    plot_dir = ensure_plot_dir(base_path)
    filepath = os.path.join(plot_dir, filename)

    # If the file already exists, don't overwrite it - just keep the current one
    if os.path.exists(filepath):
        print(f"File already exists, not saving: {filepath}")
        return False

    # Otherwise, save the plot
    fig.savefig(filepath, dpi=300, bbox_inches='tight')
    print(f"Saved plot to: {filepath}")
    return True

"""
Old REMA plot used by A and A. -- not used anymore
"""
def traditional_rema_throughput_plot(df, title = None, save = False, base_path = None):
    if 'throughput' in df.columns:
        df['throughput_ema'] = df['throughput'].ewm(alpha=0.1, adjust=False).mean()
        # Plot throughput over time
        plt.figure()
        plt.plot(df['time'], df['throughput_ema'], color='red', linestyle='--')
        plt.xlabel('Time (in seconds)')
        plt.ylabel('Throughput (in Mbps)')
        #plt.title(f"{args.base_path.split('/')[-1]}")
        plt.legend()
        #plt.ylim(20, 250)  # Set consistent y-axis range
        plt.ylim(50, 200)  # for testing...

        # plt.savefig(f"plots/{args.base_path.split('/')[-1]}.jpg")
        # print(f"{args.base_path.split('/')[-1]}.jpg")
        if save and base_path:
            if title:
                filename = f"{title.replace(' ', '_').replace(',', '')}.png"
            else:
                filename = "old_throughput_plot.png"

            save_figure(fig, base_path, filename)
        plt.show()
    else:
        print("No throughput data available for plotting.")

"""
This plotting function is used to visualize the throughput data for a specific time interval within the test.
This way we can zoom in on a specific time interval of interest so that we can see specific points in more detail.
At this point in time, this graph will not be used in a final analysis.
"""
def plot_subsection_of_throughput(df, start_time, end_time, save = False, base_path = None):
    # Filter the DataFrame to include only rows within the specified timeframe
    filtered_df = df[(df['time'] >= start_time) & (df['time'] <= end_time)].copy()
    print(f"Filtered DataFrame length: {len(filtered_df)}")

    if 'throughput' in filtered_df.columns:
        filtered_df['throughput_ema'] = filtered_df['throughput'].ewm(alpha=0.1, adjust=False).mean()
        plt.figure()

        #---------finding the largest time difference between points---------
        #FIXME - turn this portion into a separate function
        if len(filtered_df) > 1:  # Ensure there are at least two points to calculate differences
            time_differences = filtered_df['time'].diff().dropna()  # Calculate differences and drop NaN
            max_time_diff = time_differences.max()  # Find the maximum difference
            print(f"\nLargest time difference between points: {max_time_diff:.3f} seconds")
        else:
            print("\nNot enough data points to calculate time differences.")


        # Build a scatter plot to show the individual throughput data points
        plt.scatter(
            filtered_df['time'],
            filtered_df['throughput'],
            color='blue',
            s=10,  # Point size
            alpha=0.7,     # Transparency
            label='Throughput Points'
        )

        # Overlay of the REMA throughput
        plt.plot(
            filtered_df['time'],
            filtered_df['throughput_ema'],
            color='red',
            linestyle='--',
            linewidth=1.5,
            label='REMA Smoothed'
        )

        plt.xlabel('Time (in seconds)')
        plt.ylabel('Throughput (in Mbps)')
        plt.title(f"Filtered Throughput (Timeframe: {start_time}s to {end_time}s)")
        plt.legend()
        #plt.ylim(50, 250)  # Same ylim as traditional_rema_throughput_plot -- don't set interval since some throughput values are very high

        plt.tight_layout()
        if save and base_path:
            filename = "throughput_over_small_interval.png"

            save_figure(fig, base_path, filename)
        plt.show()
    else:
        print("No throughput data available for plotting.")


"""
Builds two plots:
1) A time series chart showing the throughput value over the duration of the test.
2) A Gantt chart of the HTTP streams, where each stream is color-coded by its socket ID.
"""
def plot_throughput_and_http_streams(df, title=None, source_times=None, begin_time=None, save = False, base_path = None):
    if 'throughput' in df.columns:
        # Create the figure with two subplots, stacked vertically
        df['throughput_ema'] = df['throughput'].ewm(alpha=0.1, adjust=False).mean()
        fig, (ax1, ax2) = plt.subplots(2, 1, height_ratios=[3, 1], figsize=(10, 8))

        # Plot throughput on the top subplot
        ax1.plot(df['time'], df['throughput_ema'], color='red', linestyle='--', label='REMA Throughput')
        ax1.set_xlabel('Time (in seconds)')
        ax1.set_ylabel('Throughput (in Mbps)')

        ax1.legend()
        ax1.set_ylim(0, 1000) #set y-axis for consistency

        # Create color map for unique socket IDs
        unique_sockets = set(info['socket'] for info in source_times.values() if info['socket'] is not None)
        colors = plt.cm.rainbow(np.linspace(0, 1, len(unique_sockets)))
        socket_colors = dict(zip(unique_sockets, colors)) #forms a dictionary where the key is the socket ID, and the value is the color.

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

            # Start and end time labels for each source ID - this makes the plot too cluttered...
            # ax2.text(start_sec, y_offset, f"{start_sec:.4f}s", color=color, fontsize=8, ha='right', va='center')
            # ax2.text(end_sec, y_offset, f"{end_sec:.4f}s", color=color, fontsize=8, ha='left', va='center')
            y_offset += 1

        ax2.set_xlabel('Time (in seconds)')
        ax2.set_ylabel('HTTP Stream ID')
        ax2.set_yticks(range(len(source_times)))
        # ax2.set_yticklabels([f'Source {id}' for id in source_times.keys()])
        ax2.set_yticklabels([f'Stream {id}' for id in source_times.keys()], fontsize=8)
        ax2.grid(True, axis='y', linestyle='--', alpha=0.3)
        ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

        # Align the x-axes of both plots
        ax1.set_xlim(ax2.get_xlim())

        # Adjust spacing between subplots
        plt.tight_layout()
        if save and base_path:
            filename = "throughput_and_sockets.png"
            save_figure(fig, base_path, filename)

        plt.show()
    else:
        print("No throughput data available for plotting.")


"""
Plot throughput data with both REMA and a scatter plot, but ONLY for throughput points where num_flows are contributing to the bytecount.
Also includes a sockets Gantt chart below.
#FIXME: remove the time range from the arguments, remove the title for the upper plot.
"""
def plot_throughput_scatter_max_flows_only(df, start_time, end_time, source_times, begin_time, title=None):
    # Filter the DataFrame for the specified time range
    filtered_df = df[(df['time'] >= start_time) & (df['time'] <= end_time)].copy()

    # Calculate the REMA for the filtered data
    filtered_df['throughput_ema'] = filtered_df['throughput'].ewm(alpha=0.1, adjust=False).mean()

    fig, (ax1, ax2) = plt.subplots(2, 1, height_ratios=[3, 1], figsize=(12, 8))

    # ------------------- Throughput Scatter Plot (Top Subplot) -------------------
    # Scatter plot for full num_flows
    ax1.scatter(
        filtered_df['time'],
        filtered_df['throughput'],
        color='blue',
        s=10,
        alpha=0.7,
    )

    # REMA line for the filtered data
    ax1.plot(
        filtered_df['time'],
        filtered_df['throughput_ema'],
        color='red',
        linestyle='--',
        linewidth=1.5,
    )

    # Add labels, title, and legend for the throughput plot
    ax1.set_xlabel('Time (in seconds)')
    ax1.set_ylabel('Throughput (in Mbps)')
    plot_title = f"Throughput Scatter (Full Flows Only) - Timeframe: {start_time}s to {end_time}s"
    ax1.set_title(plot_title)
    ax1.legend()

    # ------------------- Sockets Gantt Chart (Bottom Subplot) -------------------
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
    ax2.set_xlabel('Time (in seconds)')
    ax2.set_ylabel('HTTP Stream ID')
    ax2.set_yticks(range(len(source_times)))
    ax2.set_yticklabels([f'Source {id}' for id in source_times.keys()], fontsize=8)
    ax2.grid(True, axis='y', linestyle='--', alpha=0.3)
    ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

    # Align the x-axes of both plots - important for seeing correlation between throughput and socket activity
    ax1.set_xlim(ax2.get_xlim())

    # Adjust spacing between subplots
    plt.tight_layout()
    if save and base_path:
        filename = "throughput_rema_and_scatter_max_flows_only.png"

        save_figure(fig, base_path, filename)
    plt.show()

"""
Plots the throughout as a scatter plot with points where num_flows are contributing are in blue, and num_flows - 1 are in green.
Combines both of these scatter plots in one REMA line.
Also includes a the Gantt chart of the HTTP streams below.

This function is only used for num_flows and num_flows - 1... to see ALL points classified by the number of flows contributing,
see plot_throughput_rema_separated_by_flows.
"""
def plot_throughput_scatter_max_and_one_fewer_flows(df, less_flows_df, start_time, end_time, source_times, begin_time):
    # Combine the two DataFrames for the REMA line
    combined_df = pd.concat([df, less_flows_df]).sort_values(by='time').reset_index(drop=True)
    combined_df['throughput_ema'] = combined_df['throughput'].ewm(alpha=0.1, adjust=False).mean()

    # Filter the DataFrames for the specified time range
    filtered_df = df[(df['time'] >= start_time) & (df['time'] <= end_time)].copy()
    filtered_less_flows_df = less_flows_df[(less_flows_df['time'] >= start_time) & (less_flows_df['time'] <= end_time)].copy()
    filtered_combined_df = combined_df[(combined_df['time'] >= start_time) & (combined_df['time'] <= end_time)].copy()

    # Create figure with two subplots, stacked vertically similar to the other functions where the streams are plotted
    fig, (ax1, ax2) = plt.subplots(2, 1, height_ratios=[3, 1], figsize=(12, 8))

    # ------------------- Throughput Plot (Top Subplot) -------------------
    # Scatter plot for num_flows
    ax1.scatter(
        filtered_df['time'],
        filtered_df['throughput'],
        color='blue',
        s=10,
        alpha=0.7,
        label='Throughput (num_flows)'
    )

    # Scatter plot for num_flows - 1
    ax1.scatter(
        filtered_less_flows_df['time'],
        filtered_less_flows_df['throughput'],
        color='green',
        s=10,
        alpha=0.7,
        label='Throughput (num_flows - 1)'
    )

    # REMA line for combined data
    ax1.plot(
        filtered_combined_df['time'],
        filtered_combined_df['throughput_ema'],
        color='red',
        linestyle='--',
        linewidth=1.5,
        label='REMA Smoothed (Combined)'
    )

    # Add labels, title, and legend for the throughput plot
    ax1.set_xlabel('Time (in seconds)')
    ax1.set_ylabel('Throughput (in Mbps)')
    ax1.set_title(f"Throughput for num_flows and num_flows - 1 (Timeframe: {start_time}s to {end_time}s)")
    ax1.legend()

    # ------------------- Sockets Gantt Chart (Bottom Subplot) -------------------
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
    ax2.set_xlabel('Time (in seconds)')
    ax2.set_ylabel('HTTP Stream ID')
    ax2.set_yticks(range(len(source_times)))
    ax2.set_yticklabels([f'Stream {id}' for id in source_times.keys()], fontsize=8)
    ax2.grid(True, axis='y', linestyle='--', alpha=0.3)
    ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

    # Align the x-axes of both plots
    ax1.set_xlim(ax2.get_xlim())

    # Adjust spacing between subplots
    plt.tight_layout()
    if save and base_path:
        filename = "scatterplot_with_two_flow_groups.png"
        save_figure(fig, base_path, filename)
    plt.show()


"""
Plot of the throughput, but throughput points are classified by the number of flows contributing to the bytecount.
Has the option to add a scatter plot overlay. These points are also classified by the number of flows contributing to the bytecount.
"""
def plot_throughput_rema_separated_by_flows(throughput_list_dict, start_time, end_time, source_times, begin_time, title=None, scatter=False, save=False, base_path=None):

    fig, (ax1, ax2) = plt.subplots(2, 1, height_ratios=[3, 1], figsize=(10, 8))
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
    for flow_count, throughput_list in throughput_list_dict.items():
        for entry in throughput_list:
            if start_time <= entry['time'] <= end_time:
                combined_data.append({
                    'time': entry['time'],
                    'throughput': entry['throughput'],
                    'flow_count': flow_count
                })

    combined_df = pd.DataFrame(combined_data).sort_values(by='time').reset_index(drop=True)

    combined_df['throughput_ema'] = combined_df['throughput'].ewm(alpha=0.1, adjust=False).mean()

    # -------------------  Throughput Plot with color-coded segments (Top Subplot) -------------------
    if scatter:
        for flow_count in sorted(throughput_list_dict.keys()):
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

    # Add labels, title, and legend
    ax1.set_xlabel('Time (in seconds)')
    ax1.set_ylabel('Throughput (in Mbps)')
    ax1.set_ylim(20, 250)

    # if title:
    #     ax1.set_title(title)
    # else:
    #     ax1.set_title(f"Throughput REMA with Flow Count Coloring ({start_time}s to {end_time}s)")

    # Create a custom legend for flow counts
    handles = []
    labels = []
    for flow_count in sorted(set(combined_df['flow_count'])):
        color = flow_colors.get(flow_count, 'gray')
        handles.append(plt.Line2D([0], [0], color=color, lw=3))
        labels.append(f'{flow_count} Flows')

    # Place the flow count legend in the upper right
    ax1.legend(handles=handles, labels=labels, loc='upper right')

    # -------------------  Sockets Gantt Chart (Bottom Subplot) -------------------
    # Create color map for unique socket IDs
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

    ax1.set_xlim(start_time, end_time)
    ax2.set_xlim(start_time, end_time)

    plt.tight_layout()
    if save and base_path:
        filename = "throughput_rema_separated_by_flows.png"
        save_figure(fig, base_path, filename)
    plt.show()

"""
Plots only the aggregated bytecounts across all HTTP streams. This gives a clean view of total system throughput.
"""
def plot_aggregated_bytecount(data, test_type=None, title=None, log_scale=False, save=False, base_path=None, begin_time=None, source_times=None):
    """
    Plot aggregated bytecounts across all HTTP streams for both upload and download tests.

    Args:
        data: For upload tests, this is normalized_current_position_list
              For download tests, this is byte_list (from normalize_test_data)
        test_type: "upload" or "download" - if None, will auto-detect
        title: Custom title for the plot
        log_scale: Whether to use log scale on y-axis
        save: Whether to save the plot
        base_path: Path to save the plot
        begin_time: Start time in milliseconds for normalizing download data timestamps
        source_times: Dictionary containing stream timing and socket information for Gantt chart
    """
    stream_data = {}

    # Auto-detect test type if not provided
    if test_type is None:
        # Check if data has 'current_position' field (upload) or 'bytecount' field (download)
        if data and data[0].get('progress') and data[0]['progress'][0].get('current_position') is not None:
            test_type = "upload"
        else:
            test_type = "download"

    print(f"Plotting aggregated bytecounts for {test_type} test")

    # For download tests, find begin_time if not provided
    if test_type == "download" and begin_time is None:
        all_times = []
        for entry in data:
            for item in entry['progress']:
                all_times.append(int(item['time']))
        begin_time = min(all_times) if all_times else 0
        print(f"Auto-detected begin_time for download normalization: {begin_time}")

    # Process each stream to get individual stream data
    for entry in data:
        stream_id = entry['id']
        progress = entry['progress']

        # Combine bytecounts with the same timestamp
        combined_data = {}

        if test_type == "upload":
            # For upload, check if data is already normalized (has 'bytecount') or raw (has 'current_position')
            if 'bytecount' in progress[0]:
                # Data is already normalized from normalize_current_position_list
                for item in progress:
                    timestamp = float(item['time'])
                    bytecount = item.get('bytecount', 0)
                    if timestamp in combined_data:
                        combined_data[timestamp] += bytecount
                    else:
                        combined_data[timestamp] = bytecount
            else:
                # Data is raw current_position data, convert to bytecounts
                prev_position = 0
                for item in progress:
                    timestamp = float(item['time'])
                    current_position = item.get('current_position', 0)
                    bytecount = current_position - prev_position
                    prev_position = current_position

                    if timestamp in combined_data:
                        combined_data[timestamp] += bytecount
                    else:
                        combined_data[timestamp] = bytecount
        else:
            # For download, use existing bytecounts and normalize timestamps
            for item in progress:
                # Normalize timestamp: convert from milliseconds to seconds relative to begin_time
                timestamp = (int(item['time']) - begin_time) / 1000.0
                bytecount = item.get('bytecount', 0)
                if timestamp in combined_data:
                    combined_data[timestamp] += bytecount
                else:
                    combined_data[timestamp] = bytecount

        df = pd.DataFrame(list(combined_data.items()), columns=['time', 'bytecount'])
        df.sort_values(by='time', inplace=True)  # Ensure data is sorted by time
        df['rema'] = df['bytecount'].ewm(alpha=0.1, adjust=False).mean()  # Calculate REMA

        # Store the processed DataFrame for the stream ID
        stream_data[stream_id] = df

    # Create aggregated data by summing bytecounts across all streams at each timestamp
    all_timestamps = set()
    for df in stream_data.values():
        all_timestamps.update(df['time'].values)

    aggregated_data = {}
    for timestamp in all_timestamps:
        total_bytecount = 0
        for df in stream_data.values():
            # Find the closest timestamp in this stream's data
            closest_idx = (df['time'] - timestamp).abs().idxmin()
            if abs(df.loc[closest_idx, 'time'] - timestamp) < 0.1:  # Within 0.1 seconds
                total_bytecount += df.loc[closest_idx, 'bytecount']
        aggregated_data[timestamp] = total_bytecount

    # Create DataFrame for aggregated data
    aggregated_df = pd.DataFrame(list(aggregated_data.items()), columns=['time', 'bytecount'])
    aggregated_df.sort_values(by='time', inplace=True)
    aggregated_df['rema'] = aggregated_df['bytecount'].ewm(alpha=0.1, adjust=False).mean()

    # Create figure with subplots - add Gantt chart if source_times is provided
    if source_times:
        fig, (ax_agg, ax2) = plt.subplots(2, 1, height_ratios=[3, 1], figsize=(12, 8))
    else:
        fig, ax_agg = plt.subplots(figsize=(12, 6))

    # Plot aggregated bytecounts
    ax_agg.plot(aggregated_df['time'], aggregated_df['rema'],
                color='black', linewidth=2, label='Aggregated REMA')
    ax_agg.scatter(aggregated_df['time'], aggregated_df['bytecount'],
                   color='red', s=8, alpha=0.6, label='Raw Data Points')

    ax_agg.set_xlabel('Time (seconds)')
    ax_agg.set_ylabel('Total Bytecount')
    if title:
        ax_agg.set_title(title)
    else:
        ax_agg.set_title(f'Aggregated Bytecounts Across All HTTP Streams ({test_type.title()} Test)')

    ax_agg.legend(loc='upper right')
    ax_agg.grid(True, alpha=0.3)

    if log_scale:
        ax_agg.set_yscale('log')

    # Add HTTP Stream Gantt Chart if source_times is provided
    if source_times:
        # ------------------- HTTP Streams Gantt Chart (Bottom Subplot) -------------------
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
        ax2.set_xlabel('Time (seconds)')
        ax2.set_ylabel('HTTP Stream ID')
        ax2.set_yticks(range(len(source_times)))
        ax2.set_yticklabels([f'Stream {id}' for id in source_times.keys()], fontsize=8)
        ax2.grid(True, axis='y', linestyle='--', alpha=0.3)
        ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

        # Align the x-axes of both plots
        ax_agg.set_xlim(ax2.get_xlim())

    plt.tight_layout()
    if save and base_path:
        filename = f"{test_type}_aggregated_bytecounts.png"
        save_figure(fig, base_path, filename)
    plt.show()

"""
For upload tests only, plots the REMA lines differentiated by each HTTP stream. Used to see spikes in the bytecount for each stream
#FIXME - inconsistency in passing parameters...
"""
def plot_rema_per_http_stream(data, test_type=None, title=None, log_scale=False, save=False, base_path=None, begin_time=None, source_times=None):
    """
    Plot REMA lines for each HTTP stream for both upload and download tests.

    Args:
        data: For upload tests, this is normalized_current_position_list
              For download tests, this is byte_list (from normalize_test_data)
        test_type: "upload" or "download" - if None, will auto-detect
        title: Custom title for the plot
        log_scale: Whether to use log scale on y-axis
        save: Whether to save the plot
        base_path: Path to save the plot
        begin_time: Start time in milliseconds for normalizing download data timestamps
        source_times: Dictionary containing stream timing and socket information for Gantt chart
    """
    stream_data = {}

    # Auto-detect test type if not provided
    if test_type is None:
        # Check if data has 'current_position' field (upload) or 'bytecount' field (download)
        if data and data[0].get('progress') and data[0]['progress'][0].get('current_position') is not None:
            test_type = "upload"
        else:
            test_type = "download"

    print(f"Plotting individual HTTP streams for {test_type} test")

    # For download tests, find begin_time if not provided
    if test_type == "download" and begin_time is None:
        all_times = []
        for entry in data:
            for item in entry['progress']:
                all_times.append(int(item['time']))
        begin_time = min(all_times) if all_times else 0
        print(f"Auto-detected begin_time for download normalization: {begin_time}")

    # for each stream...
    for entry in data:
        stream_id = entry['id']
        progress = entry['progress']

        # Combine bytecounts with the same timestamp
        combined_data = {}

        if test_type == "upload":
            # For upload, check if data is already normalized (has 'bytecount') or raw (has 'current_position')
            if 'bytecount' in progress[0]:
                # Data is already normalized from normalize_current_position_list
                for item in progress:
                    timestamp = float(item['time'])
                    bytecount = item.get('bytecount', 0)
                    if timestamp in combined_data:
                        combined_data[timestamp] += bytecount
                    else:
                        combined_data[timestamp] = bytecount
            else:
                # Data is raw current_position data, convert to bytecounts
                prev_position = 0
                for item in progress:
                    timestamp = float(item['time'])
                    current_position = item.get('current_position', 0)
                    bytecount = current_position - prev_position
                    prev_position = current_position

                    if timestamp in combined_data:
                        combined_data[timestamp] += bytecount
                    else:
                        combined_data[timestamp] = bytecount
        else:
            # For download, use existing bytecounts and normalize timestamps
            for item in progress:
                # Normalize timestamp: convert from milliseconds to seconds relative to begin_time
                timestamp = (int(item['time']) - begin_time) / 1000.0
                bytecount = item.get('bytecount', 0)
                if timestamp in combined_data:
                    combined_data[timestamp] += bytecount
                else:
                    combined_data[timestamp] = bytecount

        df = pd.DataFrame(list(combined_data.items()), columns=['time', 'bytecount'])
        df.sort_values(by='time', inplace=True)  # Ensure data is sorted by time
        df['rema'] = df['bytecount'].ewm(alpha=0.1, adjust=False).mean()  # Calculate REMA

        # Store the processed DataFrame for the stream ID
        stream_data[stream_id] = df

    # Create figure with subplots - add Gantt chart if source_times is provided
    if source_times:
        fig, (ax1, ax2) = plt.subplots(2, 1, height_ratios=[3, 1], figsize=(12, 10))
    else:
        fig, ax1 = plt.subplots(figsize=(12, 8))

    # Plot REMA lines for each source ID and store the line objects
    lines = {}
    for stream_id, df in stream_data.items():
        line, = ax1.plot(df['time'], df['rema'], label=f"Stream {stream_id}")
        lines[stream_id] = line

    if log_scale:
        ax1.set_yscale('log') # set to log... this is just for experimenting, it is mostly helpful to NOT have a log scale

    # Add labels, title, and legend
    ax1.set_xlabel('Time (seconds)')
    ax1.set_ylabel('Bytecount (REMA)')
    if title:
        ax1.set_title(title)
    else:
        ax1.set_title(f'REMA Lines for Each HTTP Stream ({test_type.title()} Test)')

    # Create an interactive legend
    legend = ax1.legend(loc='upper right', bbox_to_anchor=(1.15, 1), fontsize='small', title="Streams")
    legend_lines = legend.get_lines()

    # Add interactivity to the legend -  click on the legend to toggle visibility of the corresponding line
    #Written with the help of Claude
    def on_legend_click(event):
        for legend_line, (stream_id, line) in zip(legend_lines, lines.items()):
            if event.artist == legend_line:
                visible = not line.get_visible()
                line.set_visible(visible)  # Toggle visibility
                legend_line.set_alpha(1.0 if visible else 0.2)  # Dim the legend entry if hidden
                fig.canvas.draw()

    # Connect the legend click event to the toggle function
    fig.canvas.mpl_connect('pick_event', on_legend_click)

    for legend_line in legend_lines:
        legend_line.set_picker(True)

    # Add HTTP Stream Gantt Chart if source_times is provided
    if source_times:
        # ------------------- HTTP Streams Gantt Chart (Bottom Subplot) -------------------
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
        ax2.set_xlabel('Time (seconds)')
        ax2.set_ylabel('HTTP Stream ID')
        ax2.set_yticks(range(len(source_times)))
        ax2.set_yticklabels([f'Stream {id}' for id in source_times.keys()], fontsize=8)
        ax2.grid(True, axis='y', linestyle='--', alpha=0.3)
        ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

        # Align the x-axes of both plots
        ax1.set_xlim(ax2.get_xlim())

    plt.tight_layout()
    if save and base_path:
        filename = f"{test_type}_individual_http_streams.png"
        save_figure(fig, base_path, filename)
    plt.show()

    # Ensure the plot window is centered on the screen
    fig_manager = plt.get_current_fig_manager()
    try:
        # For TkAgg backend
        fig_manager.window.wm_geometry("+0+0")
        screen_width = fig_manager.window.winfo_screenwidth()
        screen_height = fig_manager.window.winfo_screenheight()
        window_width = fig.get_size_inches()[0] * fig.dpi
        window_height = fig.get_size_inches()[1] * fig.dpi
        x = int((screen_width - window_width) / 2)
        y = int((screen_height - window_height) / 2)
        fig_manager.window.wm_geometry(f"+{x}+{y}")
    except AttributeError:
        # For other backends, fallback to default behavior
        pass
