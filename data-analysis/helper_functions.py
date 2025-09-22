import os
import json
import sys
import numpy as np
import matplotlib.pyplot as plt

"""
Various helper functions I created (some with the help of AI) when building the plots
for throughput analysis. Keeping these functions in a separate file makes the main plotting script more readable.

The load_json function is used to load the JSON files used for plotting.
Following load_json, the next set of functions are used for printing the first 'x' elements of some of the data structures used.
"""
def load_json(filepath):
    """
    Load the data we need, stored in JSON format.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
    with open(filepath, 'r') as f:
        return json.load(f)

def print_byte_count_entries(byte_count, num_entries):
    """
    Print the first num_entries from byte_count --> used for testing purposes
    """
    for i, (timestamp, [bytes_count, flows]) in enumerate(list(byte_count.items())[:num_entries]):
        print(f"Timestamp: {timestamp}, Bytes: {bytes_count}, Flows: {flows}")

def print_throughput_entries(throughput_results, num_entries):
    """Print the first num_entries from throughput_results list
    """
    print(f"\nFirst {num_entries} entries in throughput_results:")
    for i, result in enumerate(throughput_results[:num_entries]):
        print(f"Index {i}: Time: {result['time']:.3f}s, Throughput: {result['throughput']:.2f} Mbps")

def print_aggregated_time_entries(aggregated_time, num_entries):
    """
    Print the first num_entries from aggregated_time list --> also used for testing
    """
    print(f"\nFirst {num_entries} entries in aggregated_time:")
    for i, timestamp in enumerate(aggregated_time[:num_entries]):
        print(f"Index {i}: {timestamp}")

"""
Given the byte_count dictionary, thie function will loop through each entry in the byte_count and find the distribution of elements
that have the same number of flows contributing to the bytecount.
For example, we can see that 'x' number of events have 1 flow conributing, 'y' events have 2 flows contributing, etc.
"""
def calculate_occurrence_sums(byte_count):
    occurrence_sums = {}
    for timestamp in byte_count:
        num_occurrences = byte_count[timestamp][1]
        if num_occurrences in occurrence_sums:
            occurrence_sums[num_occurrences] += 1
        else:
            occurrence_sums[num_occurrences] = 1

    # Print the sums for each occurrence count
    for occurrence_count, sum_count in sorted(occurrence_sums.items()):
        print(f"Sum of {occurrence_count} flow{'s' if occurrence_count != 1 else ''} contributing: {sum_count}")

    #return occurrence_sums

"""
Find the mean, median, and range of throughput for all entries -- a rudimentary way of finding the throuhgput over the entire test
This is used for a rough comparison...
"""
def throughput_mean_median_range(throughput_results):
    if not throughput_results:
        print("No throughput data available for analysis")
        return

    throughput_values = [result['throughput'] for result in throughput_results]

    mean_throughput = sum(throughput_values) / len(throughput_values)
    median_throughput = np.median(throughput_values)
    min_throughput = min(throughput_values)
    max_throughput = max(throughput_values)
    throughput_range = max_throughput - min_throughput

    print("\nThroughput Statistics:")
    print(f"Mean Throughput:    {mean_throughput:.2f} Mbps")
    print(f"Median Throughput:  {median_throughput:.2f} Mbps")
    print(f"Minimum Throughput: {min_throughput:.2f} Mbps")
    print(f"Maximum Throughput: {max_throughput:.2f} Mbps")
    print(f"Throughput Range:   {throughput_range:.2f} Mbps")

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

"""
Print out any throughput entries that exceed a certain threshold (default is 180 Mbps).
This is used to find any throughput entries that are significantly higher than the rest, so they can be investigated further.
"""
def analyze_high_throughput(throughput_results, threshold=180):
    high_throughput_points = []

    for i, entry in enumerate(throughput_results):
        if entry['throughput'] > threshold:
            high_throughput_points.append((i, entry))

    if high_throughput_points:
        print(f"\nFound {len(high_throughput_points)} points with throughput > {threshold} Mbps:")
        print("-" * 70)
        print(f"{'Index':>6} | {'Time (s)':>10} | {'Throughput (Mbps)':>15}")
        print("-" * 70)

        for index, entry in high_throughput_points:
            print(f"{index:>6} | {entry['time']:>10.3f} | {entry['throughput']:>15.2f}")
    else:
        print(f"\nNo throughput values exceeded {threshold} Mbps")

"""
Print out all the HTTP steam IDs used, their duration, and their corresponding sockets.
If streams use the same socket, find and print the timing differences between when the first source ends, and the next source begins.
"""
def analyze_stream_sockets_and_timing(stream_times):
    socket_to_streams = {}
    print("\nHTTP Stream Information:")
    print("-" * 80)

    for stream_id, info in stream_times.items():
        start_time = info['times'][0]
        end_time = info['times'][1]
        duration = end_time - start_time
        socket = info['socket']

        socket_info = f", Socket: {socket}" if socket is not None else ""
        print(f"Stream ID {stream_id}: Start={start_time}, End={end_time}, Duration={duration}ms{socket_info}")

        # Map stream IDs to their sockets
        if socket is not None:
            if socket not in socket_to_streams:
                socket_to_streams[socket] = []
            socket_to_streams[socket].append((stream_id, start_time, end_time))

    print("\nTiming Differences Between Sources Using the Same Socket:")
    print("-" * 80)

    # Calculate timing differences for sources using the same socket
    for socket, sources in socket_to_streams.items():
        # Sort sources by their start time
        sources.sort(key=lambda x: x[1])  # Sort by start_time
        for i in range(1, len(sources)):
            prev_stream_id, _, prev_end_time = sources[i - 1]
            curr_stream_id, curr_start_time, _ = sources[i]
            time_diff = curr_start_time - prev_end_time
            print(f" \nSocket {socket}: Source {prev_stream_id} ends at {prev_end_time}, "
                  f"Source {curr_stream_id} starts at {curr_start_time}, "
                  f"Time Difference: {time_diff}ms")

    return socket_to_streams


"""
Given an input JSON file (either byte_time_list.json or current_position_list.json),
this function will read the file and sum the byte counts or current positions for each source ID.
Will return a dictionary where the keys are the source IDs and the values are the summed byte counts transferred by the source ID.
The summed byte counts should be equal to the message size(or less if the test ends while the source is still sending data).

