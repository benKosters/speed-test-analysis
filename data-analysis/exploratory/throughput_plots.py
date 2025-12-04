
"""
1) plot_throughput_and_http_streams: Plots the throughput data with HTTP streams in a Gantt chart on a plot beneath it

2) plot_throughput_scatter_max_flows_only: Plots the throughput data with a scatter plot overlay, but only for points where num_flows are contributing to the bytecount
3) plot_throughput_scatter_max_and_one_fewer_flows: Plots the throughput data with a scatter plot overlay, but only for points where num_flows and num_flows - 1 are contributing to the bytecount
4) plot_throughput_rema_separated_by_flows: Plots the throughput data with a scatter plot overlay, classified by the number of flows contributing(ALL flows represented)
5) plot_throughput_rema_separated_by_flows_socket_grouped: Same as #4, but Gantt chart groups streams by socket instead of showing each stream individually

6) plot_rema_per_http_stream: Plots the REMA lines for each HTTP stream, useful for visualizing spikes in the bytecount
7) plot_aggregated_bytecount: Plots only the aggregated bytecounts across all HTTP streams for a clean view of total system throughput

"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import plotting_utilities



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
        ax1.set_ylim(0, 1500) #set y-axis for consistency

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
            plotting_utilities.save_figure(fig, base_path, filename)

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

        plotting_utilities.save_figure(fig, base_path, filename)
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
        plotting_utilities.save_figure(fig, base_path, filename)
    plt.show()


"""
Plot of the throughput, but throughput points are classified by the number of flows contributing to the bytecount.
Has the option to add a scatter plot overlay. These points are also classified by the number of flows contributing to the bytecount.
"""
def plot_throughput_rema_separated_by_flows(throughput_list_dict, start_time, end_time, source_times, begin_time, title=None, scatter=False, save=False, base_path=None):

    fig, (ax1, ax2) = plt.subplots(2, 1, height_ratios=[3, 1], figsize=(10, 8))
    # Define colors for different flow counts (cool to warm: fewer to more flows)
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
    ax1.set_xlabel('Time (in seconds)')
    ax1.set_ylabel('Throughput (in Mbps)')
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
        plotting_utilities.save_figure(fig, base_path, filename)
    plt.show()


"""
Similar to plot_throughput_rema_separated_by_flows(), but the Gantt chart groups HTTP streams by socket.
Each socket gets one row, and all streams using that socket are shown on that row.
"""
def plot_throughput_rema_separated_by_flows_socket_grouped(throughput_list_dict, start_time, end_time, source_times, begin_time, title=None, scatter=False, save=False, base_path=None):

    fig, (ax1, ax2) = plt.subplots(2, 1, height_ratios=[3, 1], figsize=(10, 8))
    # Define colors for different flow counts
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
                # segment['throughput_ema'],
                segment['throughput'],
                color=flow_colors.get(flow_count_prev, 'gray'),
                linewidth=1.5,
                linestyle='--',
            )

    # Add labels, title, and legend
    ax1.set_xlabel('Time (in seconds)')
    ax1.set_ylabel('Throughput (in Mbps)')
    ax1.set_ylim(0, 3200)

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
    colors = plt.cm.rainbow(np.linspace(0, 1, len(unique_sockets)))
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

    ax2.set_xlabel('Time (in seconds)')
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
        plotting_utilities.save_figure(fig, base_path, filename)
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
        plotting_utilities.save_figure(fig, base_path, filename)
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
