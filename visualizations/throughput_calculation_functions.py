"""
This file contains the important functions for procssing data so that the throughput can be calculated.

The functions for preparing the data are:
1) normalize_test_data: Normalize either byte_time_list.json or current_position_list.json, depending on the test

2) aggregate_timestamps_and_find_stream_durations: aggregates the timestamps from all sources and finds the start and end times for each HTTP stream. It also finds the socket that each stream uses if socket_file is available.

3) sum_bytecounts_for_timestamps: Finds the proportion of byte counts for each interval, and how many flows are contributing at each byte count

4) sum_bytecounts_and_find_time_proportions: Used for finding the frequencies that the time proportion evaluates to... used for seeing the common proportions of times that byte counts must be split into
(used for testing only)

There are three methods of calculating throughput:
1. Traditional method: A and A's method of calculating throughput, which converts byte_count entries into throughput values.

2. Interval method: This method uses a threshold to determine the minimum time interval used in calculating the throughput. This is the current method of calculating throughput.
If a data point has a time interval less than the threshold, it is combined with the next data point so that the time interval is greater than or equal to the threshold.

3. Less flows method (used for testing only): This method calculates throughput for entries with num_flows and num_flows - 1, keeping them in separate lists.
    Both lists follow the same time interval threshold calculation technique as method #2.


"""
import os
import helper_functions as hf
#------------------------------------Data Normalization------------------------------------------------
def normalize_test_data(byte_file, current_file, latency_file):
    # Load byte list first to determine test type
    byte_list = hf.load_json(byte_file)
    print("The length of byte_list is:", len(byte_list))  # Verify byte_list is loaded correctly

    test_type = None

    if byte_list == []:  # For upload test
        test_type = "upload"
        current_list = hf.load_json(current_file)
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
        # Load the latency file
        latency_data = hf.load_json(latency_file)
        print("Latency loaded")
        print("Size of latency list:", len(latency_data), "\n")


        # Create a dictionary to map IDs to the first receive time from the latency file
        #latency_time_map = {entry['sourceID']: int(entry['recv_time'][0]) for entry in latency_data} #old way that is too rigid... would crash if a value does not exist
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
def sum_bytecounts_for_timestamps(byte_list, aggregated_time):
    """
    Sum byte counts for timestamps over intervals.

    For every source ID, loop through the entire aggregated time list.
    For every interval of time, loop through every element in that ID's progress list.
    Find the start and end times for each interval, then calculate the proportion of bytes
    to add to each timestamp.

    If there are multiple byte counts added to a particular timestamp, then there are multiple
    flows producing data.

    Args:
        byte_list (list): List of byte transfer entries with progress data
        aggregated_time (list): Sorted list of all unique timestamps

    Returns:
        dict: Dictionary mapping timestamps to tuples of (bytecount, number_of_flows)
    """
    byte_count = {}
    for entry in byte_list: #for each source ID
        end_time = -1
        start_time = -1
        for i in range(len(aggregated_time[1:])): #loop through entire aggregated_time list, setting the window size to be between each event
            current_list_time = aggregated_time[i]
            prev_list_time = aggregated_time[i-1]

            progress = entry['progress']
            for item in progress:
                if (end_time != -1 and start_time!= -1):
                    break

                if ((int(item['time']) > prev_list_time) and start_time==-1):
                    break

                if (int(item['time']) <= prev_list_time):
                    start_time = int(item['time'])

                elif (int(item['time']) >= current_list_time):
                    end_time = int(item['time'])
                if (end_time != -1):
                    proportion = (current_list_time - prev_list_time) / (end_time - start_time)
                    bytes_to_add = int(item['bytecount']) * proportion
                    if current_list_time in byte_count:
                        byte_count[current_list_time][0] += bytes_to_add
                        byte_count[current_list_time][1] += 1

                    else:
                        byte_count[current_list_time] = [bytes_to_add,1]

            start_time = -1
            end_time = -1 #reset start and end time for each event


    return byte_count

