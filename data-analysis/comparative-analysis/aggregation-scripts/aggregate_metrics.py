#!/usr/bin/env python3
"""
Used to combine data accoss multiple speed test files into one, unified CSV. Each speed test will generate two types of data: core data, and configuration data.

Core data are data and metadata that do not change depending on the throughput computation configurations, such as latency, total bytes sent, and test duraction.
Configuration data are the data that depends on the throughput computation configuration (bin size, artifact filtering, and data selection), and the results change for each configuration.

This script can aggregate two types of data:
1. Core Data: speedtest_result.json and test_summary.json
2. Configuration Data: configuration_data.csv from upload/download directories

This script was made with AI due to limited time.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import pandas as pd


class TestAggregator:
    def __init__(self, target_dir: str, output_dir: str, test_direction: str = 'both', flow_type: str = 'both', data_mode: str = 'both'):
        """
            target_dir: Directory to search for tests
            output_dir: Directory to save output CSVs
            test_direction: 'download', 'upload', or 'both'
            flow_type: 'single', 'multi', or 'both'
            data_mode: 'core', 'configuration', or 'both'
        """
        self.target_dir = Path(target_dir)
        self.output_dir = Path(output_dir)
        self.test_direction = test_direction
        self.flow_type = flow_type
        self.data_mode = data_mode

        # Tracking
        self.successful_tests = []
        self.failed_tests = []

        # Data containers
        self.core_data = []
        self.configuration_data = []
        self.unique_servers = set()
        self.current_test_number = 0

    def should_process_test(self, test_path: Path) -> bool:
        # Check if test matches flow type filter.
        test_name = test_path.name.lower()

        if self.flow_type == 'single' and 'single' not in test_name:
            return False
        if self.flow_type == 'multi' and 'multi' not in test_name:
            return False

        return True

    def find_test_directories(self) -> List[Path]:
        # Find all test directories containing speedtest_result.json.
        test_dirs = []

        for root, dirs, files in os.walk(self.target_dir):
            if 'speedtest_result.json' in files:
                test_path = Path(root)
                if self.should_process_test(test_path):
                    test_dirs.append(test_path)

        return test_dirs

    def load_json_safe(self, file_path: Path) -> Tuple[Dict, bool]:
        # Load JSON
        # TODO: Update this to use shared JSON structure
        try:
            with open(file_path, 'r') as f:
                return json.load(f), True
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            return {}, False

    def aggregate_core_data(self, test_dir: Path) -> bool:
        """Aggregate configuration-core data."""
        speedtest_path = test_dir / 'speedtest_result.json'

        # Check if speedtest_result.json exists (shared by both phases)
        if not speedtest_path.exists():
            print(f"  Missing: speedtest_result.json")
            return False

        # Load speedtest_result.json
        speedtest_data, success = self.load_json_safe(speedtest_path)
        if not success:
            return False

        # Create base identifiers from speedtest_result.json
        base_info = {
            'test_name': test_dir.name,
            'server': speedtest_data.get('server', 'NULL'),
            'date': speedtest_data.get('date', ''),
            'time': speedtest_data.get('time', 'NULL'),
            'connection_type': speedtest_data.get('connection_type', 'NULL')
            # 'os_type': speedtest_data.get('os_type', 'NULL'),
            # 'chrome_version': speedtest_data.get('chrome_version', 'NULL'),
        }

        at_least_one_success = False

        # Process download test data
        if self.test_direction in ['download', 'both']:
            download_summary_path = test_dir / 'download' / 'test_summary.json'

            if download_summary_path.exists():
                download_summary_data, success = self.load_json_safe(download_summary_path)

                if success:
                    download_row = base_info.copy()
                    download_row['test_direction'] = 'download'

                    # Add speedtest_result download data
                    download_row.update({
                        'ping_latency': speedtest_data.get('ping_latency', 0),
                        'loaded_latency': speedtest_data.get('download_latency', 0),
                        'ookla_reported_throughput': speedtest_data.get('ookla_download_speed', 0),
                        'bulk_throughput_mbps': (download_summary_data.get('total_raw_bytes', 0) * 8 / 1_000_000) / download_summary_data.get('list_duration_sec', 1),  # Convert to Mbps
                    })

                    # Add test_summary download data
                    download_row.update({
                        'duration_ms': download_summary_data.get('total_duration_ms', 0),
                        'total_raw_bytes': download_summary_data.get('total_raw_bytes', 0),
                        'total_processed_bytes': download_summary_data.get('total_processed_bytes', 0),
                        'percent_byte_loss': download_summary_data.get('percent_byte_loss', 0),
                        'total_http_streams': download_summary_data.get('total_http_streams', 0),
                        'num_sockets': download_summary_data.get('num_sockets', 0),
                        'num_points_all_flows_contributing': download_summary_data.get('num_points_all_flows_contributing', 0),
                        'percent_bytes_all_flows_contributing': download_summary_data.get('percent_bytes_all_flows_contributing', 0),
                        'percent_time_all_flows_contributing': download_summary_data.get('percent_time_all_flows_contributing', 0),
                    })

                    self.core_data.append(download_row)
                    at_least_one_success = True
            else:
                print(f"  Missing: download/test_summary.json")
                if self.test_direction == 'download':
                    return False

        # Process upload test data
        if self.test_direction in ['upload', 'both']:
            upload_summary_path = test_dir / 'upload' / 'test_summary.json'

            if upload_summary_path.exists():
                upload_summary_data, success = self.load_json_safe(upload_summary_path)

                if success:
                    upload_row = base_info.copy()
                    upload_row['test_direction'] = 'upload'

                    # Add speedtest_result upload data
                    upload_row.update({
                        'ping_latency': speedtest_data.get('ping_latency', 0),
                        'loaded_latency': speedtest_data.get('upload_latency', speedtest_data.get('upload_Latency', 0)), # Due to a bug with initial tests, but new tests have corrected name
                        'ookla_reported_throughput': speedtest_data.get('ookla_upload_speed', 0),
                        'bulk_throughput_mbps': (upload_summary_data.get('total_raw_bytes', 0) * 8 / 1_000_000) / upload_summary_data.get('list_duration_sec', 1),  # Convert to Mbps
                    })

                    # Add test_summary upload data
                    upload_row.update({
                        'duration_ms': upload_summary_data.get('total_duration_ms', 0),
                        'total_raw_bytes': upload_summary_data.get('total_raw_bytes', 0),
                        'total_processed_bytes': upload_summary_data.get('total_processed_bytes', 0),
                        'percent_byte_loss': upload_summary_data.get('percent_byte_loss', 0),
                        'total_http_streams': upload_summary_data.get('total_http_streams', 0),
                        'num_sockets': upload_summary_data.get('num_sockets', 0),
                        'num_points_all_flows_contributing': upload_summary_data.get('num_points_all_flows_contributing', 0),
                        'percent_bytes_all_flows_contributing': upload_summary_data.get('percent_bytes_all_flows_contributing', 0),
                        'percent_time_all_flows_contributing': upload_summary_data.get('percent_time_all_flows_contributing', 0),
                    })

                    self.core_data.append(upload_row)
                    at_least_one_success = True
            else:
                print(f"  Missing: upload/test_summary.json")
                if self.test_direction == 'upload':
                    return False

        return at_least_one_success

    def aggregate_configuration_data(self, test_dir: Path, test_number: int) -> bool:
        """Aggregate configuration-configuration data."""
        speedtest_path = test_dir / 'speedtest_result.json'

        # Check if speedtest_result.json exists
        if not speedtest_path.exists():
            print(f"  Missing: speedtest_result.json")
            return False

        # Load speedtest_result.json for base identifiers
        speedtest_data, success = self.load_json_safe(speedtest_path)
        if not success:
            return False

        # Track unique servers for filename generation
        server_name = speedtest_data.get('server', 'unknown')
        self.unique_servers.add(server_name)

        base_info = {
            'test_name': test_dir.name,
            'server_name': speedtest_data.get('server', ''),
            'timestamp': f"{speedtest_data.get('date', '')} {speedtest_data.get('time', '')}",
            'os_type': speedtest_data.get('os_type', ''),
            'chrome_version': speedtest_data.get('chrome_version', ''),
        }

        success_count = 0

        # Process download configuration data
        if self.test_direction in ['download', 'both']:
            download_config_path = test_dir / 'download' / 'configuration_metrics.csv'
            if download_config_path.exists():
                try:
                    df = pd.read_csv(download_config_path)
                    # Add base identifiers to all rows
                    df['test_number'] = test_number
                    for key, value in base_info.items():
                        df[key] = value
                    df['test_direction'] = 'download'
                    self.configuration_data.append(df)
                    success_count += 1
                except Exception as e:
                    print(f"  Error loading {download_config_path}: {e}")
            else:
                print(f"  Missing: download/configuration_data.csv")
                if self.test_direction == 'download':
                    return False

        # Process upload configuration data
        if self.test_direction in ['upload', 'both']:
            upload_config_path = test_dir / 'upload' / 'configuration_metrics.csv'
            if upload_config_path.exists():
                try:
                    df = pd.read_csv(upload_config_path)
                    # Add base identifiers to all rows
                    df['test_number'] = test_number
                    for key, value in base_info.items():
                        df[key] = value
                    df['test_direction'] = 'upload'
                    self.configuration_data.append(df)
                    success_count += 1
                except Exception as e:
                    print(f"  Error loading {upload_config_path}: {e}")
            else:
                print(f"  Missing: upload/configuration_data.csv")
                if self.test_direction == 'upload':
                    return False

        return success_count > 0

    def process_test_directory(self, test_dir: Path, test_number: int):
        """Process a single test directory."""
        print(f"Processing: {test_dir.name}")

        success = True
        errors = []

        # Aggregate core data
        if self.data_mode in ['core', 'both']:
            if not self.aggregate_core_data(test_dir):
                success = False
                errors.append("Failed to aggregate core data")

        # Aggregate configuration data
        if self.data_mode in ['configuration', 'both']:
            if not self.aggregate_configuration_data(test_dir, test_number):
                success = False
                errors.append("Failed to aggregate configuration data")

        if success:
            self.successful_tests.append(str(test_dir))
            print(f"  ✓ Success")
        else:
            self.failed_tests.append({
                'path': str(test_dir),
                'errors': errors
            })
            print(f"  ✗ Failed")

    def save_results(self, test_dir: Path):
        """Save aggregated data to CSV files."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Save core data
        if self.data_mode in ['core', 'both'] and self.core_data:
            df = pd.DataFrame(self.core_data)
            output_path = self.output_dir / "aggregated_core_data.csv"
            df.to_csv(output_path, index=False)
            print(f"\n✓ Saved core data to: {output_path}")
            print(f"  Total rows: {len(df)}")

        # Save configuration configuration data (upload and download combined)
        if self.data_mode in ['configuration', 'both'] and self.configuration_data:
            df = pd.concat(self.configuration_data, ignore_index=True)

            # Reorder columns to put test_number first
            if 'test_number' in df.columns:
                cols = ['test_number'] + [col for col in df.columns if col != 'test_number']
                df = df[cols]

            # Use the server name for as part of the file name, but only if aggregating one server
            if len(self.unique_servers) == 1:
                server_name = list(self.unique_servers)[0]
                filename = f"{server_name}_aggregated_configuration_data.csv"
            else:
                filename = "aggregated_configuration_data.csv"

            output_path = self.output_dir / filename
            df.to_csv(output_path, index=False)
            print(f"\n✓ Saved configuration data to: {output_path}")
            print(f"  Total rows: {len(df)}")
            print(f"  Download rows: {len(df[df['test_direction'] == 'download'])}")
            print(f"  Upload rows: {len(df[df['test_direction'] == 'upload'])}")

    def print_summary(self):
        """Print summary of aggregation."""
        print("\n" + "="*60)
        print("AGGREGATION SUMMARY")
        print("="*60)
        print(f"Successful tests: {len(self.successful_tests)}")
        print(f"Failed tests: {len(self.failed_tests)}")

        if self.failed_tests:
            print("\nFailed test details:")
            for failed in self.failed_tests:
                print(f"  - {Path(failed['path']).name}")
                for error in failed['errors']:
                    print(f"    * {error}")

    def run(self):
        """Run the aggregation process."""
        print("="*60)
        print("Speed Test Metrics Aggregation")
        print("="*60)
        print(f"Target directory: {self.target_dir}")
        print(f"Output directory: {self.output_dir}")
        print(f"Flow type filter: {self.flow_type}")
        print(f"Test phase filter: {self.test_direction}")
        print(f"Data mode: {self.data_mode}")
        print("="*60)
        print()

        test_dirs = self.find_test_directories()
        print(f"Found {len(test_dirs)} test directories matching filters\n")

        if not test_dirs:
            print("No test directories found. Exiting.")
            return

        for test_dir in test_dirs:
            self.current_test_number += 1
            self.process_test_directory(test_dir, self.current_test_number)

        print()
        self.save_results(test_dir)
        self.print_summary()


