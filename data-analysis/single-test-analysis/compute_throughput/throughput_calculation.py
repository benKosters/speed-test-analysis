"""
This file contains the methods for computing throughput.

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
    TODO: Delete this function, we have not used it since September 2025
    """
    throughput_results = []

    for i in range(1, len(aggregated_time)):
        current_list_time = aggregated_time[i]
        prev_list_time = aggregated_time[i-1]

        if current_list_time in byte_count and byte_count[current_list_time][1] == num_flows:
        #if current_list_time in byte_count:
            # Calculate throughput in bytes/second
            throughput = byte_count[current_list_time][0]/((current_list_time-prev_list_time)/1000)

            throughput_results.append({
                "time": (current_list_time - begin_time)/1000,  # Convert to seconds
                "throughput": throughput*(8/1000000)  # Convert to Mbps
            })

    return throughput_results

def calculate_interval_threshold_throughput(aggregated_time, byte_count, num_flows, interval_threshold, begin_time, all_data = False):

    throughput_results = []
    accumulated_bytes = 0
    accumulated_time = 0
    interval_start = None

    discarded_intervals = 0  # Number of accumulated intervals discarded
    discarded_objects = 0    # Number of individual objects discarded
    discarded_bytes = 0
    discarded_time = 0
    objects_in_current_interval = 0  # Track how many objects are in current accumulated interval

    for i in range(1, len(aggregated_time)):
        current_list_time = aggregated_time[i]
        prev_list_time = aggregated_time[i-1]
        time_diff = current_list_time - prev_list_time

        # Skip if not all flows are contributing (current_list_time should always be in byte_count, unless it is the last timestamp)
        if all_data: # If all data is selected, only skip if there are 0 flows
            data_accumulation_reset = current_list_time not in byte_count or byte_count[current_list_time][1] <= 0
        else:
            data_accumulation_reset = current_list_time not in byte_count or byte_count[current_list_time][1] != num_flows
        if data_accumulation_reset:
            # Track discarded data before resetting
            if accumulated_bytes > 0:
                discarded_intervals += 1
                discarded_objects += objects_in_current_interval
                discarded_bytes += accumulated_bytes
                discarded_time += accumulated_time

            # Also discard bytes from current invalid interval if it exists in byte_count
            if current_list_time in byte_count:
                discarded_objects += 1
                discarded_bytes += byte_count[current_list_time][0]
                discarded_time += time_diff

            # Reset accumulation if we skip a point
            accumulated_bytes = 0
            accumulated_time = 0
            interval_start = None
            objects_in_current_interval = 0
            continue

        # Start new interval if needed
        if interval_start is None:
            interval_start = prev_list_time

        # Add current interval's bytes and time
        accumulated_bytes += byte_count[current_list_time][0]
        accumulated_time += time_diff
        objects_in_current_interval += 1

        # If we've reached or exceeded the threshold, calculate throughput
        if accumulated_time >= interval_threshold:
            # Calculate throughput for this combined interval
            throughput = (accumulated_bytes/accumulated_time) * 1000  # conversion to bytes/second

            throughput_results.append({
                'time': (interval_start - begin_time)/1000,  # time since start in seconds
                'throughput': throughput * (8/1000000)  # conversion to Mbps
            })

            # Reset accumulators
            accumulated_bytes = 0
            accumulated_time = 0
            interval_start = None
            objects_in_current_interval = 0

    # Check if there's any remaining accumulated data at the end that didn't meet threshold
    if accumulated_bytes > 0:
        discarded_intervals += 1
        discarded_objects += objects_in_current_interval
        discarded_bytes += accumulated_bytes
        discarded_time += accumulated_time

    discarded_stats = {
        'discarded_intervals': discarded_intervals,
        'discarded_objects': discarded_objects,
        'discarded_bytes': discarded_bytes,
        'discarded_time': discarded_time
    }

    return throughput_results, discarded_stats

