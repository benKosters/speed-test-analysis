#!/usr/bin/env python3
"""
Generate throughput statistics at multiple interval thresholds for comparative analysis.

For each test directory (download and upload), this script:
1. Loads the byte_count.json if it exists
2. Calculates throughput at intervals: 1, 2, 5, 10, 50, and 100 ms
3. Tracks discarded data (events dropped, bytes lost)
4. Computes statistics (mean, median, min, max, range)
5. Outputs one row per interval per test direction to CSV

Usage: python3 generate_interval_throughput_csv.py <test_directory> <output_csv_file>
"""

import json
import csv
import sys
import os
import numpy as np

# Add the exploratory directory to path for imports
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'exploratory'))

import throughput_calculation as tp_calc
import throughput_data_processing as tp_proc
import data_processing_validation as validate
import utilities

def calculate_throughput_statistics(throughput_results):
    """Calculate statistics from throughput results."""
    if not throughput_results:
        return {
            'num_points': 0,
            'mean_throughput': 0,
            'median_throughput': 0,
            'min_throughput': 0,
            'max_throughput': 0,
            'throughput_range': 0
        }

    throughput_values = [result['throughput'] for result in throughput_results]

    return {
        'num_points': len(throughput_values),
        'mean_throughput': sum(throughput_values) / len(throughput_values),
        'median_throughput': np.median(throughput_values),
        'min_throughput': min(throughput_values),
        'max_throughput': max(throughput_values),
        'throughput_range': max(throughput_values) - min(throughput_values)
    }

def process_test_direction(test_dir, direction):
    """
    Process a single test direction (download or upload).

    Returns a tuple: (results_list, total_processed_bytes) where results_list contains
    one dictionary for each interval threshold.
    Returns (None, 0) if byte_count.json doesn't exist.
    """
    direction_path = os.path.join(test_dir, direction)
    byte_count_path = os.path.join(direction_path, "byte_count.json")

    # Skip if byte_count doesn't exist
    if not os.path.exists(byte_count_path):
        print(f"  Skipping {direction}: byte_count.json not found")
        return None, 0

    # Load required data
    try:
        byte_count_raw = utilities.load_json(byte_count_path)
        byte_count = {int(timestamp): value for timestamp, value in byte_count_raw.items()}

        # Get aggregated_time from byte_count keys (sorted timestamps)
        aggregated_time = sorted(byte_count.keys())

        # Get begin_time (first timestamp)
        begin_time = aggregated_time[0] if aggregated_time else 0

        # Get num_flows (max flow count in byte_count)
        num_flows = max(byte_count[timestamp][1] for timestamp in byte_count)

        # Load byte_list for validation
        byte_list_path = os.path.join(direction_path, "byte_time_list.json")
        if not os.path.exists(byte_list_path):
            byte_list_path = os.path.join(direction_path, "current_position_list.json")

        if os.path.exists(byte_list_path):
            byte_list = utilities.load_json(byte_list_path)
            # Normalize byte_list if it's an upload test (current_position_list)
            if "current_position_list.json" in byte_list_path:
                byte_list_normalized = []
                for item in byte_list:
                    new_progress = []
                    prev_position = 0
                    for progress in item["progress"]:
                        current_position = progress["current_position"]
                        time = progress["time"]
                        bytes_transferred = current_position - prev_position
                        prev_position = current_position
                        new_progress.append({"bytecount": bytes_transferred, "time": time})
                    byte_list_normalized.append({
                        "id": item["id"],
                        "type": item["type"],
                        "progress": new_progress
                    })
                byte_list = byte_list_normalized

            # Calculate total_processed_bytes using validation function
            _, total_processed_bytes, _, _, _ = validate.byte_count_validation(byte_list, byte_count)
        else:
            print(f"  Warning: Could not find byte_list file for {direction}")
            total_processed_bytes = 0

    except Exception as e:
        print(f"  Error loading data for {direction}: {e}")
        return None, 0

    # Calculate throughput at different intervals
    intervals = [1, 2, 5, 10, 50, 100]
    results = []

    for interval_ms in intervals:
        try:
            throughput_results, discarded_stats = tp_calc.calculate_interval_throughput_tracking_discarded_data(
                aggregated_time, byte_count, num_flows, interval_ms, begin_time
            )

            stats = calculate_throughput_statistics(throughput_results)

            results.append({
                'interval_ms': interval_ms,
                'num_points': stats['num_points'],
                'discarded_events': discarded_stats['discarded_objects'],
                'discarded_bytes': discarded_stats['discarded_bytes'],
                'mean_throughput': stats['mean_throughput'],
                'median_throughput': stats['median_throughput'],
                'min_throughput': stats['min_throughput'],
                'max_throughput': stats['max_throughput'],
                'throughput_range': stats['throughput_range']
            })

        except Exception as e:
            print(f"  Error calculating {interval_ms}ms throughput for {direction}: {e}")
            continue

    return results, total_processed_bytes

