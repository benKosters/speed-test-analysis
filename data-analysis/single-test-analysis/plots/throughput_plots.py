
"""
1) plot_throughput_and_http_streams: Plots the throughput data with HTTP streams in a Gantt chart grouped by socket on a plot beneath it

2) plot_throughput_scatter_max_flows_only: Plots the throughput data with a scatter plot overlay, but only for points where num_flows are contributing to the bytecount
3) plot_throughput_rema_separated_by_flows: Plots the throughput data with a scatter plot overlay, classified by the number of flows contributing(ALL flows represented)
4) plot_throughput_rema_separated_by_flows_socket_grouped: Same as #3, but Gantt chart groups streams by socket instead of showing each stream individually
5) plot_throughput_max_flow_only: Plots raw throughput (no REMA) only where maximum flows are contributing, with options for scatter, line, or both

6) plot_rema_per_http_stream: Plots the REMA lines for each HTTP stream, useful for visualizing spikes in the bytecount
7) plot_aggregated_bytecount: Plots only the aggregated bytecounts across all HTTP streams for a clean view of total system throughput

"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# import ploting_utilities.py in the same directory
# import plotting_utilities
import plots as plotting_utilities


"""
Builds two plots:
1) A time series chart showing the throughput value over the duration of the test.
2) A Gantt chart of the HTTP streams, grouped by socket ID (each socket gets one row).
"""
def plot_throughput_and_http_streams(plot_data, title=None):
    # Extract parameters from plot_data
    df = pd.DataFrame(plot_data["throughput_results"])
    source_times = plot_data["source_times"]
    begin_time = plot_data["begin_time"]
    save = plot_data["save"]
    base_path = plot_data["base_path"]
    if 'throughput' in df.columns:
        # Create the figure with two subplots, stacked vertically
        df['throughput_ema'] = df['throughput'].ewm(alpha=0.1, adjust=False).mean()
        fig, (ax1, ax2) = plt.subplots(2, 1, height_ratios=[3, 1], figsize=(10, 8))

        # Plot throughput on the top subplot
        ax1.plot(df['time'], df['throughput_ema'], color='red', linestyle='--')
        ax1.set_xlabel('Time (seconds)')
        ax1.set_ylabel('Throughput (Mbps)')
        ax1.set_ylim(0, 5000) #set y-axis for consistency

        # Add title
        if title:
            ax1.set_title(title)
        else:
            server = plot_data.get("server", "Unknown").capitalize()
            test_type = plot_data.get("test_type", "Test").capitalize()
            bin_size = plot_data.get("bin_size_ms", "N/A")
            ax1.set_title(f'REMA Throughput: {server}, {test_type} with {bin_size}ms Bin Size')

        ax1.legend()

        # -------------------  Sockets Gantt Chart (Bottom Subplot) - Grouped by Socket -------------------
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
        colors = plt.cm.Paired(np.linspace(0, 1, len(unique_sockets)))
        socket_colors = dict(zip(unique_sockets, colors))
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

        ax2.set_xlabel('Time (seconds)')
        ax2.set_ylabel('Socket ID')
        ax2.set_yticks(range(len(sorted_sockets)))
        ax2.set_yticklabels([f'Socket {s}' if s != 'no_socket' else 'No Socket' for s in sorted_sockets], fontsize=8)
        ax2.grid(True, axis='y', linestyle='--', alpha=0.3)

        # Create legend for sockets
        socket_handles = []
        socket_labels = []
        for socket_id in sorted_sockets:
            color = socket_colors[socket_id]
            socket_handles.append(plt.Line2D([0], [0], color=color, lw=2))
            socket_labels.append(f'Socket {socket_id}' if socket_id != 'no_socket' else 'No Socket')

        ax2.legend(handles=socket_handles, labels=socket_labels, bbox_to_anchor=(1.05, 1), loc='upper left')

        # Align the x-axes of both plots
        ax1.set_xlim(ax2.get_xlim())

        # Adjust spacing between subplots
        plt.tight_layout()
        if save and base_path:
            filename = "throughput_and_sockets.png"
            plotting_utilities.save_figure(fig, base_path, filename)

        plt.show()
    else:
        print("No throughput data available for plotting.")


"""
Plot throughput data with both REMA and a scatter plot, but ONLY for throughput points where num_flows are contributing to the bytecount.
Also includes a sockets Gantt chart below.
"""
def plot_throughput_scatter_max_flows_only(plot_data, start_time=0, end_time=None, title=None):
    # Extract parameters from plot_data
    df = pd.DataFrame(plot_data["throughput_results"])
    source_times = plot_data["source_times"]
    begin_time = plot_data["begin_time"]
    if end_time is None:
        end_time = plot_data["end_time"]
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
    ax1.set_xlabel('Time (seconds)')
    ax1.set_ylabel('Throughput (Mbps)')
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
    ax2.set_xlabel('Time (seconds)')
    ax2.set_ylabel('HTTP Stream ID')
    ax2.set_yticks(range(len(source_times)))
    ax2.set_yticklabels([f'Source {id}' for id in source_times.keys()], fontsize=8)
    ax2.grid(True, axis='y', linestyle='--', alpha=0.3)
    ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

    # Align the x-axes of both plots - important for seeing correlation between throughput and socket activity
    ax1.set_xlim(ax2.get_xlim())

    # Adjust spacing between subplots
    plt.tight_layout()
    plt.show()


"""
Plot of the throughput, but throughput points are classified by the number of flows contributing to the bytecount.
Has the option to add a scatter plot overlay. These points are also classified by the number of flows contributing to the bytecount.
"""
def plot_throughput_rema_separated_by_flows(plot_data, start_time=0, end_time=None, title=None, scatter=False):
    # Extract parameters from plot_data
    throughput_list_dict = plot_data["throughput_by_flows"]
    source_times = plot_data["source_times"]
    begin_time = plot_data["begin_time"]
    save = plot_data["save"]
    base_path = plot_data["base_path"]
    if end_time is None:
        end_time = plot_data["end_time"]

    fig, (ax1, ax2) = plt.subplots(2, 1, height_ratios=[3, 1], figsize=(10, 8))
    flow_colors = {
        1: "#9ecae1",
        2: "#6baed6",
        3: '#4292c6',
        4: "#2171b5",
        5: '#08519c',
        6: "#08306b"
    }

    # Another way of coloring the flows
    # unique_flows = sorted(throughput_list_dict.keys())
    # colors = plt.cm.tab10(np.linspace(0, 0.6, len(unique_flows)))
    # flow_colors = dict(zip(unique_flows, colors))

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
    ax1.set_xlabel('Time (seconds)')
    ax1.set_ylabel('Throughput (Mbps)')
    ax1.set_ylim(0, 3250)

    if title:
        ax1.set_title(title)
    else:
        ax1.set_title("HTTP Level Throughput, Grouped by Number of Concurrent Flows")

    # Create a custom legend for flow counts
    handles = []
    labels = []
    for flow_count in sorted(set(combined_df['flow_count'])):
        color = flow_colors.get(flow_count, 'gray')
        handles.append(plt.Line2D([0], [0], color=color, lw=3))
        labels.append(f'{flow_count} Flows')

    # Place the flow count legend in the upper right
    ax1.legend(handles=handles, labels=labels, bbox_to_anchor=(1.05, 1), loc='upper left')

    # -------------------  Sockets Gantt Chart (Bottom Subplot) -------------------
    # Create color map for unique socket IDs
    unique_sockets = set(info['socket'] for info in source_times.values() if info['socket'] is not None)
    colors = plt.cm.Paired(np.linspace(0, 1, len(unique_sockets)))
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

    ax2.set_xlabel('Time (seconds)')
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
        plotting_utilities.save_figure(fig, base_path, filename)
    plt.show()


"""
Similar to plot_throughput_rema_separated_by_flows(), but the Gantt chart groups HTTP streams by socket.
Each socket gets one row, and all streams using that socket are shown on that row.
"""
def plot_throughput_rema_separated_by_flows_socket_grouped(plot_data, start_time=0, end_time=None, title=None, scatter=False):
    # Extract parameters from plot_data
    throughput_list_dict = plot_data["throughput_by_flows"]
    source_times = plot_data["source_times"]
    begin_time = plot_data["begin_time"]
    save = plot_data["save"]
    base_path = plot_data["base_path"]
    if end_time is None:
        end_time = plot_data["end_time"]

    fig, (ax1, ax2) = plt.subplots(2, 1, height_ratios=[3, 1], figsize=(10, 8))
    # flow_colors = {
    #     1: '#9ecae1',
    #     2: '#6baed6',
    #     3: '#4292c6',
    #     4: '#2171b5',
    #     5: '#08519c',
    #     6: '#08306b'
    # }
    # unique_flows = sorted(throughput_list_dict.keys())
    # colors = plt.cm.Paired(np.linspace(0, 0.6, len(unique_flows)))
    # flow_colors = dict(zip(unique_flows, colors))
    flow_colors = {
        1: 'Blue',
        2: 'DeepSkyBlue',
        3: 'Green',
        4: 'Gold',
        5: 'DarkOrange',
        6: 'Red'
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
    ax1.set_xlabel('Time (seconds)')
    ax1.set_ylabel('Throughput (Mbps)')
    # ax1.set_ylim(0, 5000)
    ax1.set_ylim(0, combined_df['throughput'].max() * 1.1)

    if title:
        ax1.set_title(title)
    else:
        server = plot_data.get("server", "Unknown").capitalize()
        test_type = plot_data.get("test_type", "Test").capitalize()
        bin_size = plot_data.get("bin_size_ms", "N/A")
        ax1.set_title(f'REMA Throughput: {server}, {test_type} with {bin_size}ms Bin Size')

    # Create a custom legend for flow counts
    handles = []
    labels = []
    for flow_count in sorted(set(combined_df['flow_count'])):
        color = flow_colors.get(flow_count, 'gray')
        handles.append(plt.Line2D([0], [0], color=color, lw=3))
        labels.append(f'{flow_count} Flows')

    # Place the flow count legend in the upper right
    ax1.legend(handles=handles, labels=labels, bbox_to_anchor=(1.05, 1), loc='upper left')

    # -------------------  Sockets Gantt Chart (Bottom Subplot) - Grouped by Socket -------------------
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
    colors = plt.cm.Paired(np.linspace(0, 1, len(unique_sockets)))
    socket_colors = dict(zip(unique_sockets, colors))
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

    ax2.set_xlabel('Time (seconds)')
    ax2.set_ylabel('Socket ID')
    ax2.set_yticks(range(len(sorted_sockets)))
    ax2.set_yticklabels([f'Socket {s}' if s != 'no_socket' else 'No Socket' for s in sorted_sockets], fontsize=8)
    ax2.grid(True, axis='y', linestyle='--', alpha=0.3)

    # Create legend for sockets
    socket_handles = []
    socket_labels = []
    for socket_id in sorted_sockets:
        color = socket_colors[socket_id]
        socket_handles.append(plt.Line2D([0], [0], color=color, lw=2))
        socket_labels.append(f'Socket {socket_id}' if socket_id != 'no_socket' else 'No Socket')

    ax1.set_xlim(start_time, end_time)
    ax2.set_xlim(start_time, end_time)

    plt.tight_layout()
    if save and base_path:
        filename = "throughput_rema_separated_by_flows_socket_grouped.png"
        plotting_utilities.save_figure(fig, base_path, filename)
    plt.show()


def plot_throughput_max_flow_only(plot_data, start_time=0, end_time=None, title=None, plot_type='both'):
    """
    Plot throughput where maximum number of flows are contributing.

    Args:
        plot_type: 'line', 'scatter', or 'both' to control what is displayed
    """
    # Extract parameters from plot_data
    throughput_list_dict = plot_data["throughput_by_flows"]
    source_times = plot_data["source_times"]
    begin_time = plot_data["begin_time"]
    save = plot_data["save"]
    base_path = plot_data["base_path"]
    if end_time is None:
        end_time = plot_data["end_time"]

    fig, (ax1, ax2) = plt.subplots(2, 1, height_ratios=[3, 1], figsize=(10, 8))

    # Find the maximum flow count
    max_flow_count = max(throughput_list_dict.keys())

    # Colors for scatter and line
    scatter_color = 'Blue'
    line_color = 'Red'

    # Create a DataFrame with only the maximum flow count data
    combined_data = []
    if max_flow_count in throughput_list_dict:
        for entry in throughput_list_dict[max_flow_count]:
            if start_time <= entry['time'] <= end_time:
                combined_data.append({
                    'time': entry['time'],
                    'throughput': entry['throughput'],
                    'flow_count': max_flow_count
                })

    combined_df = pd.DataFrame(combined_data).sort_values(by='time').reset_index(drop=True)

    if len(combined_df) > 0:
        # -------------------  Throughput Plot (Top Subplot) -------------------
        if plot_type in ['scatter', 'both']:
            ax1.scatter(
                combined_df['time'],
                combined_df['throughput'],
                color=scatter_color,
                s=10,
                alpha=0.6
                # label=f'{max_flow_count} Flows (scatter)'
            )

        if plot_type in ['line', 'both']:
            ax1.plot(
                combined_df['time'],
                combined_df['throughput'],
                color=line_color,
                linewidth=1.5,
                linestyle='--'
                #label=f'{max_flow_count} Flows (line)'
            )

        # Add labels, title, and legend
        ax1.set_xlabel('Time (seconds)')
        ax1.set_ylabel('Throughput (Mbps)')
        ax1.set_ylim(0, combined_df['throughput'].max ()* 1.1) #so the y-aix is slightly higher... cool trick

        if title:
            ax1.set_title(title)
        else:
            server = plot_data.get("server", "Unknown").capitalize()
            test_type = plot_data.get("test_type", "Test").capitalize()
            bin_size = plot_data.get("bin_size_ms", "N/A")
            ax1.set_title(f'Throughput (Max {max_flow_count} Flows Only): {server}, {test_type} with {bin_size}ms Bin Size')

        ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

    else:
        ax1.text(0.5, 0.5, 'No data available for maximum flow count',
                horizontalalignment='center', verticalalignment='center',
                transform=ax1.transAxes)
        ax1.set_xlabel('Time (seconds)')
        ax1.set_ylabel('Throughput (Mbps)')

    # -------------------  Sockets Gantt Chart (Bottom Subplot) - Grouped by Socket -------------------
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
    colors = plt.cm.Paired(np.linspace(0, 1, len(unique_sockets)))
    socket_colors = dict(zip(unique_sockets, colors))
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

    ax2.set_xlabel('Time (seconds)')
    ax2.set_ylabel('Socket ID')
    ax2.set_yticks(range(len(sorted_sockets)))
    ax2.set_yticklabels([f'Socket {s}' if s != 'no_socket' else 'No Socket' for s in sorted_sockets], fontsize=8)
    ax2.grid(True, axis='y', linestyle='--', alpha=0.3)

    # Create legend for sockets
    socket_handles = []
    socket_labels = []
    for socket_id in sorted_sockets:
        color = socket_colors[socket_id]
        socket_handles.append(plt.Line2D([0], [0], color=color, lw=2))
        socket_labels.append(f'Socket {socket_id}' if socket_id != 'no_socket' else 'No Socket')

    ax1.set_xlim(start_time, end_time)
    ax2.set_xlim(start_time, end_time)

    plt.tight_layout()
    if save and base_path:
        filename = "throughput_max_flow_only.png"
        plotting_utilities.save_figure(fig, base_path, filename)
    plt.show()

