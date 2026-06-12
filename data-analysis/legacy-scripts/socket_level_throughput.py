"""
To run this program: python3 throughput_with_plot.py <directory containing the upload or download results>

If the test is a download test, the byte_time_list and latency files are used.
If the test is an upload test, the current_position_list and latency files are used.

This script was last used in the fall of 2025 and has not been used since then. It may need to be updated.

"""
import json


import argparse
import os
import sys
import pandas as pd
from collections import defaultdict
from matplotlib import pyplot as plt
import numpy as np

#importing functions from other files to keep this one clean
import helper_functions as hf
import throughput_calculation_functions as tp
import plotting_functions as plot


# Function to load JSON files from a given filepath
def load_json(filepath):
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
    with open(filepath, 'r') as f:
        return json.load(f)

# Set up argument parsing to allow a base path as input
parser = argparse.ArgumentParser(description='Process byte time and latency JSON files.')
parser.add_argument('base_path', type=str, help='Base path to the JSON files')



args = parser.parse_args()
# Ensure only one argument is provided
if len(sys.argv) != 2:  # sys.argv[0] is the script name, so we check if there are extra args
    parser.error(f"The incorrect number of arguments provided. Expected 1 argument, but got {len(sys.argv) - 1}.")

# Print base path and working directory for debugging
print(f"Provided Base Path: {args.base_path}")
print(f"Current Working Directory: {os.getcwd()}")

# Construct the full file paths by appending the specific filenames
#byte_file = os.path.abspath(os.path.join(args.base_path, "byte_time_list.json"))

#For testing: Read in the byte_time_list file that was generated at the socket level
byte_file = os.path.abspath(os.path.join(args.base_path, "socket_byte_time_list.json")) #testing with socket level only
current_file = os.path.abspath(os.path.join(args.base_path, "current_position_list.json"))
latency_file = os.path.abspath(os.path.join(args.base_path, "latency.json"))
loaded_latency_file = os.path.abspath(os.path.join(args.base_path, "normalized_latency.json"))


# Debugging: Print the constructed paths
print()
print(f"Byte Time File: {byte_file}")
print(f"Current Position File: {current_file}")
print(f"Latency File: {latency_file}")
print()
# Check and load files
for file_path in [byte_file, current_file, latency_file, loaded_latency_file]:
    print(f"Checking: {file_path}")
    if not os.path.exists(file_path):
        print(f"ERROR: File not found - {file_path}\n")
    else:
        print(f"File exists: {file_path}\n")
print()

# loaded_latency = load_json(loaded_latency_file)
# print(loaded_latency)

"""
Load the JSON files
byte_list is autofilled from the byte_time_list file created by the download test but must be manually filled if an upload test is selected
byte_list is then used to calculated throughput.
An example entry in byte_list looks like:
{'id': 5781,
'type': 'upload',
'progress': [
 {'bytecount': 0, 'time': '53483952'},
 {'bytecount': 10000, 'time': '53483952'}
 ]
}


If the test is upload, use the current_position_list to access bytecount data. An example entry in current_postition_list looks like this:
{
    "id": 5781,
    "type": "upload",
    "progress": [
      {
        "current_position": 0,
        "time": "53483952"
      },
      {
        "current_position": 10000,
        "time": "53483952"
      }
    ]
  },
"""
#-----------------Step 1: Normalize Data-------------------------
byte_list = load_json(byte_file)

print("the length of byte_list is:", len(byte_list)) #to verfiy that the byte_list is being loaded correctly

if byte_list == []: #for upload:
    current_list = load_json(current_file)


    # Transform cumulative data into incremental byte data
    # This loop runs through the current position list, calculating 1) the bytes transfered between entries
    byte_list = []
    for item in current_list:
        new_progress = []
        prev_position = 0  # Initialize the previous position

        for progress in item["progress"]:

            current_position = progress["current_position"]
            time = progress["time"]

            bytes_transferred = current_position - prev_position # the difference between the two positions is the number of bytes transfered
            prev_position = current_position  # Update previous position(move the window)

            # Add the incremental data to the new progress list
            new_progress.append({"bytecount": bytes_transferred, "time": time})

        # Append the transformed item to the uncumulated list
        byte_list.append({
            "id": item["id"],
            "type": item["type"],
            "progress": new_progress
        })
        #print(byte_list[len(byte_list)- 1])