#March 28, 2026
def calculate_throughput_strict_intervals(aggregated_time, byte_count, num_flows, sampling_period, begin_time, all_data=False):
    throughput_results = []
    accumulated_bytes = 0
    accumulated_time = 0
    current_interval_start = None  # start time of current sampling period (this is a timestamp)

    # Track discarded data
    discarded_intervals = 0  # Number of incomplete intervals discarded
    discarded_bytes = 0  # Total bytes discarded
    discarded_time = 0  # Total time (ms) discarded
    discarded_objects = 0  # Number of whole byte_count events discarded
    objects_in_current_accumulation = 0  # Track objects in current incomplete interval

    for i in range(1, len(aggregated_time)):
        current_list_time = aggregated_time[i]
        prev_list_time = aggregated_time[i-1]
        time_diff = current_list_time - prev_list_time

        # Determine if this particular byte_count event should be used
        if all_data:
            # Use all data where at least one flow is contributing
            valid_data = current_list_time in byte_count and byte_count[current_list_time][1] > 0
        else:
            # Only use data where all flows are contributing
            valid_data = current_list_time in byte_count and byte_count[current_list_time][1] == num_flows

        # If this interval isn't valid (0 flows, or isn't max flow), discard it and move to the next byte_count interval
        if not valid_data:
            # Discard any accumulated bytes from previous valid intervals
            if accumulated_bytes > 0:
                discarded_intervals += 1
                discarded_bytes += accumulated_bytes
                discarded_time += accumulated_time
                discarded_objects += objects_in_current_accumulation

            # Also discard bytes from current invalid interval if it exists in byte_count
            if current_list_time in byte_count:
                discarded_objects += 1  # Count this whole invalid event
                discarded_bytes += byte_count[current_list_time][0]
                discarded_time += time_diff

            # Reset accumulators
            accumulated_bytes = 0
            accumulated_time = 0
            current_interval_start = None
            objects_in_current_accumulation = 0
            continue

        # For valid byte_count bins, get bytes
        interval_bytes = byte_count[current_list_time][0]

        # Start a new interval if one doesn't already exist
        if current_interval_start is None:
            current_interval_start = prev_list_time

        # Add incoming data to accumulators (there may be bytes/time from the previous interval)
        accumulated_bytes += interval_bytes
        accumulated_time += time_diff
        objects_in_current_accumulation += 1

        # While the accumulated time is greater than or equal to the sampling period,
        # calculate throughput for each sampling period using proportional byte distribution
        while accumulated_time >= sampling_period:
            # Calculate proportion of accumulated data that fits in this sampling period
            proportion = sampling_period / accumulated_time
            bytes_for_period = accumulated_bytes * proportion

            throughput_results.append({
                'time': (current_interval_start - begin_time) / 1000,  # Convert to seconds
                'throughput': (bytes_for_period / sampling_period) * 1000 * (8/1000000)  # Convert to Mbps
            })

            # Subtract what we just used from accumulators
            accumulated_bytes -= bytes_for_period
            accumulated_time -= sampling_period
            current_interval_start += sampling_period

            # Note: We don't reset objects_in_current_accumulation here because the same objects
            # may contribute to multiple sampling periods. We only reset when we encounter
            # invalid data or finish processing.

    # At the very end of byte_count, if there is any remaining data that didn't
    # complete a full sampling period, add it to the discard pile
    if accumulated_bytes > 0:
        discarded_intervals += 1
        discarded_bytes += accumulated_bytes
        discarded_time += accumulated_time
        discarded_objects += objects_in_current_accumulation

    discarded_stats = {
        'discarded_intervals': discarded_intervals,
        'discarded_bytes': discarded_bytes,
        'discarded_time': discarded_time,
        'discarded_objects': discarded_objects
    }

    return throughput_results, discarded_stats



# NOT USED - can delete
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

    for i in range(1, len(aggregated_time)):
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

def calculate_throughput_separate_flows(aggregated_time, byte_count, num_flows, begin_time):
    """
    Calculate throughput by aggregating bytes and time continuously until the flow count changes.

    Unlike calculate_interval_throughput which uses a fixed time threshold, this function
    accumulates data for as long as the specified number of flows are contributing. When
    the flow count drops below num_flows, it calculates throughput for the accumulated
    interval and resets.

    This approach creates variable-length intervals based on flow stability rather than
    time thresholds, which can be useful for analyzing throughput during stable periods
    of consistent flow counts.
    """

    throughput_results = []
    accumulated_bytes = 0
    accumulated_time = 0
    interval_start = None

    for i in range(1, len(aggregated_time)):
        current_list_time = aggregated_time[i]
        prev_list_time = aggregated_time[i-1]
        time_diff = current_list_time - prev_list_time

        # Check if this point has the required number of flows
        if current_list_time in byte_count and byte_count[current_list_time][1] == num_flows:
            # Start new interval if needed
            if interval_start is None:
                interval_start = prev_list_time

            # Add current interval's bytes and time
            accumulated_bytes += byte_count[current_list_time][0]
            accumulated_time += time_diff
        else:
            # Flow count changed or point not in byte_count - calculate throughput if we have accumulated data
            if accumulated_bytes > 0 and accumulated_time > 0:
                # Calculate throughput for this accumulated interval
                throughput = (accumulated_bytes/accumulated_time) * 1000  # conversion to bytes/second

                throughput_results.append({
                    'time': (interval_start - begin_time)/1000,  # time since start in seconds
                    'throughput': throughput * (8/1000000),  # conversion to Mbps
                    'duration': accumulated_time / 1000  # duration in seconds
                })

            # Reset accumulators
            accumulated_bytes = 0
            accumulated_time = 0
            interval_start = None

    # Calculate throughput for any remaining accumulated data at the end
    if accumulated_bytes > 0 and accumulated_time > 0:
        throughput = (accumulated_bytes/accumulated_time) * 1000  # conversion to bytes/second

        throughput_results.append({
            'time': (interval_start - begin_time)/1000,  # time since start in seconds
            'throughput': throughput * (8/1000000),  # conversion to Mbps
            'duration': accumulated_time / 1000  # duration in seconds
        })

    return throughput_results
