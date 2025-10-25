import json
import os
import sys
"""
Counts the total bytes transferred by each http stream ID.
Takes a list of stream data and returns a dictionary mapping stream IDs to their total byte counts.
"""
def sum_byte_counts(byte_list):
    id_sums = {}

    if not byte_list or not isinstance(byte_list, list):
        print("Warning: Empty or invalid byte_list provided")
        return id_sums

    try:
        for item in byte_list:
            id_num = item['id']
            byte_sum = 0

            # Check if this is byte_time_list format (has 'bytecount')
            if 'progress' in item and any('bytecount' in p for p in item['progress'] if p):
              # Sum the bytecount values
                for progress in item['progress']:
                    if 'bytecount' in progress:
                        byte_sum += progress['bytecount']

            # Check if this is current_position_list format (has 'current_position')
            elif 'progress' in item and any('current_position' in p for p in item['progress'] if p):
                max_position = 0
                # Get the maximum current_position value
                for progress in item['progress']:
                    if 'current_position' in progress:
                        max_position = max(max_position, progress['current_position'])
                byte_sum = max_position

            id_sums[id_num] = byte_sum

        return id_sums

    except Exception as e:
        print(f"Error processing byte_list: {str(e)}")
        return {}

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

def capture_http_stream_statistics(byte_list, source_times, print_output):
    """
    Capture information about each HTTP stream, save it in JSON format
    """

    http_stream_data = []
    socket_to_streams = {}
    byte_counts_sums = {}

    #Sum byte counts by http stream
    if byte_list and isinstance(byte_list, list):
        id_byte_sums = sum_byte_counts(byte_list)
        if print_output:
            print(f"Loaded byte counts for {len(id_byte_sums)} streams")

    if print_output:
        print("\nHTTP Stream Information:")
        print("-" * 80)
    for stream_id, info in source_times.items():
        socket = info['socket']
        start_time = info['times'][0]
        end_time = info['times'][1]
        stream_duration = end_time - start_time
        bytes_transferred = id_byte_sums.get(stream_id, 0)

        stream_throughput_mbps = 0
        if bytes_transferred > 0 and stream_duration > 0:
            stream_throughput_mbps = (bytes_transferred * 8) / (stream_duration / 1000) / 1000000 #convert bytes per ms to megabits per second

        #map stream IDs to their sockets
        if socket is not None:
            if socket not in socket_to_streams:
                socket_to_streams[socket] = []
            socket_to_streams[socket].append((stream_id, start_time, end_time))

        if print_output:
            print(f"Stream ID {stream_id}: Start={start_time}, End={end_time}, Duration={stream_duration}ms, Socket = {socket}")

        stream_entry = {
            "stream_id": stream_id,
            "socket": socket,
            "start_time": start_time,
            "end_time": end_time,
            "stream_duration": stream_duration,
            "bytes_transferred": bytes_transferred,
            "stream_throughput_mbps": stream_throughput_mbps
        }
        http_stream_data.append(stream_entry)

    return http_stream_data, socket_to_streams

def capture_socket_statistics(socket_to_streams, print_output):
    socket_data = []
    # Collect data about the sockets
    for socket, sources in socket_to_streams.items():
        # Sort http streams by their start time
        sources.sort(key=lambda x: x[1])

        #create an entry for a socket
        socket_entry = {
            "socket_id": socket,
            "stream_count": len(sources),
            "stream_ids": [source[0] for source in sources],
            "time_differences": []
        }

        for i in range(1, len(sources)):
            prev_stream_id, _, prev_end_time = sources[i - 1]
            curr_stream_id, curr_start_time, _ = sources[i]
            time_diff = curr_start_time - prev_end_time

            if print_output:
                print(f" \nSocket {socket}: Source {prev_stream_id} ends at {prev_end_time}, "
                    f"Source {curr_stream_id} starts at {curr_start_time}, "
                    f"Time Difference: {time_diff}ms")

            time_diff_entry = {
            "first_stream": {
                "id": prev_stream_id,
                "end_time": prev_end_time
            },
            "second_stream": {
                "id": curr_stream_id,
                "start_time": curr_start_time
            },
            "time_difference_ms": time_diff
            }

            socket_entry["time_differences"].append(time_diff_entry)

        socket_data.append(socket_entry)
    return socket_data