else: #for download:
    # Load the latency file -even though this is only for
    latency_data = load_json(latency_file)
    print("latency loaded")
    print("size of latency list:", len(latency_data),"\n")

    # Create a dictionary to map IDs to the first time from the latency file (the first receive time associated with that id)
    #Example: {<id>: first_recv_time} --> the recv_time is the START of the throughput calculation time

    #COMMENTED OUT FOR SOCKET LEVEL THROUGHPUT
    #latency_time_map = {entry['sourceID']: int(entry['recv_time'][0]) for entry in latency_data}
   # print("Unique source IDs:",len(latency_time_map))
    # print(latency_time_map)

    # Step 1: Aggregate unique time into one list
    #In order to accurately calculate throughput, we need the READ_RESPONSE_HEADERS timestamp, which was saved as recv_time.
    # For every unique source ID, create an object that can be prepended to the byte_list list - this way, all required timestamps are in the list
#     for entry in byte_list:
#         id = entry['id']
#         progress = entry['progress']
#         # If the ID exists in the latency map, prepend the 0th time entry
#         if id in latency_time_map:
#             zero_time_entry = {
#                 "bytecount": 0,  # Bytecount at recv_time is 0, because no bytes have been received yet
#                 "time": latency_time_map[id]
#             }
#             progress.insert(0, zero_time_entry)  # Prepend to the progress list
#     #byte_list now contains the prepended recv_time(the beginning of throughput time)
# print("Length of byte_list:", len(byte_list))
#----------------------Step 2: Aggregating timestamps----------------------------------------------
"""
The aggregated list contains the unique timestamps of every bytecount entry for all source IDs.
To calculated
If there are multiple flows, there will be entries with overlapping timestamps.
"""
aggregated_time = []
source_times = {}
test_type = None  #Will store the type of test (upload or download) for later use
for entry in byte_list: #for every source ID...
    progress = entry['progress']
    source_id = entry['id']
    if test_type is None:
        test_type = entry['type']
        # Initialize start and end times for this source
    # Initialize timing information
    if progress:
        source_times[source_id] = {
            'times': [int(progress[0]['time']), int(progress[-1]['time'])],
            'socket': None  # Will be populated later for upload flows
        }

    # Add timestamps to aggregated_time
    for item in progress:
        if int(item['time']) not in aggregated_time:
            aggregated_time.append(int(item['time']))
#find the socket ID that the source is using
if test_type == 'upload'or test_type == 'download':
    socket_file = os.path.join(os.path.dirname(args.base_path), 'socketIds.txt')
    if os.path.exists(socket_file):
        with open(socket_file, 'r') as f:
            for line in f:
                source_id, _, socket_id = map(int, line.strip().split(','))
                if source_id in source_times:
                    source_times[source_id]['socket'] = socket_id

aggregated_time.sort() #sort the timestamps for bytecounts for ALL sources
byte_count = {}
begin_time = aggregated_time[0] #beginning of time interval(recv_time for download)
print("number of aggregated timestamps:", len(aggregated_time))

hf.analyze_source_sockets_and_timing(source_times)

#--------------------------------Step 3: Summing bytecounts for timestamps------------------------
"""
Find bytecounts that have the same timestamp over an interval, and add their proportion of bytes to the timestamp.
For every source ID, loopthrough the entire aggregated time list.
For every interval of time, loop through every element in that IDs progress list.
If the timestamp of the bytecount is equal to the start of the interval, set it as the start time.
If the timestamp of the bytecount is equal to the end of the interval, set it as the end time.

If there are multiple byte counts added to a particular timestamp, then there are multiple flows producing data.
"""
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
                if current_list_time in byte_count:
                    byte_count[current_list_time][0] += int(item['bytecount']) * ((current_list_time - prev_list_time) / (end_time - start_time))
                    byte_count[current_list_time][1] += 1

                else:
                    byte_count[current_list_time] = [int(item['bytecount']) * ((current_list_time - prev_list_time) / (end_time - start_time)),1]

        start_time = -1
        end_time = -1 #reset start and end time for each event

