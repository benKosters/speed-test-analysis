import sys
import os

# Add data-analysis/ directory to path so submodules can import utilities
# __file__ is at: data-analysis/single-test-analysis/data_normalization/__init__.py
# We need to go up 2 levels to reach data-analysis/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from .throughput_data_processing import (
    normalize_test_data,
    aggregate_timestamps_and_find_stream_durations,
    sum_all_bytecounts_across_http_streams
)

from .latency_data_processing import (
    extract_latencies
)

from .validate_data_normalization import (
    byte_count_validation,
    normalize_byte_count,
    print_aggregated_time_entries,
    analyze_missing_timestamps,
    sum_bytecounts_and_find_time_proportions,
    print_throughput_entries,
    analyze_throughput_intervals,
    throughput_mean_median_range
)

from .validate_upload_processing import (
    normalize_current_position_list
)

from .data_norm_driver import (
    run_normalization_driver
)

# Define what gets imported with "from data_normalization import *"
__all__ = [
    # Core processing functions
    'normalize_test_data',
    'aggregate_timestamps_and_find_stream_durations',
    'sum_all_bytecounts_across_http_streams',
    'extract_latencies',

    # Validation functions
    'byte_count_validation',
    'normalize_byte_count',
    'print_aggregated_time_entries',
    'analyze_missing_timestamps',
    'sum_bytecounts_and_find_time_proportions',
    'print_throughput_entries',
    'analyze_throughput_intervals',
    'throughput_mean_median_range',
    'normalize_current_position_list',
    'run_normalization_driver'
]

# Module metadata
__version__ = '1.0.0'
__author__ = 'Ben Kosters'
