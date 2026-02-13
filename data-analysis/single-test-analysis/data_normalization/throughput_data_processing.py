"""
The functions for preparing the data are:
1) normalize_test_data: Normalize either byte_time_list.json or current_position_list.json, depending on the test

2) aggregate_timestamps_and_find_stream_durations: aggregates the timestamps from all sources and finds the start and end times for each HTTP stream. It also finds the socket that each stream uses if socket_file is available.

3) sum_bytecounts_for_timestamps: Finds the proportion of byte counts for each interval, and how many flows are contributing at each byte count
"""
import utilities
import os

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

        # upload tests record the cumulative byte counts, so convert to incremental byte counts (ex: 16k, 32k and 48k bytes will be reported, but only 16k, 16k, and 16k bytes were actually transferred)
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
        # Load the latency file only if it exists (unloaded latency is optional, but needed to set the start time for the range)
        if os.path.exists(latency_file):
            latency_data = utilities.load_json(latency_file)
            print("Latency loaded")

            # Handle new nested structure or old flat structure
            if 'test_latency' in latency_data and 'streams' in latency_data['test_latency']:
                streams = latency_data['test_latency']['streams']
                print("Size of latency list:", len(streams), "\n")
                latency_time_map = {stream['id']: int(stream['recv_time']) for stream in streams if 'recv_time' in stream and stream['recv_time'] is not None}

            # For every unique source ID, prepend a zero-byte entry with the first receive time
            for entry in byte_list:
                id = entry['id']
                progress = entry['progress']

                if id in latency_time_map and latency_time_map[id] is not None:
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
                'socket': None
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
    Sum byte counts for all unique timestamps across HTTP streams into one list.
    Each element in the resulting list looks like:
    timestamp: [total_bytecount, number_of_flows_contributing]
    """
    byte_count = {}

    for timestamp in aggregated_time: # Initialize all bins
        byte_count[timestamp] = [0, 0]

    for entry in byte_list: # For each HTTP stream:
        source_id = entry['id']
        progress = entry['progress']

        # Some http streams will have duplicate events with the same timestamp - this step will group them together into one event
        stream_bytes = {}
        for item in progress:
            timestamp = int(item['time'])
            bytecount = int(item['bytecount'])

            if timestamp in stream_bytes:
                stream_bytes[timestamp] += bytecount
            else:
                stream_bytes[timestamp] = bytecount

        # Since the stream_bytes is a dictionary, sort the timestamps
        stream_timestamps = sorted(stream_bytes.keys())

        # check if first timestamp has non-zero bytes (missing initial zero-byte event)
        first_timestamp = stream_timestamps[0]
        if stream_bytes[first_timestamp] > 0:
            print(f"Warning: Stream {source_id} - First timestamp ({first_timestamp}) has {stream_bytes[first_timestamp]} bytes.")
            print(f"         These bytes will be dropped. Stream should start with a 0-byte event.")
            # Treat first timestamp as the "zero" baseline - drop its bytes and use it as interval start
            # dropping these bytes should have minimal impact on the overall throughput calculation
            stream_bytes[first_timestamp] = 0

        # After grouping duplicate timestamps together, distribute these bytes across the smaller sub-intervals of the aggregated timestamps
        for i in range(1, len(aggregated_time)):
            #specifiy the smallest interval of the aggregated timestamps
            current_time = aggregated_time[i]
            prev_time = aggregated_time[i-1]

            for j in range(len(stream_timestamps) - 1): #  For each stream interval
                #Look at the current interval of timestamps from the stream - this should be >= the intervals in aggregated_time
                start_time = stream_timestamps[j]
                end_time = stream_timestamps[j+1]

                # Skip if this interval doesn't overlap with our time window
                if end_time <= prev_time or start_time >= current_time:
                    continue

                interval_duration = end_time - start_time #calculate the interval from the HTTP Stream

                # Handle zero-duration intervals (multiple events at same timestamp)
                if interval_duration <= 0:
                    # Zero-duration: attribute bytes directly to end_time without distribution
                    if end_time in byte_count:
                        byte_count[end_time][0] += stream_bytes[end_time]
                        # Increment flow count if this is a new flow starting at this timestamp
                        if j == 0 or (end_time > stream_timestamps[j-1]):
                            byte_count[end_time][1] += 1
                    continue  # Skip proportional distribution for zero-duration intervals

                # Calculate overlap between the http stream interval and the current sub-interval
                overlap_start = max(prev_time, start_time)
                overlap_end = min(current_time, end_time)
                proportion = (overlap_end - overlap_start) / interval_duration

                # Calculate bytes to add to the sub-interval from the aggregated timestamps
                # The bytes at end_time represent data received during [start_time → end_time]
                bytes_to_add = int(stream_bytes[end_time] * proportion)

                # Add bytes to the current timestamp entry
                if current_time in byte_count:
                    byte_count[current_time][0] += bytes_to_add

                    # Increment the flow count at this timestamp
                    if j == 0 or (prev_time > stream_timestamps[j-1]):
                        byte_count[current_time][1] += 1

    print(f"Length of byte_count: {len(byte_count)}")
    return byte_count
