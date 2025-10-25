"""
This is the main driver for exploratory data analysis (just learning about one single test)

For a Conventional Ookla test, the command is: python3 eda_driver.py ../../ookla/test-execution/ookla-test-results/michwave-multi-2025-10-02_1945 --save

For a RABBITS test, this should look like: python3 eda_driver.py ../tests/test_1_ookla_upload_multi_5_30000000/ --save


Steps of the program:
1) normalize the data into an form that is agnositc of the test type (upload or download).
2) aggregate all unique timestamps that occur, so that we can properly distribute the bytecounts from each HTTP stream.
3) find the proportion of bytes send within each time interval, summing them up and keeping track of how many flows are contributing to the bytecount.
4) calculate the throughput based on the bytecounts and the time intervals.
5)plot throughput


**NOTE:** when plotting or comparing latency.json or loaded_latency.json, the timestamps need to be normalized to compare them against the throughput.

"""
import json
import argparse
import sys
import os
import pandas as pd

#Custom function imports to keep the driver clean:
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import throughput_data_processing as tp_proc
import throughput_plots as tp_plot
import data_processing_validation as validate
import throughput_calculation as tp_calc
import summary_statistics as ss
import utilities


# Set up argument parsing to allow a base path as input
parser = argparse.ArgumentParser(description='Process byte time and latency JSON files.')
parser.add_argument('base_path', type=str, help='Base path to the JSON files')
parser.add_argument('--save', action='store_true', help='Save plots to plot_images directory')

args = parser.parse_args()

# Print base path and working directory for debugging
print(f"Provided Base Path: {args.base_path}")
print(f"Current Working Directory: {os.getcwd()}")

# Construct the full file paths by appending the specific filenames
byte_file = os.path.abspath(os.path.join(args.base_path, "byte_time_list.json"))
current_file = os.path.abspath(os.path.join(args.base_path, "current_position_list.json"))
latency_file = os.path.abspath(os.path.join(args.base_path, "latency.json"))
loaded_latency_file = os.path.abspath(os.path.join(args.base_path, "loaded_latency.json"))
socket_file = os.path.abspath(os.path.join(args.base_path, "socketIds.json"))

#loaded_latency_file = os.path.abspath(os.path.join(args.base_path, "normalized_latency.json"))
# Debugging: Print the constructed paths
print()
print(f"Byte Time File: {byte_file}")
print(f"Current Position File: {current_file}")
print(f"Latency File: {latency_file}")
print(f"Loaded Latency File: {loaded_latency_file}")
print()

# Check and load files
files_to_check = [byte_file, current_file, loaded_latency_file]
if os.path.exists(latency_file):
    files_to_check.append(latency_file)

for file_path in files_to_check:
    print(f"Checking: {file_path}")
    if not os.path.exists(file_path):
        print(f"ERROR: File not found - {file_path}\n")
    else:
        print(f"File exists: {file_path}\n")

if not os.path.exists(latency_file):
    print(f"Optional file (unloaded latency): {latency_file}")
    print("File not found - this is OK if no unload URLs were used in the test\n")
else:
    print(f"Optional file (unloaded latency): {latency_file}")
    print("File exists - unloaded latency data will be included\n")
print()


#-----------------Step 1: Normalize Data-------------------------
"""
 Normalize the test data based on the test type (upload or download) - This function is defined in throughput_calculation_functions.py
 #FIXME: test_type might not be needed.
"""
byte_list, test_type = tp_proc.normalize_test_data(byte_file, current_file, latency_file)

normalized_byte_list_file = os.path.abspath(os.path.join(args.base_path, "normalized_byte_list.json"))

print(f"Byte List Length: {len(byte_list)}")
print()

#----------------------Step 2: Aggregating timestamps----------------------------------------------
"""
In order to calculate throughput, (especially for multiple flows) we need to aggregate the timestamps to find
the intervals of time that byte counts were being sent over.
"""
aggregated_time, source_times, begin_time = tp_proc.aggregate_timestamps_and_find_stream_durations(byte_list, socket_file)
old = -1


for x in aggregated_time:
    if x == old:
        print("Found a duplicate timestamp in aggregated_time:", x)

ss.save_socket_stream_data(byte_list, source_times, args.base_path, print_output=False)
print()

#--------------------------------Step 3: Summing bytecounts for timestamps------------------------

byte_count_file = os.path.abspath(os.path.join(args.base_path, "byte_count.json"))

# If the file exists, load it; otherwise, calculate and save it
if os.path.exists(byte_count_file):
    print(f"Loading byte_count data: {byte_count_file}")
    # Load the byte_count data and convert string keys back to integers
    byte_count_raw = utilities.load_json(byte_count_file)
    # Convert the dictionary keys from strings back to integers
    byte_count = {int(timestamp): value for timestamp, value in byte_count_raw.items()}
    print(f"Converted {len(byte_count)} timestamp keys from strings to integers")