This is a modified version of the file summarize_byte_counts.py, which can be used via the command line to print the byte counts
to the terminal.
"""
def sum_byte_counts(input_file):

    try:
        # Read the JSON file
        with open(input_file, 'r') as file:
            data = json.load(file)

        # Determine file type based on filename
        filename = os.path.basename(input_file)
        id_sums = {}

        if 'current_position_list' in filename:
            print("Processing current_position_list format...")
            for item in data:
                id_num = item['id']
                max_position = 0

                # Get the maximum current_position value
                for progress in item['progress']:
                    if 'current_position' in progress:
                        max_position = max(max_position, progress['current_position'])

                id_sums[id_num] = max_position

        elif 'byte_time_list' in filename:
            print("Processing byte_time_list format...")
            for item in data:
                id_num = item['id']
                byte_sum = 0

                # Sum the bytecount values
                for progress in item['progress']:
                    if 'bytecount' in progress:
                        byte_sum += progress['bytecount']

                id_sums[id_num] = byte_sum

        else:
            raise ValueError("Unknown file format. Expecting 'current_position_list.json' or 'byte_time_list.json'")

        return id_sums

    except FileNotFoundError:
        print(f"Error: Could not find file '{input_file}'", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: '{input_file}' is not a valid JSON file", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

#----------------------------------Investigating spikes in upload tests----------------------------------
"""
The following functions transform the current_position_list.json file so that we can investigate the spikes in the throughput
that occur after a gap.
"""
def normalize_current_position_list(current_position_list, begin_time, output_file_path=None):
    """
    Normalize the timestamps in current_position_list to match the graph's relative time
    and calculate incremental byte counts from cumulative data.
    Optionally save the normalized data to a file for easier inspection.

    Args:
        current_position_list (list): The raw current_position_list data.
        begin_time (int): The starting timestamp for normalization.
        output_file_path (str, optional): Path to save the normalized data. If None, the data is not saved.

    Returns:
        list: A list of normalized current_position_list entries with incremental byte counts.

    Add these lines to calculate_plot_throughput.py:
    normalized_output_path = os.path.join(os.path.dirname(__file__), "normalized_current_position_list.json")
    normalized_current_list = hf.normalize_current_position_list(current_position_list=current_list,begin_time=begin_time, output_file_path=normalized_output_path)


    """
    normalized_data = []

    for entry in current_position_list:
        normalized_progress = []
        prev_position = 0  # Initialize the previous position for incremental calculation

        for progress in entry['progress']:
            # Normalize the timestamp
            normalized_time = (int(progress['time']) - begin_time) / 1000  # Convert to seconds

            # Calculate incremental byte count
            current_position = progress['current_position']
            bytes_transferred = current_position - prev_position
            prev_position = current_position  # Update the previous position

            # Add the normalized and incremental data to the progress list
            normalized_progress.append({
                "bytecount": bytes_transferred,
                "time": f"{normalized_time:.3f}"  # Keep precision for easier comparison
            })

        # Append the transformed entry to the normalized data
        normalized_data.append({
            "id": entry['id'],
            "type": entry['type'],
            "progress": normalized_progress
        })

    # Optionally save the normalized data to a file
    if output_file_path:
        with open(output_file_path, 'w') as f:
            json.dump(normalized_data, f, indent=4)
        print(f"Normalized current_position_list saved to {output_file_path}")

    return normalized_data

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


#----------------------------------Cache data used for throughput calculation----------------------------------#
"""
For testing purposes, the throughput calculation script may be run mpultiple times for the same test.
Since the algorithm for calculating throughput is inefficent, this rudimentary "caching" technique saves time for recomputing
values again (especially for CARROT tests)

