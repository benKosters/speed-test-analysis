"""
Utility functions to help with debugging data structures during data processing.

sum_bytecounts_and_find_time_proportions: Used for finding the frequencies that the time proportion evaluates to... used for seeing the common proportions of times that byte counts must be split into
(used for testing only)
"""

import numpy as np
import json

def byte_count_validation(byte_list, byte_count):
    #1: calculate the raw bytes collected from the test, as well as the duration of the test
    total_raw_bytes = 0
    first_timestamp = float('inf')
    last_timestamp = -1
    for entry in byte_list:
        for progress in entry['progress']:
            total_raw_bytes += int(progress['bytecount'])
            first_timestamp = min([int(progress['time']), first_timestamp])
            last_timestamp = max([int(progress['time']), last_timestamp])


    duration_ms = last_timestamp - first_timestamp
    list_duration_sec = duration_ms / 1000
    #---------------------------collection of bytes/duraction from byte_count--------------------------
    #Next, calculate the total bytes in byte_count - these bytes have been processed according to A and A's method
    total_processed_bytes = 0
    for timestamp, (bytes_count, flows) in byte_count.items():
        total_processed_bytes += bytes_count

    # Convert keys to integers (in case they're strings)
    timestamps = [int(ts) for ts in byte_count.keys()]
    first_timestamp = min(timestamps)
    last_timestamp = max(timestamps)
    duration_ms = last_timestamp - first_timestamp
    count_duration_sec = duration_ms / 1000

    #using the byte_list, loop through the each entry. For each entry, only add the bytecounts if the previous timestamp was different than the last one
    unique_timestamp_bytes = 0
    for entry in byte_list:
        previous_time = None
        for progress in entry['progress']:
            current_time = int(progress['time'])
            if current_time != previous_time:
                unique_timestamp_bytes += int(progress['bytecount'])
                previous_time = current_time

    #pretty print results: table of bytecount and duration comparison between raw and processed
    print(f"{'Metric':<30} | {'Value':<20}")
    print("-" * 55)
    print(f"{'Total Raw Bytes Sent:':<30} | {total_raw_bytes:<20}")
    print(f"{'Duration of raw bytes sent:':<30} | {list_duration_sec:<20.3f}")
    print()
    print(f"{'Sum of byte counts in byte_count':<30} | {total_processed_bytes:<20}")
    print(f"{'Duration of byte_count timestamps:':<30} | {count_duration_sec:<20.3f}")

    print(f"{'Difference between total bytes and processed bytes':<30} | {total_raw_bytes - total_processed_bytes:<20}")
    print(f"Percentage difference raw bytes vs unique timestamp bytes: {((total_raw_bytes - total_processed_bytes) / total_raw_bytes) * 100:.2f}%")
    print("-" * 55)

#Convert the timestamps in byte_count to seconds - #FIXME: confirm that the first timestamp matches the first timestamp in aggregated_time
def normalize_byte_count(byte_count, output_file_path=None):
    """
    Normalize the byte_count dictionary to have timestamps in seconds relative to the first timestamp.

    Converts internal timestamps (milliseconds) to relative seconds for easier analysis and visualization.
    Optionally saves the normalized data to a JSON file.

    Args:
        byte_count (dict): Dictionary mapping timestamps to tuples of (bytecount, flows)
        output_file_path (str, optional): Path to save the normalized data. If None, data is not saved.

    Returns:
        dict: A dictionary with normalized timestamps (in seconds) as keys

    Add these lines to calculate_plot_throughput.py:
        output_file_path = os.path.join(os.path.dirname(__file__), "byte_count_entries.json")
        byte_count_seconds = hf.normalize_byte_count(byte_count, output_file_path)
    """
    if not byte_count:
        print("Warning: Empty byte_count dictionary provided")
        return {}

    # Get the first timestamp to calculate relative time
    first_timestamp = min(byte_count.keys())

    # Create a new dictionary with timestamps converted to seconds
    normalized_byte_count = {}

    for timestamp, (bytes_count, flows) in byte_count.items():
        # Convert from milliseconds to seconds, relative to first timestamp
        relative_time = (timestamp - first_timestamp) / 1000

        # Format with 3 decimal places for consistent precision
        time_key = f"{relative_time:.3f}"

        # Store in new format
        normalized_byte_count[time_key] = {
            "bytes": bytes_count,
            "flows": flows
        }

    # Optionally save the normalized data to a file
    if output_file_path:
        with open(output_file_path, 'w') as output_file:
            json.dump(normalized_byte_count, output_file, indent=4)
        print(f"Normalized byte_count saved to {output_file_path}")

    return normalized_byte_count

#2. Validation for aggregated_time list
def print_aggregated_time_entries(aggregated_time, num_entries):
    """
    Print the first num_entries from aggregated_time list --> also used for testing
    """
    print(f"\nFirst {num_entries} entries in aggregated_time:")
    for i, timestamp in enumerate(aggregated_time[:num_entries]):
        print(f"Index {i}: {timestamp}")

"""
Print any timestamps in the aggregated_time list that are not present in the byte_count dictionary.
(This should be the first and last timestamp, but used to confirm this)
"""
def analyze_missing_timestamps(aggregated_time, byte_count):
    missing_indices = []

    for i, timestamp in enumerate(aggregated_time):
        if timestamp not in byte_count:
            missing_indices.append(i)

    print(f"\nMissing Timestamps Analysis:")
    print(f"Total timestamps in aggregated_time: {len(aggregated_time)}")
    print(f"Total timestamps in byte_count: {len(byte_count)}")
    print(f"Number of missing timestamps: {len(missing_indices)}")
    print(f"Percentage missing: {(len(missing_indices)/len(aggregated_time))*100:.2f}%")

    # if missing_indices:
    #     print("\nFirst 10 indices with missing timestamps:")
    #     for i, index in enumerate(missing_indices[:10]):
    #         print(f"Missing at index {index} (timestamp: {aggregated_time[index]})")
