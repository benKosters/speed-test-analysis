#!/usr/bin/env python3
"""
Aggregate speed test metrics from multiple tests.

This script can aggregate two types of data:
1. Configuration-independent: speedtest_result.json and test_summary.json
2. Configuration-dependent: configuration_data.csv from upload/download directories
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import pandas as pd


class TestAggregator:
    def __init__(self, target_dir: str, output_dir: str, test_type: str = 'both', flow_type: str = 'both', data_mode: str = 'both'):
        """
            target_dir: Directory to search for tests
            output_dir: Directory to save output CSVs
            test_type: 'download', 'upload', or 'both'
            flow_type: 'single', 'multi', or 'both'
            data_mode: 'independent', 'dependent', or 'both'
        """
        self.target_dir = Path(target_dir)
        self.output_dir = Path(output_dir)
        self.test_type = test_type
        self.flow_type = flow_type
        self.data_mode = data_mode

        # Tracking
        self.successful_tests = []
        self.failed_tests = []

        # Data containers
        self.independent_data = []
        self.dependent_download_data = []
        self.dependent_upload_data = []

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

    def aggregate_independent_data(self, test_dir: Path) -> bool:
        """Aggregate configuration-independent data."""
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
            'test_directory': str(test_dir),
            'test_name': test_dir.name,
            'server_name': speedtest_data.get('server', ''),
            'server_id': speedtest_data.get('server', ''),
            'server_location': speedtest_data.get('server', ''),
            'timestamp': f"{speedtest_data.get('date', '')} {speedtest_data.get('time', '')}",
            'os_type': speedtest_data.get('os_type', ''),
            'chrome_version': speedtest_data.get('chrome_version', ''),
        }

        at_least_one_success = False

        # Process download test data
        if self.test_type in ['download', 'both']:
            download_summary_path = test_dir / 'download' / 'test_summary.json'

            if download_summary_path.exists():
                download_summary_data, success = self.load_json_safe(download_summary_path)

                if success:
                    download_row = base_info.copy()
                    download_row['test_phase'] = 'download'

                    # Add speedtest_result download data (now stored at root level)
                    download_row.update({
                        'ping_latency': speedtest_data.get('ping_latency', 0),
                        'download_latency': speedtest_data.get('download_latency', 0),
                        'ookla_download_speed': speedtest_data.get('ookla_download_speed', 0),
                    })

                    # Add test_summary download data
                    download_row.update({
                        'duration_ms': download_summary_data.get('total_duration_ms', 0),
                        'total_bytes': download_summary_data.get('total_bytes', 0),
                        'total_raw_bytes': download_summary_data.get('total_raw_bytes', 0),
                        'total_processed_bytes': download_summary_data.get('total_processed_bytes', 0),
                        'percent_byte_loss': download_summary_data.get('percent_byte_loss', 0),
                        'total_http_streams': download_summary_data.get('total_http_streams', 0),
                        'num_sockets': download_summary_data.get('num_sockets', 0),
                        'num_points_all_flows_contributing': download_summary_data.get('num_points_all_flows_contributing', 0),
                        'percent_bytes_all_flows_contributing': download_summary_data.get('percent_bytes_all_flows_contributing', 0),
                        'percent_time_all_flows_contributing': download_summary_data.get('percent_time_all_flows_contributing', 0),
                    })

                    self.independent_data.append(download_row)
                    at_least_one_success = True
            else:
                print(f"  Missing: download/test_summary.json")
                if self.test_type == 'download':
                    return False

        # Process upload test data
        if self.test_type in ['upload', 'both']:
            upload_summary_path = test_dir / 'upload' / 'test_summary.json'

            if upload_summary_path.exists():
                upload_summary_data, success = self.load_json_safe(upload_summary_path)

                if success:
                    upload_row = base_info.copy()
                    upload_row['test_phase'] = 'upload'

                    # Add speedtest_result upload data (now stored at root level)
                    upload_row.update({
                        'ping_latency': speedtest_data.get('ping_latency', 0),
                        'upload_latency': speedtest_data.get('upload_Latency', 0),  # Note: capital L in Latency
                        'ookla_upload_speed': speedtest_data.get('ookla_upload_speed', 0),
                    })

                    # Add test_summary upload data
                    upload_row.update({
                        'duration_ms': upload_summary_data.get('total_duration_ms', 0),
                        'total_bytes': upload_summary_data.get('total_bytes', 0),
                        'total_raw_bytes': upload_summary_data.get('total_raw_bytes', 0),
                        'total_processed_bytes': upload_summary_data.get('total_processed_bytes', 0),
                        'percent_byte_loss': upload_summary_data.get('percent_byte_loss', 0),
                        'total_http_streams': upload_summary_data.get('total_http_streams', 0),
                        'num_sockets': upload_summary_data.get('num_sockets', 0),
                        'num_points_all_flows_contributing': upload_summary_data.get('num_points_all_flows_contributing', 0),
                        'percent_bytes_all_flows_contributing': upload_summary_data.get('percent_bytes_all_flows_contributing', 0),
                        'percent_time_all_flows_contributing': upload_summary_data.get('percent_time_all_flows_contributing', 0),
                    })

                    self.independent_data.append(upload_row)
                    at_least_one_success = True
            else:
                print(f"  Missing: upload/test_summary.json")
                if self.test_type == 'upload':
                    return False

        return at_least_one_success

    def aggregate_dependent_data(self, test_dir: Path) -> bool:
        """Aggregate configuration-dependent data."""
        speedtest_path = test_dir / 'speedtest_result.json'

        # Check if speedtest_result.json exists
        if not speedtest_path.exists():
            print(f"  Missing: speedtest_result.json")
            return False

        # Load speedtest_result.json for base identifiers
        speedtest_data, success = self.load_json_safe(speedtest_path)
        if not success:
            return False

        base_info = {
            'test_directory': str(test_dir),
            'test_name': test_dir.name,
            'server_name': speedtest_data.get('server', ''),
            'timestamp': f"{speedtest_data.get('date', '')} {speedtest_data.get('time', '')}",
            'os_type': speedtest_data.get('os_type', ''),
            'chrome_version': speedtest_data.get('chrome_version', ''),
        }

        success_count = 0

        # Process download configuration data
        if self.test_type in ['download', 'both']:
            download_config_path = test_dir / 'download' / 'configuration_metrics.csv'
            if download_config_path.exists():
                try:
                    df = pd.read_csv(download_config_path)
                    # Add base identifiers to all rows
                    for key, value in base_info.items():
                        df[key] = value
                    df['test_phase'] = 'download'
                    self.dependent_download_data.append(df)
                    success_count += 1
                except Exception as e:
                    print(f"  Error loading {download_config_path}: {e}")
            else:
                print(f"  Missing: download/configuration_data.csv")
                if self.test_type == 'download':
                    return False

        # Process upload configuration data
        if self.test_type in ['upload', 'both']:
            upload_config_path = test_dir / 'upload' / 'configuration_data.csv'
            if upload_config_path.exists():
                try:
                    df = pd.read_csv(upload_config_path)
                    # Add base identifiers to all rows
                    for key, value in base_info.items():
                        df[key] = value
                    df['test_phase'] = 'upload'
                    self.dependent_upload_data.append(df)
                    success_count += 1
                except Exception as e:
                    print(f"  Error loading {upload_config_path}: {e}")
            else:
                print(f"  Missing: upload/configuration_data.csv")
                if self.test_type == 'upload':
                    return False

        return success_count > 0

    def process_test_directory(self, test_dir: Path):
        """Process a single test directory."""
        print(f"Processing: {test_dir.name}")

        success = True
        errors = []

        # Aggregate independent data
        if self.data_mode in ['independent', 'both']:
            if not self.aggregate_independent_data(test_dir):
                success = False
                errors.append("Failed to aggregate independent data")

        # Aggregate dependent data
        if self.data_mode in ['dependent', 'both']:
            if not self.aggregate_dependent_data(test_dir):
                success = False
                errors.append("Failed to aggregate dependent data")

        if success:
            self.successful_tests.append(str(test_dir))
            print(f"  ✓ Success")
        else:
            self.failed_tests.append({
                'path': str(test_dir),
                'errors': errors
            })
            print(f"  ✗ Failed")

    def save_results(self):
        """Save aggregated data to CSV files."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Save independent data
        if self.data_mode in ['independent', 'both'] and self.independent_data:
            df = pd.DataFrame(self.independent_data)
            output_path = self.output_dir / 'aggregated_independent_data.csv'
            df.to_csv(output_path, index=False)
            print(f"\n✓ Saved independent data to: {output_path}")
            print(f"  Total rows: {len(df)}")

        # Save dependent download data
        if self.data_mode in ['dependent', 'both'] and self.dependent_download_data:
            df = pd.concat(self.dependent_download_data, ignore_index=True)
            output_path = self.output_dir / 'aggregated_download_configuration_data.csv'
            df.to_csv(output_path, index=False)
            print(f"\n✓ Saved download configuration data to: {output_path}")
            print(f"  Total rows: {len(df)}")

        # Save dependent upload data
        if self.data_mode in ['dependent', 'both'] and self.dependent_upload_data:
            df = pd.concat(self.dependent_upload_data, ignore_index=True)
            output_path = self.output_dir / 'aggregated_upload_configuration_data.csv'
            df.to_csv(output_path, index=False)
            print(f"\n✓ Saved upload configuration data to: {output_path}")
            print(f"  Total rows: {len(df)}")

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
        print(f"Test phase filter: {self.test_type}")
        print(f"Data mode: {self.data_mode}")
        print("="*60)
        print()

        test_dirs = self.find_test_directories()
        print(f"Found {len(test_dirs)} test directories matching filters\n")

        if not test_dirs:
            print("No test directories found. Exiting.")
            return

        for test_dir in test_dirs:
            self.process_test_directory(test_dir)

        print()
        self.save_results()
        self.print_summary()


def main():
    parser = argparse.ArgumentParser(
        description='Aggregate speed test metrics from multiple tests',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Aggregate all data from multi-flow tests
  python aggregate_metrics.py -t /path/to/tests -o ./output -f multi

  # Aggregate only independent data from download tests
  python aggregate_metrics.py -t /path/to/tests -o ./output -m independent -p download

  # Aggregate only configuration-dependent data from single-flow tests
  python aggregate_metrics.py -t /path/to/tests -o ./output -m dependent -f single

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
        choices=['independent', 'dependent', 'both'],
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
        test_type=args.test_phase,
        flow_type=args.flow_type,
        data_mode=args.data_mode
    )

    aggregator.run()


if __name__ == '__main__':
    main()