def main():
    parser = argparse.ArgumentParser(
        description='Aggregate speed test metrics from multiple tests',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Aggregate all data from multi-flow tests
  python aggregate_metrics.py -t /path/to/tests -o ./output -f multi

  # Aggregate only core data from download tests
  python aggregate_metrics.py -t /path/to/tests -o ./output -m core -p download

  # Aggregate only configuration data from single-flow tests
  python aggregate_metrics.py -t /path/to/tests -o ./output -m configuration -f single

  # Aggregate both types from a specific batch
  python aggregate_metrics.py -t /path/to/batch_folder -o ./csvs -m both
        """
    )

    parser.add_argument(
        '-t', '--target-dir',
        required=True,
        help='Target directory to search for tests (recursively)'
    )

    parser.add_argument(
        '-o', '--output-dir',
        required=True,
        help='Output directory to save aggregated CSV files'
    )

    parser.add_argument(
        '-m', '--data-mode',
        choices=['core', 'configuration', 'both'],
        default='both',
        help='Type of data to aggregate (default: both)'
    )

    parser.add_argument(
        '-f', '--flow-type',
        choices=['single', 'multi', 'both'],
        default='both',
        help='Filter by flow type: single, multi, or both (default: both)'
    )

    parser.add_argument(
        '-p', '--test-phase',
        choices=['download', 'upload', 'both'],
        default='both',
        help='Filter by test phase: download, upload, or both (default: both)'
    )

    args = parser.parse_args()

    # Validate directories
    if not os.path.isdir(args.target_dir):
        print(f"Error: Target directory does not exist: {args.target_dir}")
        sys.exit(1)

    # Create aggregator and run
    aggregator = TestAggregator(
        target_dir=args.target_dir,
        output_dir=args.output_dir,
        test_direction=args.test_phase,
        flow_type=args.flow_type,
        data_mode=args.data_mode
    )

    aggregator.run()


if __name__ == '__main__':
    main()
