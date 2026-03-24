import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


"""
Plots only the aggregated bytecounts across all HTTP streams. This gives a clean view of total system throughput.
"""
def plot_aggregated_bytecount(plot_data, test_type=None, title=None, log_scale=False):
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
    data = plot_data["byte_list"]
    save = plot_data["save"]
    base_path = plot_data["base_path"]
    begin_time = plot_data["begin_time"]
    source_times = plot_data["source_times"]
    if test_type is None:
        test_type = plot_data.get("test_type")

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
"""
def plot_rema_per_http_stream(plot_data, test_type=None, title=None, log_scale=False):
    # Extract parameters from plot_data
    data = plot_data["byte_list"]
    save = plot_data["save"]
    base_path = plot_data["base_path"]
    begin_time = plot_data["begin_time"]
    source_times = plot_data["source_times"]
    if test_type is None:
        test_type = plot_data.get("test_type")
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
