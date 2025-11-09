"""
The functions for preparing the data are:
1) normalize_test_data: Normalize either byte_time_list.json or current_position_list.json, depending on the test

2) aggregate_timestamps_and_find_stream_durations: aggregates the timestamps from all sources and finds the start and end times for each HTTP stream. It also finds the socket that each stream uses if socket_file is available.

3) sum_bytecounts_for_timestamps: Finds the proportion of byte counts for each interval, and how many flows are contributing at each byte count
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import utilities

#------------------------------------Data Normalization------------------------------------------------
def normalize_test_data(byte_file, current_file, latency_file):
    # Load byte list first to determine test type
    byte_list = utilities.load_json(byte_file)
    print("The length of byte_list is:", len(byte_list))  # Verify byte_list is loaded correctly

    test_type = None

    if byte_list == []:  # For upload test
        test_type = "upload"
        current_list = utilities.load_json(current_file)
        print("Length of current position list:", len(current_list))

        # Transform cumulative data into incremental byte data
        byte_list = []
        for item in current_list:
            new_progress = []
            prev_position = 0  # Initialize the previous position

            for progress in item["progress"]:
                current_position = progress["current_position"]
                time = progress["time"]

                # Difference between positions is the number of bytes transferred
                bytes_transferred = current_position - prev_position
                prev_position = current_position  # Update previous position

                # Add the incremental data to the new progress list
                new_progress.append({"bytecount": bytes_transferred, "time": time})

            # Append the transformed item to the uncumulated list
            byte_list.append({
                "id": item["id"],
                "type": item["type"],
                "progress": new_progress
            })
    else:  # For download test
        test_type = "download"
        # Load the latency file only if it exists (unloaded latency is optional)
        if os.path.exists(latency_file):
            latency_data = utilities.load_json(latency_file)
            print("Latency loaded")
            print("Size of latency list:", len(latency_data), "\n")

            # Create a dictionary to map IDs to the first receive time from the latency file
            latency_time_map = {entry['sourceID']: int(entry['recv_time'][0]) for entry in latency_data
                       if 'recv_time' in entry and entry['recv_time']}
            print("Unique source IDs:", len(latency_time_map))

            # For every unique source ID, prepend a zero-byte entry with the first receive time
            for entry in byte_list:
                id = entry['id']
                progress = entry['progress']
                # If the ID exists in the latency map, prepend the 0th time entry
                if id in latency_time_map:
                    zero_time_entry = {
                        "bytecount": 0,  # Bytecount at recv_time is 0, because no bytes have been received yet
                        "time": latency_time_map[id]
                    }
                    progress.insert(0, zero_time_entry)  # Prepend to the progress list
        else:
            print("No unloaded latency file found - throughput calculation will not include unloaded latency timing")
            print("Only loaded latency (if available) will be used for plotting")

    print("Length of byte_list after normalization:", len(byte_list))
    return byte_list, test_type
#-----------------------------------Timestamp Aggregation---------------------------------------------
def aggregate_timestamps_and_find_stream_durations(byte_list, socket_file):
    """
    The aggregated_time_list contains all the unique timestamps from all sources in the test.
    If there are multiple tests, these timestamps should overlap.

    This function:
    1. Extracts unique timestamps from all sources
    2. Records the start and end times for each source
    3. Finds the socket each source uses if socket_file is available

    Args:
        byte_list (list): List of byte transfer entries with progress data
        socket_file (str): Path to socketIds.txt file

    Returns:
        tuple: (aggregated_time, source_times, test_type, begin_time)
            - aggregated_time: List of all unique timestamps from all sources
            - source_times: Dictionary mapping source IDs to timing and socket info
            - begin_time: The earliest timestamp in the aggregated data
    """
    aggregated_time = []
    source_times = {}

    # Step 1: Extract timestamps and source timing information
    for entry in byte_list:  # For every source ID...
        progress = entry['progress']
        source_id = entry['id']

        # Find the "begin" and "end" time for each source (first and last timestamps that have a bytecount)
        if progress:
            source_times[source_id] = {
                'times': [int(progress[0]['time']), int(progress[-1]['time'])],
                'socket': None  # Will be populated later
            }

            # Add  unique timestamps to aggregated_time
            for item in progress:
                timestamp = int(item['time'])
                if timestamp not in aggregated_time:
                    aggregated_time.append(timestamp)

    #Find the socket that each source uses
    if os.path.exists(socket_file):
        try:
            # First try to load as JSON
            socket_data = utilities.load_json(socket_file)
            if isinstance(socket_data, list) and len(socket_data) > 0 and isinstance(socket_data[0], list):
                # Process JSON list format
                for entry in socket_data:
                    if len(entry) >= 3:
                        source_id = entry[0]  # First element is source_id
                        socket_id = entry[2]  # Third element is socket_id
                        if source_id in source_times:
                            source_times[source_id]['socket'] = socket_id
            else:
                # For backward capability where socketIds.txt is still used, parse as text file
                with open(socket_file, 'r') as f:
                    for line in f:
                        try:
                            source_id, _, socket_id = map(int, line.strip().split(','))
                            if source_id in source_times:
                                source_times[source_id]['socket'] = socket_id
                        except (ValueError, IndexError):
                            print(f"Warning: Invalid line in socket file: {line.strip()}")
        except Exception as e:
            print(f"Error processing socket file: {e}")
            # Fallback to text file parsing
            with open(socket_file, 'r') as f:
                for line in f:
                    try:
                        source_id, _, socket_id = map(int, line.strip().split(','))
                        if source_id in source_times:
                            source_times[source_id]['socket'] = socket_id
                    except (ValueError, IndexError):
                        print(f"Warning: Invalid line in socket file: {line.strip()}")

    # Step 3: Sort timestamps and find the beginning time
    aggregated_time.sort()
    begin_time = aggregated_time[0]

    print("Number of aggregated timestamps:", len(aggregated_time))

    return aggregated_time, source_times, begin_time
#-----------------------------------Bytecount Summation---------------------------------------------
def sum_all_bytecounts_across_http_streams(byte_list, aggregated_time):

    """
    Sum byte counts for all unique timestamps across HTTP streams.

    This improved implementation:
    1. Properly handles duplicate timestamps within a single stream
    2. Aggregates bytes from all streams that contribute to each timestamp
    3. Tracks the number of unique flows contributing at each timestamp

    Args:
        byte_list (list): List of HTTP stream entries with progress data
        aggregated_time (list): Sorted list of all unique timestamps

    Returns:
        dict: Dictionary mapping timestamps to tuples of (bytecount, number_of_flows)
    """
    byte_count = {}

    for timestamp in aggregated_time:
        byte_count[timestamp] = [0, 0]  # [bytecount, flows] - initialize to zero

    for entry in byte_list: # For each HTTP stream:
        source_id = entry['id']
        progress = entry['progress']

        stream_bytes = {} # This structure looks like a http stream's progress list, but with the bytecounts of duplicate timestamps summed into one event
        for item in progress:
            timestamp = int(item['time'])
            bytecount = int(item['bytecount'])

            if timestamp in stream_bytes:
                stream_bytes[timestamp] += bytecount
            else:
                stream_bytes[timestamp] = bytecount

        # Since the stream_bytes is a dictionary, sort the timestamps
        stream_timestamps = sorted(stream_bytes.keys())
        if not stream_timestamps:
            continue  # Skip this stream if there are no timestamps (this should never occur)

        # Distribute bytes across the smaller sub-intervals of the aggregated timestamps
        for i in range(1, len(aggregated_time)):
            #smallest sub-interval:
            current_time = aggregated_time[i]
            prev_time = aggregated_time[i-1]

            for j in range(len(stream_timestamps) - 1): #  For each HTTP stream
                #Look at the current interval of timestamps from the stream - this should be >= the intervals in aggregated_time
                start_time = stream_timestamps[j]
                end_time = stream_timestamps[j+1]

                # Skip if this interval doesn't overlap with our time window
                if end_time <= prev_time or start_time >= current_time:
                    continue

                # Calculate the time-based proportion of bytes to add
                interval_duration = end_time - start_time
                if interval_duration <= 0:
                    continue  # Skip invalid intervals

                # Calculate overlap between the http stream interval and the current sub-interval
                overlap_start = max(prev_time, start_time)
                overlap_end = min(current_time, end_time)
                proportion = (overlap_end - overlap_start) / interval_duration

                if proportion <= 0:
                    continue  # Skip if no meaningful overlap

                # Calculate bytes to add to the sub-interval from the aggregated timestamps
                bytes_to_add = stream_bytes[start_time] * proportion

                # Add bytes to the current timestamp entry
                if current_time in byte_count:
                    byte_count[current_time][0] += bytes_to_add

                    # Increment the flow count at this timestamp
                    if j == 0 or (prev_time > stream_timestamps[j-1]):
                        byte_count[current_time][1] += 1


    print(f"Length of byte_count: {len(byte_count)}")
    return byte_count

def find_percentage_of_test_all_flows_contributing():
    pass