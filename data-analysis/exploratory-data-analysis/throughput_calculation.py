"""
There are three methods of calculating throughput:
1. Traditional method: A and A's method of calculating throughput, which converts byte_count entries into throughput values.

2. Interval method: This method uses a threshold to determine the minimum time interval used in calculating the throughput. This is the current method of calculating throughput.
If a data point has a time interval less than the threshold, it is combined with the next data point so that the time interval is greater than or equal to the threshold.

3. Less flows method (used for testing only): This method calculates throughput for entries with num_flows and num_flows - 1, keeping them in separate lists.
    Both lists follow the same time interval threshold calculation technique as method #2.
"""


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
    Calculate throughput using interval-based aggregation to avoid burst artifacts.

    This method accumulates bytes and time over intervals until a minimum time threshold
    is reached, then calculates throughput for the combined interval. This approach
    eliminates artificial spikes caused by 0ms time intervals where multiple byte
    transfers occur at the same timestamp.

    The function only calculates throughput when all specified flows are contributing
    to ensure consistent measurements across the timeline.

    Args:
        aggregated_time (list): Sorted list of all unique timestamps from all sources
        byte_count (dict): Dictionary mapping timestamps to tuples of (bytecount, number_of_flows)
        num_flows (int): Expected number of flows that should be contributing
        interval_threshold (int): Minimum time interval in milliseconds for throughput calculation
        begin_time (int): Starting timestamp for normalization to relative time

    Returns:
        list: List of dictionaries containing throughput measurements, each with:
            - 'time': Time since begin_time in seconds (float)
            - 'throughput': Throughput in Mbps (float)
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
