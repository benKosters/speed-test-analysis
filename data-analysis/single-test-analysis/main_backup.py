"""
This is the main driver for exploratory data analysis (just learning about one single test)

For a Conventional Ookla test, the command is: python3 main.py ../../ookla/test-tool/ookla-test-results/michwave-multi-2025-10-02_1945 --save

For a RABBITS test, this should look like: python3 main.py ../tests/test_1_ookla_upload_multi_5_30000000/ --save


Steps of the program:
1) normalize the data into an form that is agnositc of the test type (upload or download).
2) aggregate all unique timestamps that occur, so that we can properly distribute the bytecounts from each HTTP stream.
3) find the proportion of bytes send within each time interval, summing them up and keeping track of many flows are contributing to the bytecount.
4) calculate the throughput based on the bytecounts and the time intervals.
5)plot throughput


**NOTE:** when plotting or comparing latency.json or loaded_latency.json, the timestamps need to be normalized to compare them against the throughput.

"""
import argparse
import os
import math
import json
# Custom modules.
import data_normalization as dn
import dimension_throughput_calc as tp_calc
import plots
from statistics import StatisticsAccumulator, save_socket_stream_data
import dimension_data_selection as data_selection
import dimension_artifact as artifact
import dimension_slow_start as slow_start

# Set up argument parsing to allow a base path as input
parser = argparse.ArgumentParser(description='Process byte time and latency JSON files.')
parser.add_argument('base_path', type=str, help='Base path to the JSON files')
parser.add_argument('--save', action='store_true', help='Save plots to plot_images directory')
parser.add_argument('--bin', type=int, default=1, help='Bin size for aggregating data')
parser.add_argument('--all-configs', action='store_true', help='Run all 16 configurations (2 dbscan * 2 slow start * 4 bin sizes)')
args = parser.parse_args()

print(f"Analyzing test: {args.base_path}")
print(f"Bin size: {args.bin}ms\n")

# Extract server from speedtest_result.json one level above base_path
parent_dir = os.path.dirname(args.base_path.rstrip('/'))
speedtest_result_path = os.path.join(parent_dir, "speedtest_result.json")

try:
    with open(speedtest_result_path, 'r') as f:
        speedtest_data = json.load(f)
        server = str(speedtest_data.get('server', 'Unknown')).capitalize()
except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
    print(f"Warning: Could not read server from {speedtest_result_path}: {e}")
    # Fallback to parsing from path
    server = os.path.basename(os.path.dirname(args.base_path) if args.base_path.endswith(('download','download/','upload/','upload')) else args.base_path).split('-')[0]

print(f"Server: {server}\n")

socket_file = os.path.join(args.base_path, "socketIds.json")

# Create to hold all statistics computed throughput data pipeline
stats_accumulator = StatisticsAccumulator(args.base_path)

# Step 1 Data Normalization and Validation-----------------------

# This code only needs to be run once for a test
normalization_data = dn.run_normalization_driver(args.base_path, stats_accumulator, socket_file=socket_file)
byte_list = normalization_data['byte_list']
aggregated_time = normalization_data['aggregated_time']
source_times = normalization_data['source_times']
begin_time = normalization_data['begin_time']
byte_count = normalization_data['byte_count']

# Step 2: Data Selection -----------------------------------------
# TODO Data selection, collect these metrics
data_selection_results = data_selection.run_data_selection_driver(byte_count, aggregated_time, stats_accumulator)

# http_stream_data_structure = save_socket_stream_data(byte_list, source_times, args.base_path, print_output=True)
# exit()  # TEMP: for populating http_stream_data.json

if args.all_configs:
    print("Computing all configurations.")
    print("\n" + "="*60)

    # configs = {
    #     'all_data': [True, False], # True is all data, False is max flow only
    #     'dbscan': [True, False],
    #     'slow_start': [True, False],
    #     'bin_size': [1, 5, 10, 25, 50, 75, 100]
    # }
    configs = {
        'all_data': [True, False], # True is all data, False is max flow only
        'artifact_filter': [True, False],
        #  'slow_start': [True, False],
        'bin_size': [1, 2, 5, 10, 50, 100]
    }
else:
    print("Running default configuration.")
    configs = {
        'all_data': [True], # Default to just max flow data
        'artifact_filter': [False],
        # 'slow_start': [False], #TODO: Add slow start filtering
        'bin_size': [args.bin]
    }

if os.path.exists(os.path.join(args.base_path, "configuration_metrics.csv")):
    print("Configuration metrics CSV already exists. It will be overwritten with new results.")
    os.remove(os.path.join(args.base_path, "configuration_metrics.csv"))

