import dimension_throughput_calc as tp_calc
import numpy as np

def run_throughput_calculation_driver(byte_count, aggregated_time, source_times, begin_time, bin_size, stats_accumulator, config_accumulator):
    """
    Calculate throughput metrics and add them to the config accumulator.

    Metrics collected:
    - Mean, median, std, min, max throughput
    - Bulk throughput (total bytes / total time for max flow points)
    - Number of data points and bins
    - Discarded data statistics (bytes, points, time)
    """
    num_flows = stats_accumulator.get("num_sockets")

    # Calculate throughput with the specified bin size, tracking discarded data
    throughput_results, discarded_stats = tp_calc.calculate_interval_throughput_tracking_discarded_data(
        aggregated_time, byte_count, num_flows, bin_size, begin_time
    )

    # Calculate throughput statistics
    if throughput_results:
        throughputs = [point['throughput'] for point in throughput_results]

        config_accumulator.add('mean_throughput_mbps', float(np.mean(throughputs)))
        config_accumulator.add('median_throughput_mbps', float(np.median(throughputs)))
        config_accumulator.add('std_throughput_mbps', float(np.std(throughputs)))
        config_accumulator.add('min_throughput_mbps', float(np.min(throughputs)))
        config_accumulator.add('max_throughput_mbps', float(np.max(throughputs)))
        config_accumulator.add('num_throughput_bins', len(throughput_results))
    else:
        config_accumulator.add('mean_throughput_mbps', 0.0)
        config_accumulator.add('median_throughput_mbps', 0.0)
        config_accumulator.add('std_throughput_mbps', 0.0)
        config_accumulator.add('min_throughput_mbps', 0.0)
        config_accumulator.add('max_throughput_mbps', 0.0)
        config_accumulator.add('num_throughput_bins', 0)

    # Calculate bulk throughput (total bytes / total time for max flow points only)
    total_bytes_max_flows = sum(byte_count[ts][0] for ts in byte_count if byte_count[ts][1] == num_flows)
    max_flow_timestamps = [ts for ts in byte_count if byte_count[ts][1] == num_flows]
    if max_flow_timestamps:
        time_span_ms = max(max_flow_timestamps) - min(max_flow_timestamps)
        time_span_sec = time_span_ms / 1000
        bulk_throughput_mbps = (total_bytes_max_flows * 8 / 1_000_000) / time_span_sec if time_span_sec > 0 else 0
    else:
        bulk_throughput_mbps = 0.0

    config_accumulator.add('bulk_throughput_mbps', float(bulk_throughput_mbps))

    # Add aggregated data point count (before binning)
    num_max_flow_points = len([ts for ts in byte_count if byte_count[ts][1] == num_flows])
    config_accumulator.add('num_aggregated_points', num_max_flow_points)

    # Add discarded data statistics
    config_accumulator.add('discarded_bytes', discarded_stats['discarded_bytes'])
    config_accumulator.add('discarded_data_points', discarded_stats['discarded_objects'])
    config_accumulator.add('discarded_time_ms', discarded_stats['discarded_time'])

    # Calculate percentages for discarded data
    total_bytes = sum(byte_count[ts][0] for ts in byte_count)
    total_points = len(byte_count)
    all_timestamps = list(byte_count.keys())
    total_time_ms = max(all_timestamps) - min(all_timestamps) if all_timestamps else 0

    percent_discarded_bytes = (discarded_stats['discarded_bytes'] / total_bytes * 100) if total_bytes > 0 else 0
    percent_discarded_points = (discarded_stats['discarded_objects'] / total_points * 100) if total_points > 0 else 0
    percent_discarded_time = (discarded_stats['discarded_time'] / total_time_ms * 100) if total_time_ms > 0 else 0

    config_accumulator.add('percent_discarded_bytes', float(percent_discarded_bytes))
    config_accumulator.add('percent_discarded_data_points', float(percent_discarded_points))
    config_accumulator.add('percent_discarded_time', float(percent_discarded_time))

    print(f"Throughput Stats: Mean={float(np.mean(throughputs)) if throughput_results else 0:.2f} Mbps, "
          f"Bins={len(throughput_results)}, Discarded={discarded_stats['discarded_objects']} points")

    # Calculate throughput grouped by number of flows (for plotting)
    # These are NOT added to config_accumulator since they're just for visualization
    throughput_by_flows = {}
    for flow_count in range(1, num_flows + 1):
        throughput_by_flows[flow_count], _ = tp_calc.calculate_interval_throughput_tracking_discarded_data(
            aggregated_time, byte_count, flow_count, bin_size, begin_time
        )

    return {
        "throughput_results": throughput_results,
        "throughput_by_flows": throughput_by_flows,
        "discarded_stats": discarded_stats
    }


