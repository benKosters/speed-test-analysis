def run_data_selection_driver(byte_count, aggregated_time, stats_accumulator):
    """
    """
    print("\n" + "=" * 60)
    print("PHASE: DATA SELECTION")
    print("=" * 60)

    # === Analyze Flow Contribution Patterns ===
    print("  [1/2] Analyzing flow contribution patterns")

    # Find maximum number of flows
    num_flows = max(byte_count[timestamp][1] for timestamp in byte_count)

    # Calculate percentage of time each flow count contributes
    flow_distribution = {}
    for i in range(1, num_flows + 1):
        count = sum(1 for ts in byte_count if byte_count[ts][1] == i)
        flow_distribution[i] = count

    total_points = len(byte_count)
    formatted_flows = {
        f"{i}_flows": {
            "count": flow_distribution[i],
            "percentage": (flow_distribution[i] / total_points * 100) if total_points > 0 else 0
        }
        for i in range(1, num_flows + 1)
    }

    max_flow_percentage = formatted_flows.get(f"{num_flows}_flows", {}).get("percentage", 0)

    # Add flow contribution statistics
    stats_accumulator.add('data_selection.flow_contribution', {
        'max_flows': num_flows,
        'max_flow_percentage': max_flow_percentage,
        'distribution': formatted_flows
    })

    # === Compute Selection Impact Metrics ===
    print("  [2/2] Computing selection impact metrics...")

    # Metrics for max_flows_only selection
    max_flow_points = flow_distribution[num_flows]
    max_flow_bytes = sum(byte_count[ts][0] for ts in byte_count if byte_count[ts][1] == num_flows)
    total_bytes = sum(byte_count[ts][0] for ts in byte_count)

    # Calculate time duration (first to last timestamp)
    if aggregated_time:
        total_duration_ms = aggregated_time[-1] - aggregated_time[0]
        max_flow_timestamps = [ts for ts in byte_count if byte_count[ts][1] == num_flows]
        if max_flow_timestamps:
            max_flow_duration_ms = sum(
                aggregated_time[i+1] - aggregated_time[i]
                for i in range(len(aggregated_time)-1)
                if aggregated_time[i] in max_flow_timestamps
            )
        else:
            max_flow_duration_ms = 0
    else:
        total_duration_ms = 0
        max_flow_duration_ms = 0

    # Calculate exclusion percentages
    percent_bytes_excluded = ((total_bytes - max_flow_bytes) / total_bytes * 100) if total_bytes > 0 else 0
    percent_time_excluded = ((total_duration_ms - max_flow_duration_ms) / total_duration_ms * 100) if total_duration_ms > 0 else 0
    percent_points_excluded = ((total_points - max_flow_points) / total_points * 100) if total_points > 0 else 0

    stats_accumulator.add('data_selection.impact_metrics', {
        'total_points': total_points,
        'total_bytes': total_bytes,
        'total_duration_ms': total_duration_ms,
        'max_flow_points': max_flow_points,
        'max_flow_bytes': max_flow_bytes,
        'max_flow_duration_ms': max_flow_duration_ms,
        'percent_points_excluded_if_max_flows_only': percent_points_excluded,
        'percent_bytes_excluded_if_max_flows_only': percent_bytes_excluded,
        'percent_time_excluded_if_max_flows_only': percent_time_excluded
    })

    # Filter to only include points where all flows contribute
    selected_byte_count = {
        ts: byte_count[ts]
        for ts in byte_count
        if byte_count[ts][1] == num_flows
    }
    selected_aggregated_time = [ts for ts in aggregated_time if ts in selected_byte_count]

    print(f"  ✓ Selected {len(selected_byte_count)}/{total_points} points (max flows only)")
    stats_accumulator.add('data_selection.points_selected', len(selected_byte_count))
    stats_accumulator.add('data_selection.points_excluded', total_points - len(selected_byte_count))

    print("=" * 60)

    return {
        'selected_byte_count': selected_byte_count,
        'selected_aggregated_time': selected_aggregated_time,
        'num_flows': num_flows
    }