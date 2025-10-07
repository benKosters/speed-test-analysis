import json


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
