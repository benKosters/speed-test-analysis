"""
The processing of byte counts at the socket level (layer 4 in the TCP/IP model) is very similar to processing at layer 5.
However, it is easer to keep this code separate to avoid compatability issues.

To run on download tests: python3 socket_eda_driver.py <path/to/test_dir/download>
To run on upload tests:   python3 socket_eda_driver.py <path/to/test_dir/upload>
"""

import json
import argparse
import os
import sys
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
#Custom imports
import throughput_data_processing as tp_proc

import socket_plots
import data_processing_validation as validate
import throughput_calculation as tp_calc
import summary_statistics as ss
import utilities

parser = argparse.ArgumentParser(description="Process socket-level byte count data from Ookla Speedtest netlog files.")
parser.add_argument("input_dir", help="Directory containing the socket-level byte count JSON files.")

args = parser.parse_args()

# These are the file paths
socket_ids_file = os.path.join(args.input_dir, "socketIds.json")
preprocessed_socket_bytecount_file = os.path.join(args.input_dir, "socket_byte_time_list.json")
http_byte_time_list_file = os.path.join(args.input_dir, "byte_time_list.json")

#this is the JSON object itself
socket_bytecount = utilities.load_json(preprocessed_socket_bytecount_file)


# ----------------------Aggregate timestamps across all sockets----------------------------------------------
aggregated_time, begin_and_end_times, begin_time = tp_proc.aggregate_timestamps_and_find_stream_durations(socket_bytecount, socket_ids_file)
print()
#We should get anywhere between 1 and 6 sockets
for socket_id, data in begin_and_end_times.items():
    print(f"Socket ID: {socket_id}, {data['times'][0]} to {data['times'][-1]}")


#--------------------------Sum bytecounts across all sockets-------------------------------------------------
#similar to layer 5 EDA driver, compress all socket bytecounts into a single list
processed_socket_bytecount_file = os.path.join(args.input_dir, "processed_socket_byte_time_list.json")
if os.path.exists(processed_socket_bytecount_file):
    print(f"Loading byte_count data: {processed_socket_bytecount_file}")
    # Load the byte_count data and convert string keys back to integers
    byte_count_raw = utilities.load_json(processed_socket_bytecount_file)
    # Convert the dictionary keys from strings back to integers
    processed_socket_bytecount = {int(timestamp): value for timestamp, value in byte_count_raw.items()}
    print(f"Converted {len(processed_socket_bytecount)} timestamp keys from strings to integers")
else:
    print(f"Calculating and saving byte_count data: {processed_socket_bytecount_file}")
    processed_socket_bytecount = tp_proc.sum_all_bytecounts_across_http_streams(socket_bytecount, aggregated_time)
    # Save byte_count
    with open(processed_socket_bytecount_file, 'w') as f:
        json.dump(processed_socket_bytecount, f, indent=4)

#---------------------------------Compute throughput-------------------------------------------------------
#throughput calculation at 2ms intervals
num_sockets = max(processed_socket_bytecount[timestamp][1] for timestamp in processed_socket_bytecount)
print(f"Number of sockets: {num_sockets}")

throughput_by_sockets_2ms = {}
for socket_count in range(1, num_sockets + 1):
    throughput_by_sockets_2ms[socket_count] = tp_calc.calculate_interval_throughput(aggregated_time, processed_socket_bytecount, socket_count, 2, begin_time)
    print(f"Calculated throughput for {socket_count} sockets with {len(throughput_by_sockets_2ms[socket_count])} points")

throughput_by_sockets_10ms = {}
for socket_count in range(1, num_sockets + 1):
    throughput_by_sockets_10ms[socket_count] = tp_calc.calculate_interval_throughput(aggregated_time, processed_socket_bytecount, socket_count, 10, begin_time)
    # print(f"Calculated throughput for {socket_count} sockets with {len(throughput_by_sockets_10ms[socket_count])} points")


# --------------------------Plot Throughput------------------------------------------------------------------

title = "Socket-level Throughput, Separated by Number of Sockets Contributing"

socket_plots.plot_throughput_separated_by_sockets(throughput_by_sockets_2ms, start_time=0, end_time=16, source_times=begin_and_end_times, begin_time=begin_time, title=title, scatter=False, save=True, base_path=args.input_dir)
