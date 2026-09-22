#!/usr/bin/env python3
"""
Compute the largest time gap between consecutive events in byte_count.json
Usage: python3 compute_largest_bytecount_gap.py <path_to_byte_count.json>
"""

import json
import sys
import argparse


def compute_largest_gap(json_path):
    """
    Load byte_count.json and find the largest gap between consecutive timestamps.

    Args:
        json_path: Path to byte_count.json file

    Returns:
        tuple: (max_gap_ms, start_time, end_time, gap_seconds)
    """
    with open(json_path, 'r') as f:
        data = json.load(f)

    # Convert string keys to integers and sort
    timestamps = sorted([int(ts) for ts in data.keys()])

    if len(timestamps) < 2:
        print("Not enough events to compute a gap")
        return None

    # Find largest gap
    max_gap = 0
    max_gap_start = None
    max_gap_end = None

    for i in range(1, len(timestamps)):
        gap = timestamps[i] - timestamps[i-1]
        if gap > max_gap:
            max_gap = gap
            max_gap_start = timestamps[i-1]
            max_gap_end = timestamps[i]

    return max_gap, max_gap_start, max_gap_end


def main():
    parser = argparse.ArgumentParser(description='Find largest gap in byte_count events')
    parser.add_argument('byte_count_file', type=str, help='Path to byte_count.json file')

    args = parser.parse_args()

    try:
        result = compute_largest_gap(args.byte_count_file)

        if result:
            max_gap_ms, start_time, end_time = result
            max_gap_sec = max_gap_ms / 1000.0

            print(f"Largest gap: {max_gap_ms} ms ({max_gap_sec:.3f} seconds)")
            print(f"Gap occurred between timestamps: {start_time} -> {end_time}")

    except FileNotFoundError:
        print(f"Error: File not found - {args.byte_count_file}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON - {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