# hf.print_byte_count_entries(byte_count, 100)

#----------------------testing-write the contents of byte_count to a file------------------------------------
output_file_path = os.path.join(os.path.dirname(__file__), "byte_count_entries.json")
# Create a new list with timestamps converted to seconds
# Get the first timestamp to calculate relative time
first_timestamp = min(byte_count.keys())

# Create a new dictionary with timestamps converted to seconds
byte_count_seconds = {}
for timestamp, (bytes_count, flows) in byte_count.items():
    relative_time = (timestamp - first_timestamp) / 1000  # Convert to seconds
    byte_count_seconds[f"{relative_time:.3f}"] = {
        "bytes": bytes_count,
        "flows": flows
    }

# Write the modified byte_count to a file
with open(output_file_path, 'w') as output_file:
    json.dump(byte_count_seconds, output_file, indent=4)  # Write the JSON data with indentation for readability

print(f"byte_count with timestamps in seconds has been written to {output_file_path}")
#----------------------testing--------------------------------------------------------------------------------

# ----------------------------------Step 4: Throughput Calculation---------------------------------------------
throughput_results = []
num_flows = max(byte_count[timestamp][1] for timestamp in byte_count) #find the max number of flows - there should never be MORE than the defined number of flows contributing to a bytecount

throughput_results = tp.calculate_interval_throughput(aggregated_time, byte_count, num_flows, 2, begin_time)

#throughput_results = calculate_traditional_throughput(aggregated_time, byte_count, num_flows, begin_time)

print("Length of throughput results:", len(throughput_results))
hf.analyze_missing_timestamps(aggregated_time, byte_count)

mean_throughput = hf.calculate_mean_throughput(throughput_results)
print(f"\nMean throughput: {mean_throughput:.2f} Mbps")

#print out the number of flows contributing to a byte count, and the frequency that they occur.
hf.calculate_occurrence_sums(byte_count)

#print out the number of data points that were produced, and the time interval they had.
#hf.analyze_throughput_intervals(throughput_results)

# Add after calculating throughput_results:
#hf.analyze_high_throughput(throughput_results)

#--------------------testing-----------------------------------------------------------------
# Normalize the timestamps in current_position_list
#normalized_output_path = os.path.join(os.path.dirname(__file__), "normalized_current_position_list.json")
#normalized_current_list = hf.normalize_current_position_list(current_position_list=current_list,begin_time=begin_time, output_file_path=normalized_output_path)

#----------------------------------end of testing--------------------------------------------

#---------------------------------------------Throughput Plotting-------------------------------------------------
df = pd.DataFrame(throughput_results) # df for throughput
#less_flows_df = pd.DataFrame(less_flows_results) # df for
print("Number of data points:", len(df))

#various functions used for ploting the data in different ways

#plot.plot_interval_of_test(df, 3.3, 4.1)
#plot.plot_throughput_with_sockets_shown(df)
#plot.traditional_rema_throughput_plot(df, title=args.base_path.split('/')[-1])

#plot.plot_throughput_different_flows(df, less_flows_df, start_time=0, end_time=15, source_times=source_times, begin_time=begin_time)
#plot.plot_throughput_with_sockets_shown(df, title=args.base_path.split('/')[-1], source_times=source_times, begin_time=begin_time)
#plot.plot_throughput_scatter_full_flows(df,start_time=0, end_time=15, source_times=source_times, begin_time=begin_time)
#plot.plot_throughput_different_flows(df, less_flows_df, start_time=0, end_time=15, source_times=source_times, begin_time=begin_time)
#plot.plot_throughput_with_sockets_shown_and_latency(df, title=args.base_path.split('/')[-1], source_times=source_times, begin_time=begin_time, latency_file=loaded_latency_file)


plot.plot_throughput_with_sockets_shown(df, title=args.base_path.split('/')[-1], source_times=source_times, begin_time=begin_time)

#plot.plot_rema_per_source(normalized_current_list)

