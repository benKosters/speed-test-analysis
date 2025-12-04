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
        #if current_list_time in byte_count:
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

    Returns:
        list: List of dictionaries containing throughput measurements, each with:
            - 'time': Time since begin_time in seconds (float)
            - 'throughput': Throughput in Mbps (float)
    """
    throughput_results = []
    accumulated_bytes = 0
    accumulated_time = 0
    interval_start = None
    byte_counts_with_small_intervals = 0

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
            throughput = (accumulated_bytes/accumulated_time) * 1000  # conversion to bytes/second

            throughput_results.append({
                'time': (interval_start - begin_time)/1000,  # time since start in seconds
                'throughput': throughput * (8/1000000)  # conversion to Mbps
            })

            # Reset accumulators
            accumulated_bytes = 0
            accumulated_time = 0
            interval_start = None

    return throughput_results

def calculate_interval_throughput_tracking_discarded_data(aggregated_time, byte_count, num_flows, interval_threshold, begin_time):
    """
    Calculate throughput using interval-based aggregation to avoid burst artifacts.

    This method accumulates bytes and time over intervals until a minimum time threshold
    is reached, then calculates throughput for the combined interval. This approach
    eliminates artificial spikes caused by 0ms time intervals where multiple byte
    transfers occur at the same timestamp.

    The function only calculates throughput when all specified flows are contributing
    to ensure consistent measurements across the timeline.

    Returns:
        tuple: (throughput_results, discarded_stats)
            - throughput_results: List of dictionaries containing throughput measurements, each with:
                - 'time': Time since begin_time in seconds (float)
                - 'throughput': Throughput in Mbps (float)
            - discarded_stats: Dictionary containing:
                - 'discarded_intervals': Number of accumulated intervals thrown away
                - 'discarded_objects': Number of individual objects (data points) thrown away
                - 'discarded_bytes': Total bytes in discarded data points
                - 'discarded_time': Total time (ms) in discarded intervals
    """
    throughput_results = []
    accumulated_bytes = 0
    accumulated_time = 0
    interval_start = None
    byte_counts_with_small_intervals = 0

    # Track discarded data
    discarded_intervals = 0  # Number of accumulated intervals discarded
    discarded_objects = 0    # Number of individual objects discarded
    discarded_bytes = 0
    discarded_time = 0
    objects_in_current_interval = 0  # Track how many objects are in current accumulated interval

    for i in range(len(aggregated_time[1:])):
        current_list_time = aggregated_time[i]
        prev_list_time = aggregated_time[i-1]
        time_diff = current_list_time - prev_list_time

        # Skip if not all flows are contributing (current_list_time should always be in byte_count, unless it is the last timestamp)
        if current_list_time not in byte_count or byte_count[current_list_time][1] != num_flows:
            # Track discarded data before resetting
            if accumulated_bytes > 0:
                discarded_intervals += 1
                discarded_objects += objects_in_current_interval
                discarded_bytes += accumulated_bytes
                discarded_time += accumulated_time

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

    for i in range(len(aggregated_time[1:])):
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


def calculate_accurate_throughput_with_smooth_plot(aggregated_time, byte_count, num_flows, window_size_ms, begin_time):
    """
    Calculate throughput providing both an accurate single value and smooth plottable data.

    This function addresses the common problem where:
    - Individual 1-2ms intervals are too noisy to plot nicely
    - Fixed threshold methods discard data, reducing accuracy
    - Overall averages hide temporal patterns

    Returns both a single accurate throughput value (using all qualifying data) and
    smoothed data points suitable for plotting (using a sliding window).

    Args:
        aggregated_time: List of timestamps in milliseconds
        byte_count: Dictionary mapping timestamps to (bytes, flow_count) tuples
        num_flows: Required number of flows for data to be included
        window_size_ms: Size of sliding window in milliseconds for smoothing (e.g., 100ms)
        begin_time: Reference start time in milliseconds

    Returns:
        dict containing:
            - 'accurate_throughput': Single float value in Mbps (most accurate)
            - 'plot_data': List of dicts with 'time' and 'throughput' for smooth plotting
            - 'total_bytes': Total bytes where num_flows contributing
            - 'total_time': Total time duration in seconds
            - 'data_points_used': Number of raw data points included
    """
    # Collect all qualifying data points
    qualifying_points = []
    total_bytes = 0
    min_time = float('inf')
    max_time = -1

    for i in range(1, len(aggregated_time)):
        current_list_time = aggregated_time[i]
        prev_list_time = aggregated_time[i-1]

        if current_list_time in byte_count and byte_count[current_list_time][1] == num_flows:
            bytes_val = byte_count[current_list_time][0]
            time_diff = current_list_time - prev_list_time

            qualifying_points.append({
                'time': current_list_time,
                'bytes': bytes_val,
                'interval': time_diff
            })

            total_bytes += bytes_val
            min_time = min(min_time, prev_list_time)
            max_time = max(max_time, current_list_time)

    # Calculate accurate single throughput value
    total_time_ms = max_time - min_time
    total_time_sec = total_time_ms / 1000
    accurate_throughput = (total_bytes / total_time_ms) * 1000 * (8/1000000) if total_time_ms > 0 else 0

    # Create smooth plot data using sliding window
    plot_data = []

    if qualifying_points:
        # Sort by time to ensure proper sliding window
        qualifying_points.sort(key=lambda x: x['time'])

        for i, point in enumerate(qualifying_points):
            window_start = point['time'] - window_size_ms
            window_end = point['time']

            # Accumulate bytes and time within the window
            window_bytes = 0
            window_time = 0

            for p in qualifying_points:
                if window_start <= p['time'] <= window_end:
                    window_bytes += p['bytes']
                    window_time += p['interval']

            # Calculate throughput for this window
            if window_time > 0:
                window_throughput = (window_bytes / window_time) * 1000 * (8/1000000)
                plot_data.append({
                    'time': (point['time'] - begin_time) / 1000,  # seconds
                    'throughput': window_throughput
                })

    return {
        'accurate_throughput': accurate_throughput,
        'plot_data': plot_data,
        'total_bytes': total_bytes,
        'total_time': total_time_sec,
        'data_points_used': len(qualifying_points)
    }

def calculate_throughput_weighted_points(aggregated_time, byte_count, num_flows, begin_time):
    """
    Calculate throughput points weighted by their time interval durations.

    This method addresses the bias in traditional throughput calculations where all
    points are given equal weight regardless of their time duration. By weighting
    each throughput point by its time interval, the mean of the returned values
    will be mathematically equivalent to (total_bytes / total_time) but only for
    periods where all flows are contributing.

    The key insight: when calculating mean throughput, points representing longer
    time intervals should have more influence than points representing shorter
    intervals. This is achieved by including a 'weight' field that represents
    the time duration as a fraction of the total time.

    Args:
        aggregated_time: List of timestamps in milliseconds
        byte_count: Dictionary mapping timestamp -> (bytes, num_contributing_flows)
        num_flows: Maximum number of flows to filter for (only use points with this many flows)
        begin_time: Start time in milliseconds for normalizing timestamps

    Returns:
        dict: Contains:
            - 'weighted_points': List of dicts with 'time', 'throughput', 'weight', 'interval_ms'
            - 'overall_throughput': Single value equivalent to sum(bytes)/sum(time) for all flows
            - 'total_bytes': Total bytes when all flows contributing
            - 'total_time': Total time (seconds) when all flows contributing
            - 'num_points': Number of data points used

    Usage:
        To get the correct mean throughput:
        weighted_mean = sum(point['throughput'] * point['weight'] for point in result['weighted_points'])

        This weighted_mean will equal result['overall_throughput']
    """
    weighted_points = []
    total_bytes = 0
    total_time_ms = 0

    # First pass: collect all qualifying points and calculate totals
    for i in range(1, len(aggregated_time)):
        current_list_time = aggregated_time[i]
        prev_list_time = aggregated_time[i-1]

        # Only consider points where all flows are contributing
        if current_list_time in byte_count and byte_count[current_list_time][1] == num_flows:
            bytes_val = byte_count[current_list_time][0]
            time_diff = current_list_time - prev_list_time

            # Calculate instantaneous throughput for this interval
            throughput_mbps = (bytes_val / time_diff) * 1000 * (8/1000000) if time_diff > 0 else 0

            weighted_points.append({
                'time': (current_list_time - begin_time) / 1000,  # seconds since start
                'throughput': throughput_mbps,
                'interval_ms': time_diff,
                'bytes': bytes_val
            })

            total_bytes += bytes_val
            total_time_ms += time_diff

    # Second pass: assign weights as fraction of total time
    total_time_sec = total_time_ms / 1000
    for point in weighted_points:
        point['weight'] = point['interval_ms'] / total_time_ms if total_time_ms > 0 else 0

    # Calculate overall throughput (equivalent to weighted mean)
    overall_throughput = (total_bytes / total_time_ms) * 1000 * (8/1000000) if total_time_ms > 0 else 0

    return {
        'weighted_points': weighted_points,
        'overall_throughput': overall_throughput,
        'total_bytes': total_bytes,
        'total_time': total_time_sec,
        'num_points': len(weighted_points)
    }