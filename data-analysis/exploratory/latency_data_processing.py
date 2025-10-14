def extract_latencies(latency_list):
    """
    Extract latency values from latency data structure.

    Args:
        latency_list (list): List of latency entries with send_time and recv_time

    Returns:
        list: List of latency values in milliseconds
    """
    latencies = []
    for entry in latency_list:
        # If you have both send_time and recv_time:
        if 'send_time' in entry and 'recv_time' in entry and entry['recv_time']:
            if isinstance(entry['send_time'], list) and isinstance(entry['recv_time'], list):
                # Handle array format
                if len(entry['send_time']) > 0 and len(entry['recv_time']) > 0:
                    latency_us = int(entry['recv_time'][0]) - int(entry['send_time'][0])
                    latencies.append(latency_us / 1000)  # Convert to milliseconds
            else:
                # Handle single value format
                latency_us = entry['recv_time'] - entry['send_time']
                latencies.append(latency_us / 1000)  # Convert to milliseconds
        # If you only have recv_time (already normalized):
        elif 'recv_time' in entry and entry['recv_time']:
            if isinstance(entry['recv_time'], list):
                latencies.append(entry['recv_time'][0])
            else:
                latencies.append(entry['recv_time'])
    return latencies