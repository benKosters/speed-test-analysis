"""
Statistics Driver - used for computing a number of statistics from a single upload or download ookla test.

This driver runs a number of stats computations on data from the ookla test, then returns a StatisticsAccumulator object.

This driver coordinates:
1. Computing derived statistics from pipeline outputs
2. Extracting statistics from various data structures
3. Consolidating all statistics for output
"""
import os
from .statistics_accumulator import StatisticsAccumulator
from . import statistics_functions as stats_funcs


def compute_all_statistics(byte_list,byte_count,aggregated_time,source_times,throughput_results,begin_time,base_path,test_type=None):
    """
    Main function to compute statistics. It is called after all phases in the pipeline have completed.

    Arguments:
        byte_list: Normalized byte list from data normalization
        byte_count: Aggregated byte counts with flow information
        aggregated_time: List of unique timestamps
        source_times: Start/end times for each HTTP stream
        throughput_results: Dict of throughput calculations (by bin size)
        begin_time: Test start time
        base_path: Directory for saving outputs
        test_type: 'upload' or 'download'

    Returns:
        StatisticsAccumulator with all computed statistics
    """
    #for debugging/seeing progress in terminal
    print("\n" + "=" * 60)
    print("Running statistics driver")
    print("=" * 60)

    stats = StatisticsAccumulator(base_path)

    # save test type and the directory (the test's unique identifier)
    if test_type:
        stats.add('test_type', test_type)
    stats.add('test_directory', os.path.basename(base_path))

    #find the number of maximum flows and the number of total HTTP streams
    num_flows = max(byte_count[timestamp][1] for timestamp in byte_count)
    stats.add('num_flows', num_flows)
    stats.add('num_streams', len(byte_list))

    # HTTP Stream statistics
    stream_stats = stats_funcs.capture_http_stream_statistics(source_times, begin_time)
    stats.add_phase('http_streams', stream_stats)

    # Save detailed HTTP stream data to separate file
    http_stream_data = {
        'source_times': source_times,
        'num_streams': len(byte_list),
        'statistics': stream_stats
    }
    stats.add('http_stream_data', http_stream_data, detailed=True) # detailer = True will save as a separate file

    # save byte count information
    total_bytes = stats_funcs.sum_byte_counts(byte_list)
    stats.add('bytes', {
        'total_bytes': total_bytes,
        'num_unique_timestamps': len(aggregated_time)
    })

    # Test duration
    duration_ms = stats_funcs.find_test_duration(byte_list)
    stats.add('duration_ms', duration_ms)
    stats.add('duration_sec', duration_ms / 1000.0)

    # compute stats for throughput. These statistics all depend on the bin size and the method used for generating throughput points
    throughput_stats = {}

    for bin_size, results in throughput_results.items():
        if not results:
            continue

        throughputs = [r['throughput'] for r in results]
        throughput_stats[f'bin_{bin_size}ms'] = {
            'num_points': len(throughputs),
            'mean_mbps': sum(throughputs) / len(throughputs) if throughputs else 0,
            'median_mbps': sorted(throughputs)[len(throughputs)//2] if throughputs else 0,
            'min_mbps': min(throughputs) if throughputs else 0,
            'max_mbps': max(throughputs) if throughputs else 0,
            'range_mbps': max(throughputs) - min(throughputs) if throughputs else 0
        }

    stats.add_phase('throughput', throughput_stats)

    # generate socket statistics
    socket_stats = stats_funcs.capture_socket_statistics(source_times)
    if socket_stats:
        stats.add_phase('sockets', socket_stats)

    # comput the amount of time during the test that 'x' flows are contributing (ex: all 6 flows are contrubuting 85% of the test)
    occurrence_stats = stats_funcs.calculate_occurrence_sums(byte_count)
    stats.add('data_quality', {
        'flow_occurrences': occurrence_stats
    })

    print("=" * 60)
    print("Computing statistics completed")
    return stats


def save_legacy_stream_data(byte_list, source_times, base_path, print_output=False):
    # FIXME - wrapper for old function. Clean this up later
    stats_funcs.save_socket_stream_data(byte_list, source_times, base_path, print_output)