else:
    print(f"Calculating and saving byte_count data: {byte_count_file}")

    #byte_count = tp_proc.sum_bytecounts_for_timestamps(byte_list, aggregated_time) #this function has bugs!
    byte_count = tp_proc.sum_all_bytecounts_across_http_streams(byte_list, aggregated_time)
    # Save byte_count
    with open(byte_count_file, 'w') as f:
        json.dump(byte_count, f, indent=4)

#Print some stats about the byte_count
validate.byte_count_validation(byte_list, byte_count)


# ----------------------------------Step 4: Throughput Calculation---------------------------------------------
throughput_results = []
num_flows = max(byte_count[timestamp][1] for timestamp in byte_count) #find the max number of flows - there should never be MORE than the defined number of flows contributing to a bytecount
print("max number of flows:", num_flows)
ss.calculate_percent_of_all_flows_contributing(byte_count, num_flows)

# For a full slate of tests for presenting the final product, calculate throughput for 2 and 10 second intervals with max flow ONLY
throughput_results_2ms = tp_calc.calculate_interval_throughput(aggregated_time, byte_count, num_flows, 1, begin_time)
throughput_results_50ms = tp_calc.calculate_interval_throughput(aggregated_time, byte_count, num_flows, 50, begin_time)

#throughput grouped by number of flows contributing - used to show there is still a throughput even though not all flows are contributing
throughput_by_flows_2ms = {}
for flow_count in range(1, num_flows + 1):
    throughput_by_flows_2ms[flow_count] = tp_calc.calculate_interval_throughput(aggregated_time, byte_count, flow_count, 2, begin_time)
    #throughput_by_flows_2ms[flow_count] = tp_calc.calculate_traditional_throughput(aggregated_time, byte_count, flow_count, begin_time)

throughput_by_flows_50ms = {}
for flow_count in range(1, num_flows + 1):
    throughput_by_flows_50ms[flow_count] = tp_calc.calculate_interval_throughput(aggregated_time, byte_count, flow_count, 50, begin_time)

# print("Number of througput points for 2ms:", len(throughput_results_2ms))
validate.analyze_throughput_intervals(throughput_results_2ms)

print("stats for 2ms interval")
validate.throughput_mean_median_range(throughput_results_2ms)

print("stats for 50ms interval")
validate.throughput_mean_median_range(throughput_results_50ms)

#print out the number of flows contributing to a byte count, and the frequency that they occur.
#ss.calculate_occurrence_sums(byte_count)

#---------------------------------------------Plotting-------------------------------------------------
test_title = "Spacelink Single Flow, Test 1"
df_2ms = pd.DataFrame(throughput_results_2ms) # df for throughput
df_10ms = pd.DataFrame(throughput_results_50ms) # df for throughput

# #graphs to be used in final report:
# #1) plot showing throughput with only the max number of flows
#tp_plot.plot_throughput_and_http_streams(df_2ms, title=f"{test_title} 2ms Interval", source_times=source_times, begin_time=begin_time, save =args.save, base_path = args.base_path)
#plot.plot_throughput_and_http_streams(df_10ms, title=f"{test_title} 10ms Interval", source_times=source_times, begin_time=begin_time, save =args.save, base_path = args.base_path)

#2 and 3) plot throughput with all points classified by how many flows are contributing (2ms and 10ms bin sizes)
tp_plot.plot_throughput_rema_separated_by_flows(throughput_by_flows_2ms, start_time=0, end_time=15, source_times=source_times, begin_time=begin_time, title=f"{test_title} All Flows, 2ms Interval",scatter= False, save =args.save, base_path = args.base_path)
tp_plot.plot_throughput_rema_separated_by_flows(throughput_by_flows_50ms, start_time=0, end_time=15, source_times=source_times, begin_time=begin_time, title=f"{test_title} All Flows, 10ms Interval",save =args.save, base_path = args.base_path)

# # # 4 and 5) plot throughput for all flows, with scatter plot overlay
#plot.plot_throughput_rema_separated_by_flows(throughput_by_flows_2ms, start_time=0, end_time=15, source_times=source_times, begin_time=begin_time, title=f"{test_title} All Flows, 2ms Interval",scatter= True, save =args.save, base_path = args.base_path)
# plot.plot_throughput_rema_separated_by_flows(throughput_by_flows_10ms, start_time=0, end_time=15, source_times=source_times, begin_time=begin_time, title=f"{test_title} All Flows, 10ms Interval", scatter = True, save =args.save, base_path = args.base_path)

