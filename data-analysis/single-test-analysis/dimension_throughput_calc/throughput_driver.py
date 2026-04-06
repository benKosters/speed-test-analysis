import dimension_throughput_calc as tp_calc
import numpy as np

def run_throughput_calculation_driver(byte_count, aggregated_time, begin_time, bin_size, data_selection, stats_accumulator, config_accumulator):
    """
        Main driver to compute the throughput
    """
    num_flows = stats_accumulator.get("num_sockets")

    # Calculate throughput with the specified bin size, tracking discarded data
    # throughput_results, discarded_stats = tp_calc.calculate_interval_threshold_throughput_tracking_discarded_data(
    #     aggregated_time, byte_count, num_flows, bin_size, begin_time, all_data=data_selection)

    strict_interval_throughput_results, strict_interval_discarded_stats = tp_calc.calculate_throughput_strict_intervals(
        aggregated_time, byte_count, num_flows, bin_size, begin_time, data_selection)

    threshold_interval_throughput_results, threshold_interval_discarded_stats = tp_calc.calculate_interval_threshold_throughput_tracking_discarded_data(
        aggregated_time, byte_count, num_flows, bin_size, begin_time, data_selection)


    ## 3-24-2026 TODO: Since artifact filtering is now AFTER throughput computation, this needs to be moved
    # -----------------------[section 1/2] Moved to main.py ----------------------------------------
    # # Compute throughput metrics and save them
    # throughput_metrics = tp_calc.compute_throughput_metrics(throughput_results)
    # for metric_name, metric_value in throughput_metrics.items():
    #     config_accumulator.add(metric_name, metric_value)

    # --------------------------------------------------------------------------------

    bytes = stats_accumulator.get("total_raw_bytes")
    timespan = stats_accumulator.get("list_duration_sec")
    bulk_throughput_mbps = (bytes * 8 / 1_000_000) / (timespan)

    config_accumulator.add('bulk_throughput_mbps', float(bulk_throughput_mbps))

    # Add aggregated data point count (before binning)
    num_max_flow_points = len([ts for ts in byte_count if byte_count[ts][1] == num_flows])
    # config_accumulator.add('num_max_flow_points', num_max_flow_points)

    # Add discarded data statistics (bytes only discarded by binning with max flows)
    config_accumulator.add('strict_interval_discarded_bytes', strict_interval_discarded_stats['discarded_bytes'])
    #config_accumulator.add('strict_interval_discarded_original_data_points', strict_interval_discarded_stats['discarded_objects'])
    config_accumulator.add('strict_interval_discarded_time_ms', strict_interval_discarded_stats['discarded_time'])

    config_accumulator.add('threshold_interval_discarded_bytes', threshold_interval_discarded_stats['discarded_bytes'])
    #config_accumulator.add('threshold_interval_discarded_original_data_points', threshold_interval_discarded_stats['discarded_objects'])
    config_accumulator.add('threshold_interval_discarded_time_ms', threshold_interval_discarded_stats['discarded_time'])

    # Calculate percentages for discarded data
    total_bytes = stats_accumulator.get("total_processed_bytes")
    total_points = len(byte_count)
    all_timestamps = list(byte_count.keys())
    total_time_ms = max(all_timestamps) - min(all_timestamps) if all_timestamps else 0

    print("total discarded byte:", strict_interval_discarded_stats['discarded_bytes'], "and total bytes:", total_bytes)

    percent_discarded_bytes = (strict_interval_discarded_stats['discarded_bytes'] / total_bytes * 100) if total_bytes > 0 else 0
    # percent_discarded_points = (strict_interval_discarded_stats['discarded_objects'] / total_points * 100) if total_points > 0 else 0
    percent_discarded_time = (strict_interval_discarded_stats['discarded_time'] / total_time_ms * 100) if total_time_ms > 0 else 0

    config_accumulator.add('strict_interval_percent_discarded_bytes', float(percent_discarded_bytes))
    # config_accumulator.add('strict_interval_percent_discarded_original_data_points', float(percent_discarded_points))
    config_accumulator.add('strict_interval_percent_discarded_time', float(percent_discarded_time))

    percent_threshold_discarded_bytes = (threshold_interval_discarded_stats['discarded_bytes'] / total_bytes * 100) if total_bytes > 0 else 0
    # percent_threshold_discarded_points = (threshold_interval_discarded_stats['discarded_objects'] / total_points * 100) if total_points > 0 else 0
    percent_threshold_discarded_time = (threshold_interval_discarded_stats['discarded_time'] / total_time_ms * 100) if total_time_ms > 0 else 0
    config_accumulator.add('threshold_interval_percent_discarded_bytes', float(percent_threshold_discarded_bytes))
    # config_accumulator.add('threshold_interval_percent_discarded_original_data_points', float(percent_threshold_discarded_points))
    config_accumulator.add('threshold_interval_percent_discarded_time', float(percent_threshold_discarded_time))

    # ---------------------------------------[Sectioon 2/2] moved to main.py --------------------------------------------
    # print(f"Throughput Stats: Mean={throughput_metrics['mean_throughput_mbps']:.2f} Mbps, "
    #       f"Bins={throughput_metrics['num_throughput_bins']}, Discarded={discarded_stats['discarded_objects']} points")
    # -----------------------------------------------------------------------------------------------------------------

    # Calculate throughput grouped by number of flows (for plotting)
    # These are NOT added to config_accumulator since they're just for visualization
    throughput_by_flows = {}
    for flow_count in range(1, num_flows + 1):
        throughput_by_flows[flow_count], _ = tp_calc.calculate_interval_threshold_throughput_tracking_discarded_data(
            aggregated_time, byte_count, flow_count, bin_size, begin_time)

        throughput_by_flows[flow_count], _ = tp_calc.calculate_throughput_strict_intervals(
            aggregated_time, byte_count, flow_count, bin_size, begin_time)

    return {
        "strict_interval_throughput_results": strict_interval_throughput_results,
        "throughput_by_flows": throughput_by_flows,
        "strict_interval_discarded_stats": strict_interval_discarded_stats,
        "threshold_interval_throughput": threshold_interval_throughput_results,
        "threshold_interval_discarded_stats": threshold_interval_discarded_stats
    }


