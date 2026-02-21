"""
High-level orchestration for data normalization phase.
This consolidates steps 1-3 of the pipeline.
"""
import os
import json
from . import (
    normalize_test_data,
    aggregate_timestamps_and_find_stream_durations,
    sum_all_bytecounts_across_http_streams,
    byte_count_validation
)
import utilities
from statistics import StatisticsAccumulator


def run_normalization_driver(base_path, stats_accumulator, socket_file=None):
    print("Normalizing Data", "=" * 60)

    # Step 1: Normalize data
    byte_file = os.path.join(base_path, "byte_time_list.json")
    current_file = os.path.join(base_path, "current_position_list.json")
    latency_file = os.path.join(base_path, "latency_data.json")

    byte_list, test_type = normalize_test_data(byte_file, current_file, latency_file)
    print(f"Normalized {len(byte_list)} streams ({test_type})")
    stats_accumulator.add('test_type', test_type)
    stats_accumulator.add('total_http_streams', len(byte_list))

    # Step 2: Aggregate timestamps
    print("\nAggregating timestamps")
    socket_path = socket_file or os.path.join(base_path, "socketIds.json")
    aggregated_time, source_times, begin_time = aggregate_timestamps_and_find_stream_durations(byte_list, socket_path)
    print(f"Aggregated {len(aggregated_time)} unique timestamps")
    stats_accumulator.add('num_timestamps', len(aggregated_time))

    # Step 3: Sum bytecounts across HTTP streams
    print("\nSumming bytecounts across HTTP streams")
    byte_count_file = os.path.join(base_path, "byte_count.json")

    if os.path.exists(byte_count_file):
        print(f"Loading cached byte_count file")
        byte_count_raw = utilities.load_json(byte_count_file)
        byte_count = {int(ts): val for ts, val in byte_count_raw.items()}
    else:
        print(f"No cached byte_count file found, calculating from byte_list")
        byte_count = sum_all_bytecounts_across_http_streams(byte_list, aggregated_time)
        with open(byte_count_file, 'w') as f:
            json.dump(byte_count, f, indent=4)
        print(f"Calculated and saved byte_count")

    # Validation statistics
    total_raw, total_proc, list_dur, count_dur, percent_loss = byte_count_validation(byte_list, byte_count)
    num_flows = max(byte_count[timestamp][1] for timestamp in byte_count)
    stats_accumulator.add('total_raw_bytes', total_raw)
    stats_accumulator.add('total_processed_bytes', total_proc)
    stats_accumulator.add('list_duration_sec', list_dur)
    stats_accumulator.add('count_duration_sec', count_dur)
    stats_accumulator.add('percent_byte_loss', percent_loss)
    stats_accumulator.add('num_sockets', num_flows)

    print(f"\n{percent_loss:.2f}% byte loss after processing")
    print("=" * 60)

    return {
        'byte_list': byte_list,
        'aggregated_time': aggregated_time,
        'source_times': source_times,
        'begin_time': begin_time,
        'byte_count': byte_count,
        'stats_accumulator': stats_accumulator
    }