# # 6 and 7) Plot individual HTTP streams for both upload and download tests
if test_type == "upload":
    pass
    #tp_plot.plot_throughput_and_http_streams(df_2ms, title=f"{test_title} 2ms Interval", source_times=source_times, begin_time=begin_time, save =args.save, base_path = args.base_path)
    # current_list = hf.load_json(current_file)
    # # Normalize the timestamps in current_position_list (Use this if plotting each individual source's byte counts)
    # normalized_current_list = hf.normalize_current_position_list(current_position_list=current_list,begin_time=begin_time)
    #tp_plot.plot_rema_per_http_stream(normalized_current_list, test_type="upload", save=args.save, base_path=args.base_path, source_times=source_times, begin_time=begin_time)
    # # Plot aggregated bytecounts for upload
    # plot.plot_aggregated_bytecount(normalized_current_list, test_type="upload", save=args.save, base_path=args.base_path, source_times=source_times, begin_time=begin_time)
elif test_type == "download":
    pass
    # For download tests, use the normalized byte_list directly
    #plot.plot_rema_per_http_stream(byte_list, test_type="download", save=args.save, base_path=args.base_path, source_times=source_times, begin_time=begin_time)
    # Plot aggregated bytecounts for download
    #plot.plot_aggregated_bytecount(byte_list, test_type="download", save=args.save, base_path=args.base_path, source_times=source_times, begin_time=begin_time)
    #plot.plot_rema_per_http_stream(byte_list, test_type="download", save=args.save, base_path=args.base_path, source_times=source_times, begin_time=begin_time)


#------------------Step 5: Plotting Latency-------------------------------------------------

# Load and plot latency data - only if files exist
# latency_data_available = os.path.exists(latency_file) or os.path.exists(loaded_latency_file)

# if latency_data_available:
#     idle_latencies = []
#     loaded_latencies = []

#     # Load idle latency if available (from latency.json which now contains idle/unload latency)
#     if os.path.exists(latency_file):
#         with open(latency_file, 'r') as f:
#             idle_latency = json.load(f)
#         idle_latencies = tp.extract_latencies(idle_latency)
#         print("Idle Latency Values:", idle_latencies)
#     else:
#         print("No idle latency file found - skipping idle latency plotting")

#     # Load loaded latency if available
#     if os.path.exists(loaded_latency_file):
#         with open(loaded_latency_file, 'r') as f:
#             loaded_latency = json.load(f)
#         loaded_latencies = tp.extract_latencies(loaded_latency)
#         print("Loaded Latency Values:", loaded_latencies)
#     else:
#         print("No loaded latency file found - skipping loaded latency plotting")

#     # Plot latencies if we have any data
#     if idle_latencies or loaded_latencies:
#         plt.figure(figsize=(10,5))

#         if idle_latencies:
#             plt.scatter(range(len(idle_latencies)), idle_latencies, label='Idle Latency', alpha=0.7, color='blue')

#         if loaded_latencies:
#             plt.scatter(range(len(loaded_latencies)), loaded_latencies, label='Loaded Latency', alpha=0.7, color='red')

#         plt.xlabel('Stream Index')
#         plt.ylabel('Latency (ms)')
#         plt.title('Idle vs Loaded Latency Comparison')
#         plt.legend()
#         if args.save:
#             plt.savefig(os.path.join(args.base_path, "plot_images", "latency_scatter.png"))
#         plt.show()

#         # Plot histogram
#         plt.figure(figsize=(10,5))
#         if idle_latencies:
#             plt.hist(idle_latencies, bins=20, alpha=0.7, label='Idle Latency', color='blue')
#         if loaded_latencies:
#             plt.hist(loaded_latencies, bins=20, alpha=0.7, label='Loaded Latency', color='red')
#         plt.xlabel('Latency (ms)')
#         plt.ylabel('Frequency')
#         plt.title('Latency Distribution: Idle vs Loaded')
#         plt.legend()
#         if args.save:
#             plt.savefig(os.path.join(args.base_path, "plot_images", "latency_histogram.png"))
#         plt.show()

#         # Calculate and display latency comparison metrics
#         if idle_latencies and loaded_latencies:
#             idle_mean = sum(idle_latencies) / len(idle_latencies)
#             loaded_mean = sum(loaded_latencies) / len(loaded_latencies)
#             latency_increase = loaded_mean - idle_mean
#             latency_increase_percent = (latency_increase / idle_mean) * 100 if idle_mean > 0 else 0

#             print(f"--------- LATENCY ANALYSIS ---------")
#             print(f"Mean Idle Latency: {idle_mean:.2f}ms")
#             print(f"Mean Loaded Latency: {loaded_mean:.2f}ms")
#             print(f"Latency Increase: {latency_increase:.2f}ms ({latency_increase_percent:.1f}%)")

#     else:
#         print("No latency data available for plotting")
# else:
#     print("No latency files found - skipping latency plotting section")
