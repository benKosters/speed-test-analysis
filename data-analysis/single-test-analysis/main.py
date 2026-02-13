"""
This is the main driver for exploratory data analysis (just learning about one single test)

For a Conventional Ookla test, the command is: python3 eda_driver.py ../../ookla/test-execution/ookla-test-results/michwave-multi-2025-10-02_1945 --save

For a RABBITS test, this should look like: python3 eda_driver.py ../tests/test_1_ookla_upload_multi_5_30000000/ --save


Steps of the program:
1) normalize the data into an form that is agnositc of the test type (upload or download).
2) aggregate all unique timestamps that occur, so that we can properly distribute the bytecounts from each HTTP stream.
3) find the proportion of bytes send within each time interval, summing them up and keeping track of many flows are contributing to the bytecount.
4) calculate the throughput based on the bytecounts and the time intervals.
5)plot throughput


**NOTE:** when plotting or comparing latency.json or loaded_latency.json, the timestamps need to be normalized to compare them against the throughput.

"""
import json
import argparse
import sys
import os
import pandas as pd

# Custom modules.
import data_normalization as dn
import dimension_throughput_calc as tp_calc
import statistics
import plots
import utilities
from statistics import StatisticsAccumulator
import dimension_data_selection as data_selection


#Just for testing:
import time

# Set up argument parsing to allow a base path as input
parser = argparse.ArgumentParser(description='Process byte time and latency JSON files.')
parser.add_argument('base_path', type=str, help='Base path to the JSON files')
parser.add_argument('--save', action='store_true', help='Save plots to plot_images directory')
parser.add_argument('--bin', type=int, default=1, help='Bin size for aggregating data')
args = parser.parse_args()

print(f"Analyzing test: {args.base_path}")
print(f"Bin size: {args.bin}ms\n")

socket_file = os.path.join(args.base_path, "socketIds.json")

# Store information about the test, to be saved as JSON file
test_data = {}

# Create to hold all statistics computed throughput data pipeline
stats_accumulator = StatisticsAccumulator(args.base_path)
stats_accumulator.add('bin_size_ms', args.bin)


# Step 1 Data Normalization and Validation-----------------------
normalization_data = dn.run_normalization_driver(args.base_path, stats_accumulator, socket_file=socket_file)
byte_list = normalization_data['byte_list']
aggregated_time = normalization_data['aggregated_time']
source_times = normalization_data['source_times']
begin_time = normalization_data['begin_time']
byte_count = normalization_data['byte_count']
# Step 2: Data Selection -----------------------------------------
# TODO Data selection, collect these metrics
# TODO Calculate and extract more metrics

data_selection_results = data_selection.run_data_selection_driver(byte_count, aggregated_time, stats_accumulator)

# Step 3: Apply Binning ------------------------------------------
# TODO Apply binning

# Step 4: Apply DBSCAN -------------------------------------------
# TODO Update this section to unclude DBSCAN code here!

# Step 5: Slowstart Filtering ------------------------------------
# TODO Update to add slow start filtering here

#Step 6: Throughput Calculation ----------------------------------
stats_accumulator.print_summary()
throughput_results = tp_calc.run_throughput_calculation_driver(byte_count, aggregated_time, source_times, begin_time, args.bin, stats_accumulator)

#Step 7: Plotting ------------------------------------------------
# TODO Update plotting driver

# TODO: Move weighted mean calculation to throughput_driver.py
# result = tp_calc.calculate_throughput_weighted_points(aggregated_time, byte_count, num_flows, begin_time)
# weighted_mean = sum(p['throughput'] * p['weight'] for p in result['weighted_points'])
# print(f"Weighted mean: {weighted_mean:.2f} Mbps")

plots.run_plot_driver(
    byte_count=byte_count,
    throughput_results_2ms=throughput_results['throughput_results_2ms'],
    throughput_results_50ms=throughput_results['throughput_results_50ms'],
    throughput_by_flows_2ms=throughput_results['throughput_by_flows_2ms'],
    throughput_by_flows_50ms=throughput_results['throughput_by_flows_50ms'],
    source_times=source_times,
    begin_time=begin_time,
    base_path=args.base_path,
    save=args.save
)

#Step 8: Write Stats Accumulator to JSON -------------------------
stats_accumulator.save_all()