def main():
    if len(sys.argv) != 3:
        print("Usage: generate_interval_throughput_csv.py <test_directory> <output_csv_file>")
        sys.exit(1)

    test_directory = sys.argv[1]
    output_csv_file = sys.argv[2]

    # Extract test name
    test_name = os.path.basename(test_directory.rstrip('/'))

    print(f"Processing test: {test_name}")

    # Try to load speedtest metadata
    speedtest_json_path = os.path.join(test_directory, "speedtest_result.json")
    metadata = {}
    if os.path.exists(speedtest_json_path):
        try:
            with open(speedtest_json_path, 'r') as f:
                speedtest_data = json.load(f)
                metadata = {
                    'date': speedtest_data.get('date', ''),
                    'time': speedtest_data.get('time', ''),
                    'server': speedtest_data.get('server', ''),
                    'connection_type': speedtest_data.get('connection_type', '')
                }
        except Exception as e:
            print(f"  Warning: Could not load speedtest metadata: {e}")

    # Define CSV fieldnames
    fieldnames = [
        'test_name', 'date', 'time', 'server', 'connection_type',
        'test_direction', 'total_bytes_sent', 'interval_ms', 'num_points', 'discarded_events',
        'discarded_bytes', 'percent_bytes_lost', 'mean_throughput_mbps', 'median_throughput_mbps',
        'min_throughput_mbps', 'max_throughput_mbps', 'throughput_range_mbps'
    ]

    # Check if file exists
    file_exists = os.path.exists(output_csv_file)

    # Collect all rows to write
    rows_to_write = []

    # Process download
    print("  Processing download...")
    download_results, download_total_bytes = process_test_direction(test_directory, 'download')
    if download_results:
        for result in download_results:
            rows_to_write.append({
                'test_name': test_name,
                'date': metadata.get('date', ''),
                'time': metadata.get('time', ''),
                'server': metadata.get('server', ''),
                'connection_type': metadata.get('connection_type', ''),
                'test_direction': 'download',
                'total_bytes_sent': download_total_bytes,
                'interval_ms': result['interval_ms'],
                'num_points': result['num_points'],
                'discarded_events': result['discarded_events'],
                'discarded_bytes': result['discarded_bytes'],
                'percent_bytes_lost': f"{result['discarded_bytes'] / download_total_bytes}",
                'mean_throughput_mbps': f"{result['mean_throughput']:.2f}",
                'median_throughput_mbps': f"{result['median_throughput']:.2f}",
                'min_throughput_mbps': f"{result['min_throughput']:.2f}",
                'max_throughput_mbps': f"{result['max_throughput']:.2f}",
                'throughput_range_mbps': f"{result['throughput_range']:.2f}"
            })

    # Process upload
    print("  Processing upload...")
    upload_results, upload_total_bytes = process_test_direction(test_directory, 'upload')
    if upload_results:
        for result in upload_results:
            rows_to_write.append({
                'test_name': test_name,
                'date': metadata.get('date', ''),
                'time': metadata.get('time', ''),
                'server': metadata.get('server', ''),
                'connection_type': metadata.get('connection_type', ''),
                'test_direction': 'upload',
                'total_bytes_sent': upload_total_bytes,
                'interval_ms': result['interval_ms'],
                'num_points': result['num_points'],
                'discarded_events': result['discarded_events'],
                'discarded_bytes': result['discarded_bytes'],
                'percent_bytes_lost': f"{result['discarded_bytes'] / upload_total_bytes}",
                'mean_throughput_mbps': f"{result['mean_throughput']:.2f}",
                'median_throughput_mbps': f"{result['median_throughput']:.2f}",
                'min_throughput_mbps': f"{result['min_throughput']:.2f}",
                'max_throughput_mbps': f"{result['max_throughput']:.2f}",
                'throughput_range_mbps': f"{result['throughput_range']:.2f}"
            })

    # Write to CSV
    if rows_to_write:
        with open(output_csv_file, 'a', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            # Write header if file is new or empty
            if not file_exists or os.path.getsize(output_csv_file) == 0:
                writer.writeheader()

            # Write all rows
            writer.writerows(rows_to_write)

        print(f"Wrote {len(rows_to_write)} rows to {output_csv_file}")
    else:
        print(f"No data to write for {test_name}")

if __name__ == "__main__":
    main()
