"""
Data Loader for the Speed Test Visualization GUI

This module handles loading and processing of test data.
"""

import os
import json
import sys

# Add the parent directory to the path so we can import the processing modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import helper_functions as hf
import throughput_calculation_functions as tp

class DataLoader:
    """Handles loading and processing of test data"""

    def __init__(self):
        """Initialize the data loader"""
        pass

    def is_valid_test_directory(self, directory):
        """Check if a directory contains the necessary files to be a valid test directory"""
        required_files = ["byte_time_list.json", "current_position_list.json"]
        return any(os.path.exists(os.path.join(directory, f)) for f in required_files)

    def load_test_data(self, test_path):
        """Load and process test data from the specified directory"""
        # No longer checking for cached data as the caching feature is being removed

        # Construct file paths
        byte_file = os.path.join(test_path, "byte_time_list.json")
        current_file = os.path.join(test_path, "current_position_list.json")
        latency_file = os.path.join(test_path, "latency.json")
        loaded_latency_file = os.path.join(test_path, "loaded_latency.json")
        socket_file = os.path.join(test_path, "socketIds.json")
        byte_count_file = os.path.join(test_path, "byte_count.json")

        # Check if byte_count.json exists in the test directory
        if os.path.exists(byte_count_file):
            # Load pre-processed byte_count data
            with open(byte_count_file, 'r') as f:
                byte_count = json.load(f)

            # Load basic test data for type determination
            with open(byte_file, 'r') as f:
                byte_list_data = json.load(f)
                test_type = byte_list_data.get("test_type", "unknown")

            # Set placeholder values for consistency
            byte_list = []
            aggregated_time = []
            source_times = {}
            begin_time = 0
        else:
            # Step 1: Normalize bytecount data
            byte_list, test_type = tp.normalize_test_data(byte_file, current_file, latency_file)

            # Step 2: Aggregate timestamps
            aggregated_time, source_times, begin_time = tp.aggregate_timestamps_and_find_stream_durations(byte_list, socket_file)

            # Step 3: Sum bytecounts
            byte_count = tp.sum_bytecounts_for_timestamps(byte_list, aggregated_time)

        # Step 4: Calculate throughput for different intervals
        num_flows = max(byte_count[timestamp][1] for timestamp in byte_count)

        throughput_results = {}
        for interval in [2, 10]:
            throughput_results[interval] = tp.calculate_interval_throughput(
                aggregated_time, byte_count, num_flows, interval, begin_time)

        # Step 5: Create throughput by flows
        throughput_by_flows = {}
        for interval in [2, 10]:
            throughput_by_flows[interval] = {}
            for flow_count in range(1, num_flows + 1):
                throughput_by_flows[interval][flow_count] = tp.calculate_interval_throughput(
                    aggregated_time, byte_count, flow_count, interval, begin_time)

        # Step 6: Process latency data
        idle_latencies = []
        loaded_latencies = []

        if os.path.exists(latency_file):
            with open(latency_file, 'r') as f:
                idle_latency = json.load(f)
            idle_latencies = tp.extract_latencies(idle_latency)

        if os.path.exists(loaded_latency_file):
            with open(loaded_latency_file, 'r') as f:
                loaded_latency = json.load(f)
            loaded_latencies = tp.extract_latencies(loaded_latency)

        # Combine all data
        test_data = {
            "test_type": test_type,
            "byte_list": byte_list,
            "aggregated_time": aggregated_time,
            "source_times": source_times,
            "begin_time": begin_time,
            "byte_count": byte_count,
            "num_flows": num_flows,
            "throughput_results": throughput_results,
            "throughput_by_flows": throughput_by_flows,
            "idle_latencies": idle_latencies,
            "loaded_latencies": loaded_latencies
        }

        # No longer caching the results

        return test_data

    def scan_for_tests(self, parent_dir):
        """Scan a directory for valid test directories"""
        test_dirs = {}

        for item in os.listdir(parent_dir):
            test_dir = os.path.join(parent_dir, item)
            if os.path.isdir(test_dir) and self.is_valid_test_directory(test_dir):
                test_dirs[os.path.basename(test_dir)] = test_dir

        return test_dirs
