# Import individual statistic functions
from .summary_statistics import (
    sum_byte_counts,
    find_test_duration,
    calculate_occurrence_sums,
    capture_http_stream_statistics,
    capture_socket_statistics,
    save_socket_stream_data,
    calculate_percent_of_all_flows_contributing,
)

# Import high-level components
from .statistics_accumulator import StatisticsAccumulator
from .statistics_driver import compute_all_statistics, save_legacy_stream_data

__version__ = "1.0.0"
__author__ = "Ben Kosters"

__all__ = [
    # Core components
    'StatisticsAccumulator',
    'compute_all_statistics',

    # Individual functions
    'sum_byte_counts',
    'find_test_duration',
    'calculate_occurrence_sums',
    'capture_http_stream_statistics',
    'capture_socket_statistics',
    'save_socket_stream_data',
    'calculate_percent_of_all_flows_contributing',
    'save_legacy_stream_data',
]