#!/usr/bin/env python3
"""
Aggregate speedtest_result.json metrics from multiple test directories and compute mean/median statistics for:
    1) ping latency
    2) download latency
    3) upload latency
    4) download speed
    5) upload speed

Due to sake of time, this script was written with the help of AI(sadly).
"""

import argparse
import csv
import json
import os
import sys
from pathlib import Path
import statistics


def find_speedtest_results(search_dir, test_filter=None):
    """
    Find all speedtest_result.json files in the search directory.

    Args:
        search_dir: Root directory to search
        test_filter: Optional filter for 'multi' or 'single' connection types

    Returns:
        List of Path objects pointing to speedtest_result.json files
    """
    speedtest_files = []

    # Recursively search for speedtest_result.json files
    for speedtest_file in search_dir.rglob('speedtest_result.json'):
        parent_dir = speedtest_file.parent
        parent_name = parent_dir.name

        # Apply filter if specified
        if test_filter == 'multi' and '-multi-' not in parent_name:
            continue
        if test_filter == 'single' and '-single-' not in parent_name:
            continue

        # Verify it's a valid test directory (should also have netlog.json)
        if (parent_dir / 'netlog.json').exists():
            speedtest_files.append(speedtest_file)

    return sorted(speedtest_files)


def load_speedtest_data(speedtest_files):
    """
    Load speedtest data and group by (server, connection_type).

    Args:
        speedtest_files: List of paths to speedtest_result.json files

    Returns:
        Dictionary mapping (server, connection_type) to list of test results
    """
    grouped_data = {}
    failed_files = []

    for filepath in speedtest_files:
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            # Extract key and add to grouped data
            server = data.get('server', 'unknown')
            connection_type = data.get('connection_type', 'unknown')
            key = (server, connection_type)

            if key not in grouped_data:
                grouped_data[key] = []

            grouped_data[key].append(data)

        except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
            failed_files.append((filepath, str(e)))
            print(f"Warning: Failed to load {filepath}: {e}", file=sys.stderr)

    if failed_files:
        print(f"\nFailed to load {len(failed_files)} file(s)", file=sys.stderr)

    return grouped_data


def compute_statistics(grouped_data):
    """
    Compute mean and median statistics for each configuration.

    Args:
        grouped_data: Dictionary mapping (server, connection_type) to test results

    Returns:
        Dictionary with aggregated statistics for each configuration
    """
    results = {}

    for (server, connection_type), tests in grouped_data.items():
        config_key = f"{server}_{connection_type}"

        # Extract metrics from all tests
        ping_latencies = []
        download_latencies = []
        upload_latencies = []
        download_speeds = []
        upload_speeds = []

        for test in tests:
            # Collect latencies
            if 'ping_latency' in test and test['ping_latency'] is not None:
                ping_latencies.append(test['ping_latency'])

            if 'download_latency' in test and test['download_latency'] is not None:
                download_latencies.append(test['download_latency'])

            # Note: The field name is 'upload_Latency' with capital L
            if 'upload_Latency' in test and test['upload_Latency'] is not None:
                upload_latencies.append(test['upload_Latency'])
            elif 'upload_latency' in test and test['upload_latency'] is not None:
                upload_latencies.append(test['upload_latency'])

            # Collect speeds/throughputs
            if 'ookla_download_speed' in test and test['ookla_download_speed'] is not None:
                download_speeds.append(test['ookla_download_speed'])

            if 'ookla_upload_speed' in test and test['ookla_upload_speed'] is not None:
                upload_speeds.append(test['ookla_upload_speed'])

        # Compute statistics
        results[config_key] = {
            'server': server,
            'connection_type': connection_type,
            'num_tests': len(tests),
            'ping_latency': {
                'mean': round(statistics.mean(ping_latencies), 2) if ping_latencies else None,
                'median': round(statistics.median(ping_latencies), 2) if ping_latencies else None
            },
            'download_latency': {
                'mean': round(statistics.mean(download_latencies), 2) if download_latencies else None,
                'median': round(statistics.median(download_latencies), 2) if download_latencies else None
            },
            'upload_latency': {
                'mean': round(statistics.mean(upload_latencies), 2) if upload_latencies else None,
                'median': round(statistics.median(upload_latencies), 2) if upload_latencies else None
            },
            'download_speed': {
                'mean': round(statistics.mean(download_speeds), 2) if download_speeds else None,
                'median': round(statistics.median(download_speeds), 2) if download_speeds else None
            },
            'upload_speed': {
                'mean': round(statistics.mean(upload_speeds), 2) if upload_speeds else None,
                'median': round(statistics.median(upload_speeds), 2) if upload_speeds else None
            }
        }

    return results


