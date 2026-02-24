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
# Custom modules.
import data_normalization as dn
import dimension_throughput_calc as tp_calc
import plots
from statistics import StatisticsAccumulator
import dimension_data_selection as data_selection
import dimension_dbscan as dbscan

# Set up argument parsing to allow a base path as input
parser = argparse.ArgumentParser(description='Process byte time and latency JSON files.')
parser.add_argument('base_path', type=str, help='Base path to the JSON files')
parser.add_argument('--save', action='store_true', help='Save plots to plot_images directory')
parser.add_argument('--bin', type=int, default=1, help='Bin size for aggregating data')
parser.add_argument('--all-configs', action='store_true', help='Run all 16 configurations (2 dbscan * 2 slow start * 4 bin sizes)')
args = parser.parse_args()

print(f"Analyzing test: {args.base_path}")
print(f"Bin size: {args.bin}ms\n")

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

if args.all_configs:
    print("Computing all 16 configurations.")
    print("\n" + "="*60)

    configs = {
        'dbscan': [True, False],
        'slow_start': [True, False],
        'bin_size': [1, 5, 10, 50]
    }
else:
    print("Running default configuration.")
    configs = {
        'dbscan': [False],
        'slow_start': [False],
        'bin_size': [args.bin]
    }

print("\n" + "="*60)
i = 0
for dbscan_option in configs['dbscan']:
    for slow_start_option in configs['slow_start']:
        for bin_size_option in configs['bin_size']:
            print(f"Running configuration {i}: DBSCAN={dbscan_option}, Slow Start={slow_start_option}, Bin Size={bin_size_option}ms")
            # Reset byte_count for each configuration
            byte_count = normalization_data['byte_count']
            # Create a new statistics accumulator for this configuration
            config_accumulator = StatisticsAccumulator(args.base_path)
            config_accumulator.add('dbscan_filter', dbscan_option)
            config_accumulator.add('slow_start_filter', slow_start_option)
            config_accumulator.add('bin_size_ms', bin_size_option)

            # Step 4: Apply DBSCAN -------------------------------------------
            if dbscan_option:
                byte_count = dbscan.run_dbscan_driver(args.base_path, dbscan_option, config_accumulator)

            # Step 5: Slowstart Filtering ------------------------------------
            # TODO Update to add slow start filtering here
            if slow_start_option:
                pass

            # Step 6: Throughput Calculation ----------------------------------
            throughput_results = tp_calc.run_throughput_calculation_driver(byte_count, aggregated_time, source_times, begin_time, bin_size_option, stats_accumulator, config_accumulator)

            if args.all_configs:
                config_accumulator.append_to_csv('configuration_metrics.csv')
            i += 1

stats_accumulator.print_summary()

#Step 7: Plotting ------------------------------------------------

plots.run_plot_driver(
    byte_count=byte_count,
    throughput_results=throughput_results['throughput_results'],
    throughput_by_flows=throughput_results['throughput_by_flows'],
    source_times=source_times,
    begin_time=begin_time,
    base_path=args.base_path,
    save=args.save
)

#Step 8: Write Stats Accumulator to JSON -------------------------
stats_accumulator.save_all()