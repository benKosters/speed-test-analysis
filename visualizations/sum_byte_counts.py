"""
This script sums the bytecounts or current positions for each HTTP stream ID.
The test is run by: python3 sum_byte_counts.py <input_file.json>
Handles both byte_time_list.json and current_position_list.json formats.

Addition: also calculates the duration of the test based on the timestamps in the JSON file.
"""

import json
import argparse
import sys
import os

def calculate_current_position_sums(data):
    id_sums = {}
    for item in data:
        id_num = item['id']
        max_position = 0

        # Get the maximum current_position value
        for progress in item['progress']:
            if 'current_position' in progress:
                max_position = max(max_position, progress['current_position'])

        id_sums[id_num] = max_position
    return id_sums

def calculate_bytecount_sums(data):
    id_sums = {}
    for item in data:
        id_num = item['id']
        byte_sum = 0

        for progress in item['progress']:
            if 'bytecount' in progress:
                byte_sum += progress['bytecount']

        id_sums[id_num] = byte_sum
    return id_sums

def find_duration(data):
    first_timestamp = int(data[0]['progress'][0]['time'])
    last_timestamp = int(data[-1]['progress'][-1]['time'])

    duration_ms = last_timestamp - first_timestamp
    duration_seconds = duration_ms / 1000.0

    return duration_seconds

def main():
    parser = argparse.ArgumentParser(description='Sum byte counts from a JSON file.')
    parser.add_argument('input_file', help='Path to the JSON input file')
    args = parser.parse_args()

    try:
        # Read the JSON file
        with open(args.input_file, 'r') as file:
            data = json.load(file)

        # Determine file type based on filename
        filename = os.path.basename(args.input_file)
        if 'current_position_list' in filename:
            id_sums = calculate_current_position_sums(data)
            print("Processing current_position_list format...")
        elif 'byte_time_list' in filename:
            id_sums = calculate_bytecount_sums(data)
            print("Processing byte_time_list format...")
        else:
            print("Unknown file format. Expecting 'current_position_list.json' or 'byte_time_list.json'")
            sys.exit(1)

        # Print results
        for id_num, total in sorted(id_sums.items()):
            print(f"{id_num}: {total}")

        print(f"Duration: {find_duration(data)} seconds")

    except FileNotFoundError:
        print(f"Error: Could not find file '{args.input_file}'", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: '{args.input_file}' is not a valid JSON file", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()