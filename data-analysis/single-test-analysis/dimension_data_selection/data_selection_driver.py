def run_data_selection_driver(byte_count, aggregated_time, stats_accumulator):
    """
    Analyze data selection patterns: compute metrics for max flows vs non-max flows.
    All metrics are added to stats_accumulator as flat (non-nested) entries.
    """
    print("\n" + "=" * 60)
    print("Data selection driver")

    # Find maximum number of flows
    num_flows = stats_accumulator.get('num_sockets')

    # === Compute Total Metrics ===
    total_points = len(byte_count)
    total_bytes = sum(byte_count[ts][0] for ts in byte_count)

    if aggregated_time:
        total_duration_ms = aggregated_time[-1] - aggregated_time[0]
    else:
        total_duration_ms = 0

    # === Compute Max Flow Metrics ===
    # Count points where all flows are contributing
    num_points_all_flows_contributing = sum(1 for ts in byte_count if byte_count[ts][1] == num_flows)

    # Sum bytes where all flows are contributing
    num_bytes_all_flows_contributing = sum(byte_count[ts][0] for ts in byte_count if byte_count[ts][1] == num_flows)

    # Calculate time duration where all flows are contributing
    if aggregated_time:
        max_flow_timestamps = [ts for ts in byte_count if byte_count[ts][1] == num_flows]
        if max_flow_timestamps:
            time_all_flows_contributing = sum(
                aggregated_time[i+1] - aggregated_time[i]
                for i in range(len(aggregated_time)-1)
                if aggregated_time[i] in max_flow_timestamps
            )
        else:
            time_all_flows_contributing = 0
    else:
        time_all_flows_contributing = 0

    # === Compute Non-Max Flow Metrics ===
    num_points_not_max_flows = total_points - num_points_all_flows_contributing
    num_bytes_not_max_flows = total_bytes - num_bytes_all_flows_contributing
    time_not_max_flows = total_duration_ms - time_all_flows_contributing

    # === Compute Percentages ===
    percent_points_all_flows_contributing = (num_points_all_flows_contributing / total_points * 100) if total_points > 0 else 0
    percent_points_not_max_flows = (num_points_not_max_flows / total_points * 100) if total_points > 0 else 0

    percent_bytes_all_flows_contributing = (num_bytes_all_flows_contributing / total_bytes * 100) if total_bytes > 0 else 0
    percent_bytes_not_max_flows = (num_bytes_not_max_flows / total_bytes * 100) if total_bytes > 0 else 0

    percent_time_all_flows_contributing = (time_all_flows_contributing / total_duration_ms * 100) if total_duration_ms > 0 else 0
    percent_time_not_max_flows = (time_not_max_flows / total_duration_ms * 100) if total_duration_ms > 0 else 0

    stats_accumulator.add_bulk({
        # Total metrics
        'num_points': total_points,
        'total_bytes': total_bytes,
        'total_duration_ms': total_duration_ms,

        # Max flows metrics (absolute values)
        'num_points_all_flows_contributing': num_points_all_flows_contributing,
        'num_bytes_all_flows_contributing': num_bytes_all_flows_contributing,
        'time_all_flows_contributing': time_all_flows_contributing,

        # Non-max flows metrics (absolute values)
        'num_points_not_max_flows': num_points_not_max_flows,
        'num_bytes_not_max_flows': num_bytes_not_max_flows,
        'time_not_max_flows': time_not_max_flows,

        # Max flows percentages
        'percent_points_all_flows_contributing': percent_points_all_flows_contributing,
        'percent_bytes_all_flows_contributing': percent_bytes_all_flows_contributing,
        'percent_time_all_flows_contributing': percent_time_all_flows_contributing,

        # Non-max flows percentages
        'percent_points_not_max_flows': percent_points_not_max_flows,
        'percent_bytes_not_max_flows': percent_bytes_not_max_flows,
        'percent_time_not_max_flows': percent_time_not_max_flows
    })

    # === Filter to Selected Data (Max Flows Only) ===
    selected_byte_count = {
        ts: byte_count[ts]
        for ts in byte_count
        if byte_count[ts][1] == num_flows
    }
    selected_aggregated_time = [ts for ts in aggregated_time if ts in selected_byte_count]

    print(f"Selected {len(selected_byte_count)}/{total_points} points (max flows only)")
    print(f"Max flows contribute {percent_points_all_flows_contributing:.1f}% of points, {percent_bytes_all_flows_contributing:.1f}% of bytes, {percent_time_all_flows_contributing:.1f}% of time")

    print("=" * 60)

    return {
        'selected_byte_count': selected_byte_count,
        'selected_aggregated_time': selected_aggregated_time,
        'num_flows': num_flows
    }