#-----------------------------------Throughput Calculation---------------------------------------------
def calculate_traditional_throughput(aggregated_time, byte_count, num_flows, begin_time):
    """
    This is the traditional method that A and A used to calculate throughput.
    By looping through the aggregated timestamps again, they use the the time differences between the two as the time interval.
    This produces various time intervals, mostly 1 or 2 ms. Only calculate the throughput if all flows are contributing at that point.
    """
    throughput_results = []

    for i in range(len(aggregated_time[1:])):
        current_list_time = aggregated_time[i]
        prev_list_time = aggregated_time[i-1]

        if current_list_time in byte_count and byte_count[current_list_time][1] == num_flows:
            # Calculate throughput in bytes/second
            throughput = byte_count[current_list_time][0]/((current_list_time-prev_list_time)/1000)

            throughput_results.append({
                "time": (current_list_time - begin_time)/1000,  # Convert to seconds
                "throughput": throughput*(8/1000000)  # Convert to Mbps
            })

    return throughput_results

def calculate_interval_throughput(aggregated_time, byte_count, num_flows, interval_threshold, begin_time):
    """
    Use a interval threshold to determine the minimum time interval for throughput calculation.
    If a time interval is less than the threshold, combine it with the next interval so that the time interval is greater than or equal to the threshold.
    """
    throughput_results = []
    accumulated_bytes = 0
    accumulated_time = 0
    interval_start = None

    for i in range(len(aggregated_time[1:])):
        current_list_time = aggregated_time[i]
        prev_list_time = aggregated_time[i-1]
        time_diff = current_list_time - prev_list_time

        # Skip if not all flows are contributing (current_list_time should always be in byte_count, unless it is the last timestamp)
        if current_list_time not in byte_count or byte_count[current_list_time][1] != num_flows:
            # Reset accumulation if we skip a point
            accumulated_bytes = 0
            accumulated_time = 0
            interval_start = None
            continue

        # Start new interval if needed
        if interval_start is None:
            interval_start = prev_list_time

        # Add current interval's bytes and time
        accumulated_bytes += byte_count[current_list_time][0]
        accumulated_time += time_diff

        # If we've reached or exceeded the threshold, calculate throughput
        if accumulated_time >= interval_threshold:
            # Calculate throughput for this combined interval
            throughput = (accumulated_bytes/accumulated_time) * 1000  # Convert to bytes/second

            throughput_results.append({
                'time': (interval_start - begin_time)/1000,  # Time since start in seconds
                'throughput': throughput * (8/1000000)  # Convert to Mbps
            })

            # Reset accumulators
            accumulated_bytes = 0
            accumulated_time = 0
            interval_start = None

    return throughput_results

def calculate_throughput_with_less_flows(aggregated_time, byte_count, num_flows, interval_threshold, begin_time):
    """
    Calculate throughput for entries with num_flows and num_flows - 1, keeping them in separate lists.
    Both lists follow the same time interval threshold calculation technique.
    """
    throughput_results = []  # For num_flows
    less_flows_results = []  # For num_flows - 1
    accumulated_bytes = 0
    accumulated_time = 0
    interval_start = None

    for i in range(len(aggregated_time[1:])):
        current_list_time = aggregated_time[i]
        prev_list_time = aggregated_time[i - 1]
        time_diff = current_list_time - prev_list_time

        # Check if num_flows - 1 are contributing
        if current_list_time in byte_count and byte_count[current_list_time][1] == num_flows - 1:
            accumulated_bytes += byte_count[current_list_time][0]
            accumulated_time += time_diff

            if accumulated_time >= interval_threshold:
                throughput = (accumulated_bytes / accumulated_time) * 1000  # Convert to bytes/second
                less_flows_results.append({
                    'time': (prev_list_time - begin_time) / 1000,  # Time since start in seconds
                    'throughput': throughput * (8 / 1000000)  # Convert to Mbps
                })
                accumulated_bytes = 0
                accumulated_time = 0

        # Skip if not all flows are contributing
        if current_list_time not in byte_count or byte_count[current_list_time][1] != num_flows:
            accumulated_bytes = 0
            accumulated_time = 0
            interval_start = None
            continue

        # Start new interval if needed
        if interval_start is None:
            interval_start = prev_list_time

        # Add current interval's bytes and time
        accumulated_bytes += byte_count[current_list_time][0]
        accumulated_time += time_diff

        # If we've reached or exceeded the threshold, calculate throughput
        if accumulated_time >= interval_threshold:
            throughput = (accumulated_bytes / accumulated_time) * 1000  # Convert to bytes/second
            throughput_results.append({
                'time': (interval_start - begin_time) / 1000,  # Time since start in seconds
                'throughput': throughput * (8 / 1000000)  # Convert to Mbps
            })
            accumulated_bytes = 0
            accumulated_time = 0
            interval_start = None

    return throughput_results, less_flows_results

#-----------------------------------Testing Functions------------------------------------------------
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