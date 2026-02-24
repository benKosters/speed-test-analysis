#!/usr/bin/env python3
"""
Script to read speedtest_result.json from a test directory and append to CSV.
Usage: python3 append_speedtest_to_csv.py <test_directory> <output_csv>
"""

import json
import csv
import os
import sys
from pathlib import Path

def read_speedtest_json(test_dir):
    """Read speedtest_result.json from the test directory."""
    json_path = Path(test_dir) / "speedtest_result.json"

    if not json_path.exists():
        raise FileNotFoundError(f"speedtest_result.json not found in {test_dir}")

    with open(json_path, 'r') as f:
        data = json.load(f)

    return data

def append_to_csv(data, output_csv):
    """Append data to CSV file, creating it with headers if it doesn't exist."""
    # Define the expected fields in order
    fieldnames = [
        'test_name',
        'date',
        'time',
        'server',
        'connection_type',
        'ping_latency',
        'download_latency',
        'upload_Latency',
        'ookla_download_speed',
        'ookla_upload_speed'
    ]

    # Check if CSV exists to determine if we need to write headers
    file_exists = os.path.isfile(output_csv)

    # Open in append mode
    with open(output_csv, 'a', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        # Write header only if file is new
        if not file_exists:
            writer.writeheader()

        # Write the data row
        writer.writerow(data)

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 append_speedtest_to_csv.py <test_directory> <output_csv>")
        print("Example: python3 append_speedtest_to_csv.py /path/to/test ./results.csv")
        sys.exit(1)

    test_dir = sys.argv[1]
    output_csv = sys.argv[2]

    try:
        # Read the JSON data
        data = read_speedtest_json(test_dir)

        # Add test_name from the directory name
        test_name = os.path.basename(os.path.normpath(test_dir))
        data['test_name'] = test_name

        # Append to CSV
        append_to_csv(data, output_csv)

        print(f"Successfully appended data from {test_dir} to {output_csv}")

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {test_dir}/speedtest_result.json: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error processing {test_dir}: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