# validation of byte_list aggregation
def sum_bytecounts_and_find_time_proportions(byte_list, aggregated_time):
    """
    Used for finding the frequencies that the time proportion evalues to.
    """
    byte_count = {}

    # Track proportion statistics
    proportion_stats = {
        "total": 0,
        "exact_1": 0,
        "between_0_1": 0,
        "other": 0,
        "distribution": {}
    }

    for entry in byte_list:  # For each http stream
        end_time = -1
        start_time = -1

        for i in range(1, len(aggregated_time)):  # Loop through entire aggregated_time list
            current_list_time = aggregated_time[i]
            prev_list_time = aggregated_time[i-1]

            progress = entry['progress']
            for item in progress:
                if (end_time != -1 and start_time != -1):
                    break

                if ((int(item['time']) > prev_list_time) and start_time == -1):
                    break

                if (int(item['time']) <= prev_list_time):
                    start_time = int(item['time'])

                elif (int(item['time']) >= current_list_time):
                    end_time = int(item['time'])

                if (end_time != -1):
                    # Calculate proportion of bytes for this time interval
                    time_span = end_time - start_time
                    if time_span > 0:  # Avoid division by zero error
                        proportion = (current_list_time - prev_list_time) / time_span

                        # Track proportion statistics
                        proportion_stats["total"] += 1
                        rounded_prop = round(proportion, 2)  # Round to 2 decimal places for binning

                        if rounded_prop in proportion_stats["distribution"]:
                            proportion_stats["distribution"][rounded_prop] += 1
                        else:
                            proportion_stats["distribution"][rounded_prop] = 1

                        # Categorize the proportion
                        if rounded_prop == 1.0:
                            proportion_stats["exact_1"] += 1
                        elif 0 < proportion < 1:
                            proportion_stats["between_0_1"] += 1
                        else:
                            proportion_stats["other"] += 1

                        # Calculate bytes to add based on proportion
                        bytes_to_add = int(item['bytecount']) * proportion

                        # Add to byte_count
                        if current_list_time in byte_count:
                            byte_count[current_list_time][0] += bytes_to_add
                            byte_count[current_list_time][1] += 1
                        else:
                            byte_count[current_list_time] = [bytes_to_add, 1]

            # Reset start and end time for each event
            start_time = -1
            end_time = -1

    # Calculate percentages if we have any proportions
    if proportion_stats["total"] > 0:
        proportion_stats["percent_exact_1"] = (proportion_stats["exact_1"] / proportion_stats["total"]) * 100
        proportion_stats["percent_between_0_1"] = (proportion_stats["between_0_1"] / proportion_stats["total"]) * 100
        proportion_stats["percent_other"] = (proportion_stats["other"] / proportion_stats["total"]) * 100

    # Add the most common proportions
    sorted_distribution = sorted(proportion_stats["distribution"].items(),
                                key=lambda x: x[1], reverse=True)
    proportion_stats["most_common"] = sorted_distribution[:10] if sorted_distribution else []

    return byte_count, proportion_stats

#Throughput validation functions
def print_throughput_entries(throughput_results, num_entries):
    """Print the first num_entries from throughput_results list
    """
    print(f"\nFirst {num_entries} entries in throughput_results:")
    for i, result in enumerate(throughput_results[:num_entries]):
        print(f"Index {i}: Time: {result['time']:.3f}s, Throughput: {result['throughput']:.2f} Mbps")

"""
Print the distribution of the throughput_results list and the time intervals used to calcuate the throughput.
This was used for confirming that the time intervals were correctly calculated for setting a threshold for the time window.
"""
def analyze_throughput_intervals(throughput_results):
    if not throughput_results:
        print("No throughput results to analyze")
        return

    interval_diffs = {}
    for i in range(1, len(throughput_results)):
        diff_ms = (throughput_results[i]['time'] - throughput_results[i-1]['time']) * 1000  # Convert to milliseconds
        diff_key = f"{diff_ms:.1f}ms"
        interval_diffs[diff_key] = interval_diffs.get(diff_key, 0) + 1

    # Print the interval differences in a readable format
    print("\nInterval Time Differences Distribution:")
    print(f"{'Time Diff':>10} | {'Count':>10} | {'Percentage':>10}")
    total_entries = len(throughput_results) - 1

    for interval, count in sorted(interval_diffs.items()):
        percentage = (count / total_entries) * 100
        print(f"{interval:>10} | {count:>10} | {percentage:>9.1f}%")
    print("-" * 40)

"""
Find the mean, median, and range of throughput for all entries -- a rudimentary way of finding the throuhgput over the entire test
This is used for a rough comparison...
"""
def throughput_mean_median_range(throughput_results):
    if not throughput_results:
        print("No throughput data available for analysis")
        return

    throughput_values = [result['throughput'] for result in throughput_results]

    num_points = len(throughput_values)
    mean_throughput = sum(throughput_values) / len(throughput_values)
    median_throughput = np.median(throughput_values)
    min_throughput = min(throughput_values)
    max_throughput = max(throughput_values)
    throughput_range = max_throughput - min_throughput

    print("\nThroughput Statistics:")
    print(f"Number of Throughput Points: {num_points}")
    print(f"Mean Throughput:    {mean_throughput:.2f} Mbps")
    print(f"Median Throughput:  {median_throughput:.2f} Mbps")
    print(f"Minimum Throughput: {min_throughput:.2f} Mbps")
    print(f"Maximum Throughput: {max_throughput:.2f} Mbps")
    print(f"Throughput Range:   {throughput_range:.2f} Mbps")
