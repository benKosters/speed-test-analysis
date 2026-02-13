"""
Function for plotting throughput at the socket level
"""


import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import plots as plotting_utilities


def plot_throughput_separated_by_sockets(throughput_list_dict, start_time, end_time, source_times, begin_time, title=None, scatter=False, save=False, base_path=None):

    fig, (ax1, ax2) = plt.subplots(2, 1, height_ratios=[3, 1], figsize=(10, 8))
    # Define colors for different socket counts
    socket_colors = {
        1: 'purple',
        2: 'blue',
        3: 'green',
        4: 'orange',
        5: 'red',
        6: 'brown'
    }

    # Create a combined DataFrame with a 'socket_count' column
    combined_data = []
    for socket_count, throughput_list in throughput_list_dict.items():
        for entry in throughput_list:
            if start_time <= entry['time'] <= end_time:
                combined_data.append({
                    'time': entry['time'],
                    'throughput': entry['throughput'],
                    'socket_count': socket_count
                })

    combined_df = pd.DataFrame(combined_data).sort_values(by='time').reset_index(drop=True)

    combined_df['throughput_ema'] = combined_df['throughput'].ewm(alpha=0.1, adjust=False).mean()

    # -------------------  Throughput Plot with color-coded segments (Top Subplot) -------------------
    if scatter:
        for socket_count in sorted(throughput_list_dict.keys()):
            mask = combined_df['socket_count'] == socket_count
            if mask.any():  # Only plot if there are points with this flow count
                ax1.scatter(
                    combined_df.loc[mask, 'time'],
                    combined_df.loc[mask, 'throughput'],
                    color=socket_colors.get(socket_count, 'gray'),
                    s=5,  # Slightly smaller points to avoid overwhelming the plot
                    alpha=0.8,  # Slightly transparent
                    label=f'{socket_count} Flows (data points)'
                )

    # Plot the REMA line as line segments with different colors
    for i in range(1, len(combined_df)):
        socket_count_prev = combined_df.iloc[i-1]['socket_count']
        socket_count_current = combined_df.iloc[i]['socket_count']

        if socket_count_prev != socket_count_current or i == len(combined_df) - 1:
            # Find all consecutive points with the same flow count
            segment_start = i-1
            while segment_start > 0 and combined_df.iloc[segment_start-1]['socket_count'] == socket_count_prev:
                segment_start -= 1

            segment = combined_df.iloc[segment_start:i]

            ax1.plot(
                segment['time'],
                segment['throughput_ema'],
                color=socket_colors.get(socket_count_prev, 'gray'),
                linewidth=1.5,
                linestyle='--',
            )

    # Add labels, title, and legend
    ax1.set_xlabel('Time (in seconds)')
    ax1.set_ylabel('Throughput (in Mbps)')
    ax1.set_ylim(0, 2000)

    if title:
        ax1.set_title(title)
    else:
        ax1.set_title(f"Throughput REMA with Socket Count Coloring ({start_time}s to {end_time}s)")

    # Create a custom legend for flow counts
    handles = []
    labels = []
    for socket_count in sorted(set(combined_df['socket_count'])):
        color = socket_colors.get(socket_count, 'gray')
        handles.append(plt.Line2D([0], [0], color=color, lw=3))
        labels.append(f'{socket_count} Sockets')

    # Place the flow count legend in the upper right
    ax1.legend(handles=handles, labels=labels, bbox_to_anchor=(1.05, 1), loc='upper left')

    # -------------------  Sockets Gantt Chart (Bottom Subplot) -------------------
    # Create color map for unique socket IDs
    unique_sockets = set(info['socket'] for info in source_times.values() if info['socket'] is not None)
    colors = plt.cm.rainbow(np.linspace(0, 1, len(unique_sockets)))
    socket_colors = dict(zip(unique_sockets, colors))

    y_offset = 0
    for stream_id, info in source_times.items():
        start_sec = (info['times'][0] - begin_time) / 1000
        end_sec = (info['times'][1] - begin_time) / 1000

        if info['socket'] is not None:
            color = socket_colors[info['socket']]
            ax2.hlines(y=y_offset, xmin=start_sec, xmax=end_sec,
                      color=color, linewidth=2)
        else:
            color = 'gray'
            ax2.hlines(y=y_offset, xmin=start_sec, xmax=end_sec,
                      color=color, linewidth=2)

        y_offset += 1

    ax2.set_xlabel('Time (in seconds)')
    ax2.set_ylabel('Socket ID')
    ax2.set_yticks(range(len(source_times)))
    ax2.set_yticklabels([f'Socket {id}' for id in source_times.keys()], fontsize=8)
    ax2.grid(True, axis='y', linestyle='--', alpha=0.3)

    ax1.set_xlim(start_time, end_time)
    ax2.set_xlim(start_time, end_time)

    plt.tight_layout()
    if save and base_path:
        filename = "throughput_rema_separated_by_flows.png"
        plotting_utilities.save_figure(fig, base_path, filename)
    plt.show()
