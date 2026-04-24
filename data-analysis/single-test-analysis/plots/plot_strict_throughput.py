import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from dimension_throughput_calc import throughput_driver as tp_calc
import plots.plotting_utilities as plotting_utilities

def plot_strict_throughput_scatter(plot_data, start_time=0, end_time=None, title=None, line=False):
    # Extract parameters from plot_data
    df = pd.DataFrame(plot_data["filtered_throughput_data"]['strict_interval_throughput_results'])
    # df = pd.DataFrame(plot_data["all_throughput_data"]["strict_interval_throughput_results"])
    source_times = plot_data["source_times"]
    begin_time = plot_data["begin_time"]
    if end_time is None:
        end_time = plot_data["end_time"]
    # Filter the DataFrame for the specified time range
    filtered_df = df[(df['time'] >= start_time) & (df['time'] <= end_time)].copy()

    fig, (ax1, ax2) = plt.subplots(2, 1, height_ratios=[3, 1], figsize=(12, 8))

    # ------------------- Throughput Scatter Plot (Top Subplot) -------------------
    # Scatter plot for full num_flows

    # REMA line for the filtered data
    if line:
        ax1.plot(
            filtered_df['time'],
            filtered_df['throughput'],
            color='red',
            linestyle='--',
            linewidth=1,
    )
    else:
        ax1.scatter(
        filtered_df['time'],
        filtered_df['throughput'],
        color='blue',
        s=10,
        alpha=0.7,
    )

    # Add labels, title, and legend for the throughput plot
    if plot_data["configs"]["all_data"] == True:
        data_label = "All Data"
    else:
        data_label = "Max Flow Only"

    ax1.set_xlabel('Time (seconds)')
    ax1.set_ylabel('Throughput (Mbps)')
    plot_title = f"{plot_data['server']}, {plot_data['test_type']}, {data_label}, With {plot_data['bin_size_ms']}ms Bin Size"
    ax1.set_title(plot_title)
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

    ax1.set_xlim(start_time, end_time)
    ax2.set_xlim(start_time, end_time)

    plt.tight_layout()
    if plot_data['save'] and plot_data['base_path']:
        filename = f"strict_throughput_scatter_{plot_data['bin_size_ms']}ms_bin_{line}"
        plotting_utilities.save_figure(fig, plot_data['base_path'], filename)
    plt.show()