The "cached" data is just read and written to a JSON file.
"""
def set_cached_data(data, data_name, test_path):
    # these files will be in the cached_data/ directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cache_dir = os.path.join(script_dir, 'cached_data')

    # Create the directory if it doesn't exist(the cached_data directory should be in .gitignore)
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
        print(f"Created cache directory: {cache_dir}")

    # Extract the test identifier from the path
    # We want to use the full relative path from the experiment directory
    # Example: for '/path/to/michwave-multi-1/download' we want 'michwave-multi-1/download'
    test_dir = os.path.abspath(test_path)
    test_name = os.path.join(os.path.basename(os.path.dirname(test_dir)), os.path.basename(test_dir))

    # Define the cache file path
    cache_file = os.path.join(cache_dir, f"{data_name}.json")

    # Create a serializable version of the data
    if data_name == 'byte_count':
        serializable_data = {}
        for timestamp, (bytes_count, flows) in data.items():
            serializable_data[str(timestamp)] = {
                "bytes": bytes_count,
                "flows": flows
            }

    elif data_name == 'aggregated_time':
        serializable_data = [int(x) if isinstance(x, (int, float)) else x for x in data]
    elif data_name == 'stream_times':
        serializable_data = {}
        for stream_id, info in data.items():
            serializable_data[str(stream_id)] = {
                "times": info['times'],
                "socket": info['socket']
            }
    else:
        serializable_data = data

    # Create a wrapper object that includes just the test identifier and data
    cache_wrapper = {
        "test_name": test_name,
        "data": serializable_data
    }

    # Write data to the cache file
    with open(cache_file, 'w') as f:
        json.dump(cache_wrapper, f, indent=2)

    print(f"Cached {data_name} for test '{test_name}' to {cache_file}")
    return cache_file

def get_cached_data(data_name, test_path):

    script_dir = os.path.dirname(os.path.abspath(__file__))
    cache_dir = os.path.join(script_dir, 'cached_data')

    test_dir = os.path.abspath(test_path)
    test_name = os.path.join(os.path.basename(os.path.dirname(test_dir)), os.path.basename(test_dir))

    # Create the full path to the cached file
    cache_file = os.path.join(cache_dir, f"{data_name}.json")

    if not os.path.exists(cache_file):
        print(f"Cache file not found: {cache_file}")
        return None

    # Load the cached data
    try:
        with open(cache_file, 'r') as f:
            cache_wrapper = json.load(f)

        if cache_wrapper.get("test_name") != test_name:
            print(f"Cache mismatch: Found cache for test '{cache_wrapper.get('test_name')}', but current test is '{test_name}'")
            return None

        # Extract the actual data
        data = cache_wrapper.get("data")

        if data is None:
            print(f"Invalid cache format in {cache_file}")
            return None

        # Convert data back to the original format
        if data_name == 'byte_count':
            converted_data = {}
            for timestamp_str, values in data.items():
                converted_data[int(timestamp_str)] = [values["bytes"], values["flows"]]
            data = converted_data
        elif data_name == 'aggregated_time':
            # Ensure numeric values
            data = [int(x) if isinstance(x, str) and x.isdigit() else x for x in data]
        elif data_name == 'stream_times':
            # Convert stream_times back to original format
            converted_data = {}
            for stream_id_str, info in data.items():
                converted_data[int(stream_id_str) if stream_id_str.isdigit() else stream_id_str] = {
                    "times": info['times'],
                    "socket": info['socket']
                }
            data = converted_data

        print(f"Loaded cached {data_name} for test '{test_name}'")
        return data

    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error loading cache file {cache_file}: {e}")
        return None