# For tracking the configuration number
print("\n" + "="*60)
i = 0


# 3-22 note: we have now flipped to do binning -> artifact filtering
for data_selection_option in configs['all_data']:
    for artifact_filter_option in configs['artifact_filter']:
        #for slow_start_option in configs['slow_start']:
        for bin_size_option in configs['bin_size']:
            print(f"Running configuration {i}: Artifact Filter={artifact_filter_option}, Bin Size={bin_size_option}ms")
            # Reset byte_count for each configuration - TODO: double check this is needed
            byte_count = normalization_data['byte_count']
            # Create a new statistics accumulator for this configuration
            config_accumulator = StatisticsAccumulator(args.base_path)
            config_accumulator.add('config_number', i)
            config_accumulator.add('all_data', data_selection_option)
            config_accumulator.add('artifact_filter', artifact_filter_option)
            #config_accumulator.add('slow_start_filter', slow_start_option)
            config_accumulator.add('bin_size_ms', bin_size_option)

            # Step 1 and 2Throughput Calculation / Binning ----------------------------------
            print(f"Running throughput calculation driver for configuration {i}")
            all_throughput_data = tp_calc.run_throughput_calculation_driver(byte_count, aggregated_time, begin_time, bin_size_option, data_selection_option, stats_accumulator, config_accumulator)

            # Step 3: Artifact Filtering ----------------------------------------------------
            strict_interval_throughput_results = artifact.run_artifact_filter(
                config_accumulator,
                all_throughput_data['strict_interval_throughput_results'],
                'throughput',
                artifact_filter=artifact_filter_option,
                folderpath=args.base_path,
                plot_suffix=f"_{bin_size_option}_maxflow_{not data_selection_option}",
                throughput_method="strict"
            )
            threshold_interval_throughput_results = None
            # threshold_interval_throughput_results = artifact.run_artifact_filter(
            #     config_accumulator,
            #     all_throughput_data['threshold_interval_throughput'],
            #     'throughput',
            #     artifact_filter=artifact_filter_option,
            #     folderpath=args.base_path,
            #     plot_suffix=f"_{bin_size_option}_maxflow_{not data_selection_option}",
            #     throughput_method="threshold"
            # )

            # 3-24 update: now add the updated throughput values after dbscan has filtered the results

            # Create filtered throughput data object (post-artifact filtering)
            filtered_throughput_data = {
                'strict_interval_throughput_results': strict_interval_throughput_results,
                'threshold_interval_throughput_results': threshold_interval_throughput_results,
            }

            # Step 4: Compute Throughput Metrics --------------------------------------------
            strict_throughput_metrics = tp_calc.compute_throughput_metrics(strict_interval_throughput_results, "strict")
            for metric_name, metric_value in strict_throughput_metrics.items():
                config_accumulator.add(metric_name, metric_value)

            threshold_throughput_metrics = tp_calc.compute_throughput_metrics(threshold_interval_throughput_results, "threshold")
            for metric_name, metric_value in threshold_throughput_metrics.items():
                config_accumulator.add(metric_name, metric_value)


            if args.all_configs:
                config_accumulator.append_to_csv('configuration_metrics.csv')
            i += 1

            # if not args.all_configs:
            #     dn.analyze_throughput_intervals(all_throughput_data['throughput_results'])
            #     config_accumulator.print_summary()

stats_accumulator.print_summary()

end_time = math.ceil(stats_accumulator.get('list_duration_sec'))
print("begin time:", begin_time, "end time:", end_time)

#Step 7: Plotting ------------------------------------------------

# Only plot in specific instances
if not args.all_configs:
    plot_data = {
        "server": server,
        "configs": configs, # the default configurations - updated so if the default configs change, they are represented in the plots
        "bin_size_ms": args.bin,
        "test_type": str(stats_accumulator.get('test_type')).capitalize(),
        "byte_list": byte_list,
        "byte_count": byte_count,
        "source_times": source_times,
        "begin_time": begin_time,
        "end_time": end_time,
        "base_path": args.base_path,
        "save": args.save,
        "all_throughput_data": all_throughput_data,  # This is the unfiltered throughput data
        "filtered_throughput_data": filtered_throughput_data,  # This is throughput results after going through the artifact filtering
    }
    if(args.save):
        plots.run_plot_driver(plot_data)


#Step 8: Write Stats Accumulator to JSON -------------------------
stats_accumulator.save_all()