def main():
    parser = argparse.ArgumentParser(
        description='Aggregate speedtest_result.json metrics from multiple test directories.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process all tests in a directory
  %(prog)s /mnt/d/usa-server-tests/

  # Process only multi-flow tests
  %(prog)s /mnt/d/usa-server-tests/ -multi

  # Process single-flow tests with custom output file
  %(prog)s /mnt/d/usa-server-tests/ -single -o my_results.csv

  # Process specific batch
  %(prog)s /mnt/d/usa-server-tests/batch1/
        """
    )

    parser.add_argument(
        'search_directory',
        type=str,
        help='Root directory to search for speedtest_result.json files'
    )

    parser.add_argument(
        '-multi',
        action='store_true',
        help='Process only multi-flow tests (e.g., *-multi-*)'
    )

    parser.add_argument(
        '-single',
        action='store_true',
        help='Process only single-flow tests (e.g., *-single-*)'
    )

    parser.add_argument(
        '-o', '--output',
        type=str,
        default='aggregated_speedtest_metrics.csv',
        help='Output CSV file name (default: aggregated_speedtest_metrics.csv)'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Print verbose output'
    )

    args = parser.parse_args()

    # Validate arguments
    if args.multi and args.single:
        print("Error: Cannot specify both -multi and -single", file=sys.stderr)
        sys.exit(1)

    search_dir = Path(args.search_directory)
    if not search_dir.exists():
        print(f"Error: Directory '{search_dir}' does not exist", file=sys.stderr)
        sys.exit(1)

    if not search_dir.is_dir():
        print(f"Error: '{search_dir}' is not a directory", file=sys.stderr)
        sys.exit(1)

    # Determine test filter
    test_filter = None
    if args.multi:
        test_filter = 'multi'
    elif args.single:
        test_filter = 'single'

    # Find speedtest result files
    print(f"Searching for speedtest_result.json files in: {search_dir}")
    if test_filter:
        print(f"Filter: Only processing {test_filter}-flow tests")
    print()

    speedtest_files = find_speedtest_results(search_dir, test_filter)

    if not speedtest_files:
        print("No speedtest_result.json files found", file=sys.stderr)
        if test_filter:
            print(f"Try running without the -{test_filter} filter", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(speedtest_files)} speedtest_result.json file(s)")
    for file in speedtest_files:
        print(f"  - {file}")
    if args.verbose:
        for f in speedtest_files:
            rel_path = f.relative_to(search_dir)
            print(f"  - {rel_path}")
    print()

    # Load and group data
    print("Loading and grouping data by configuration...")
    grouped_data = load_speedtest_data(speedtest_files)

    print(f"Found {len(grouped_data)} unique configuration(s):")
    for (server, connection_type), tests in grouped_data.items():
        print(f"  - {server} ({connection_type}): {len(tests)} test(s)")
    print()

    # Compute statistics
    print("Computing statistics...")
    results = compute_statistics(grouped_data)

    # Write output to CSV
    output_path = Path(args.output)
    with open(output_path, 'w', newline='') as f:
        # Define CSV columns
        fieldnames = [
            'server',
            'connection_type',
            'num_tests',
            'ping_latency_mean',
            'ping_latency_median',
            'download_latency_mean',
            'download_latency_median',
            'upload_latency_mean',
            'upload_latency_median',
            'download_speed_mean',
            'download_speed_median',
            'upload_speed_mean',
            'upload_speed_median'
        ]

        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        # Flatten and write each configuration
        for config_key, stats in results.items():
            row = {
                'server': stats['server'],
                'connection_type': stats['connection_type'],
                'num_tests': stats['num_tests'],
                'ping_latency_mean': stats['ping_latency']['mean'],
                'ping_latency_median': stats['ping_latency']['median'],
                'download_latency_mean': stats['download_latency']['mean'],
                'download_latency_median': stats['download_latency']['median'],
                'upload_latency_mean': stats['upload_latency']['mean'],
                'upload_latency_median': stats['upload_latency']['median'],
                'download_speed_mean': stats['download_speed']['mean'],
                'download_speed_median': stats['download_speed']['median'],
                'upload_speed_mean': stats['upload_speed']['mean'],
                'upload_speed_median': stats['upload_speed']['median']
            }
            writer.writerow(row)

    print(f"\nResults written to: {output_path}")
    print(f"Total configurations: {len(results)}")

    # Print summary
    print("\nSummary:")
    for config_key, stats in results.items():
        print(f"\n{config_key}:")
        print(f"  Tests: {stats['num_tests']}")
        print(f"  Ping Latency - Mean: {stats['ping_latency']['mean']}ms, Median: {stats['ping_latency']['median']}ms")
        print(f"  Download Latency - Mean: {stats['download_latency']['mean']}ms, Median: {stats['download_latency']['median']}ms")
        print(f"  Upload Latency - Mean: {stats['upload_latency']['mean']}ms, Median: {stats['upload_latency']['median']}ms")
        print(f"  Download Speed - Mean: {stats['download_speed']['mean']} Mbps, Median: {stats['download_speed']['median']} Mbps")
        print(f"  Upload Speed - Mean: {stats['upload_speed']['mean']} Mbps, Median: {stats['upload_speed']['median']} Mbps")


if __name__ == '__main__':
    main()