def save_socket_stream_data(byte_list, source_times, outputDir, print_output = False):
    """
    Save summary statistics on http streams and sockets for easier comparison across different tests
    """

    http_stream_data_structure = {
        "http_stream_data": [],
        "socket_data": [],
        "stream_statistics": [],
        "socket_statistics": []
    }
    #Capture statistic
    http_stream_data, socket_to_streams = capture_http_stream_statistics(byte_list, source_times, print_output)
    http_stream_data_structure["http_stream_data"] = http_stream_data

    socket_data = capture_socket_statistics(socket_to_streams, print_output)
    http_stream_data_structure["socket_data"] = socket_data

    #collect socket statistics here:
    all_time_differences = []
    for socket_entry in http_stream_data_structure["socket_data"]:
        for time_diff_entry in socket_entry["time_differences"]:
            all_time_differences.append(time_diff_entry["time_difference_ms"])

    # Calculate the socket statistics only if we have time differences
    if all_time_differences:
        # Sort the time differences for calculating median and other statistics
        all_time_differences.sort()

        # Calculate mean
        mean_latency = sum(all_time_differences) / len(all_time_differences)

        # Calculate median
        mid = len(all_time_differences) // 2
        median_latency = all_time_differences[mid] if len(all_time_differences) % 2 != 0 else (all_time_differences[mid-1] + all_time_differences[mid]) / 2

        # Calculate min, max, and range
        min_latency = all_time_differences[0]
        max_latency = all_time_differences[-1]
        range_latency = max_latency - min_latency

        # Create socket_statistics object
        socket_statistics = {
            "total_streams": len(http_stream_data_structure["http_stream_data"]),
            "total_sockets": len(http_stream_data_structure["socket_data"]),
            "mean_latency_between_streams_ms": mean_latency,
            "median_latency_between_streams_ms": median_latency,
            "min_latency_between_streams_ms": min_latency,
            "max_latency_between_streams_ms": max_latency,
            "range_latency_between_streams_ms": range_latency
        }

        # Add to the data structure
        http_stream_data_structure["socket_statistics"] = socket_statistics

    #if the file http_stream_data.json doesnt exist, create it
    output_file = os.path.join(outputDir, "http_stream_data.json")
    try:
        with open(output_file, 'w') as file:
            json.dump(http_stream_data_structure, file, indent=2)
        if print_output:
            print(f"\nSuccessfully saved HTTP stream data to {output_file}")
    except Exception as e:
        print(f"Error saving HTTP stream data to {output_file}: {e}")

    return http_stream_data_structure

def calculate_percent_of_all_flows_contributing(byte_count, max_flows):
    """
    Analyzes byte_count events to determine how many flows contribute to each event.

    Args:
        byte_count (dict): Dictionary where keys are timestamps and values are [bytecount, num_flows]
        max_flows (int): The maximum number of flows in the test

    Returns:
        tuple: (flow_counts_dict, max_flow_percentage)
    """
    # Dictionary to track counts for each flow number
    flow_counts = {f"flow_{i}": 0 for i in range(1, max_flows + 1)}

    # Count events by number of contributing flows
    total_events = 0
    for timestamp, value in byte_count.items():
        num_flows = value[1]  # Second element is the number of flows
        if 1 <= num_flows <= max_flows:
            flow_counts[f"flow_{num_flows}"] += 1
            total_events += 1

    # Format for nicer printing
    formatted_counts = []
    for flow_num in range(1, max_flows + 1):
        key = f"flow_{flow_num}"
        formatted_counts.append([key, flow_counts[key]])

    # Calculate percentage where max flows contributed
    max_flow_count = flow_counts[f"flow_{max_flows}"]
    max_flow_percentage = (max_flow_count / total_events * 100) if total_events > 0 else 0

    print("Count of byte_count events grouped by number of flows contributing to each point:")
    print(formatted_counts)

    print(f"Percent of test where max flows contributed: {max_flow_percentage:.2f}%")

    return formatted_counts, max_flow_percentage


def calculate_bytes_lost_by_calculating_throughput(throughput_results, byte_list):
    pass
