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


def run_single_test_analysis(base_path, bin_size=1, artifact_filter=False, all_data=True, save_plots=False):
    """
    Wrapper function call to allow for this function being called elsewhere (for comparing tests)
    """
    print(f"Analyzing test: {base_path}")
    print(f"Bin size: {bin_size}ms\n")

    # Extract server from speedtest_result.json one level above base_path
    parent_dir = os.path.dirname(base_path.rstrip('/'))
    speedtest_result_path = os.path.join(parent_dir, "speedtest_result.json")

    try:
        with open(speedtest_result_path, 'r') as f:
            speedtest_data = json.load(f)
            server = str(speedtest_data.get('server', 'Unknown')).capitalize()
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        print(f"Warning: Could not read server from {speedtest_result_path}: {e}")
        # Fallback to parsing from path
        server = os.path.basename(os.path.dirname(base_path) if base_path.endswith(('download','download/','upload/','upload')) else base_path).split('-')[0]

    print(f"Server: {server}\n")

    socket_file = os.path.join(base_path, "socketIds.json")

    # Create to hold all statistics computed throughput data pipeline
    stats_accumulator = StatisticsAccumulator(base_path)

    # Step 1 Data Normalization and Validation-----------------------

    # This code only needs to be run once for a test
    normalization_data = dn.run_normalization_driver(base_path, stats_accumulator, socket_file=socket_file)
    byte_list = normalization_data['byte_list']
    aggregated_time = normalization_data['aggregated_time']
    source_times = normalization_data['source_times']
    begin_time = normalization_data['begin_time']
    byte_count = normalization_data['byte_count']

    # Step 2: Data Selection -----------------------------------------
    # TODO Data selection, collect these metrics
    data_selection_results = data_selection.run_data_selection_driver(byte_count, aggregated_time, stats_accumulator)

    # Run single configuration
    print(f"Running configuration: Artifact Filter={artifact_filter}, Bin Size={bin_size}ms, All Data={all_data}")

    # Create a configuration accumulator
    config_accumulator = StatisticsAccumulator(base_path)
    config_accumulator.add('all_data', all_data)
    config_accumulator.add('artifact_filter', artifact_filter)
    config_accumulator.add('bin_size_ms', bin_size)

    # Step 3: Throughput Calculation / Binning ----------------------------------
    print(f"Running throughput calculation driver")
    all_throughput_data = tp_calc.run_throughput_calculation_driver(byte_count, aggregated_time, begin_time, bin_size, all_data, stats_accumulator, config_accumulator)

    # Step 4: Artifact Filtering ----------------------------------------------------
    strict_interval_throughput_results = artifact.run_artifact_filter(
        config_accumulator,
        all_throughput_data['strict_interval_throughput_results'],
        'throughput',
        artifact_filter=artifact_filter,
        folderpath=base_path,
        plot_suffix=f"_{bin_size}_maxflow_{not all_data}",
        throughput_method="strict"
    )

    threshold_interval_throughput_results = None

    # Create filtered throughput data object (post-artifact filtering)
    filtered_throughput_data = {
        'strict_interval_throughput_results': strict_interval_throughput_results,
        'threshold_interval_throughput_results': threshold_interval_throughput_results,
    }

    # Step 5: Compute Throughput Metrics --------------------------------------------
    strict_throughput_metrics = tp_calc.compute_throughput_metrics(strict_interval_throughput_results, "strict")
    for metric_name, metric_value in strict_throughput_metrics.items():
        config_accumulator.add(metric_name, metric_value)

    threshold_throughput_metrics = tp_calc.compute_throughput_metrics(threshold_interval_throughput_results, "threshold")
    for metric_name, metric_value in threshold_throughput_metrics.items():
        config_accumulator.add(metric_name, metric_value)

    stats_accumulator.print_summary()

    end_time = math.ceil(stats_accumulator.get('list_duration_sec'))
    print("begin time:", begin_time, "end time:", end_time)

    # Step 6: Plotting ------------------------------------------------
    if save_plots:
        configs = {
            'all_data': [all_data],
            'artifact_filter': [artifact_filter],
            'bin_size': [bin_size]
        }
        plot_data = {
            "server": server,
            "configs": configs,
            "bin_size_ms": bin_size,
            "test_type": str(stats_accumulator.get('test_type')).capitalize(),
            "byte_list": byte_list,
            "byte_count": byte_count,
            "source_times": source_times,
            "begin_time": begin_time,
            "end_time": end_time,
            "base_path": base_path,
            "save": save_plots,
            "all_throughput_data": all_throughput_data,
            "filtered_throughput_data": filtered_throughput_data,
        }
        plots.run_plot_driver(plot_data)

    # Step 7: Write Stats Accumulator to JSON -------------------------
    stats_accumulator.save_all()

    # Return the results
    return {
        'all_throughput_data': all_throughput_data,
        'strict_interval_throughput_results': strict_interval_throughput_results,
        'stats_accumulator': stats_accumulator,
        'server': server,
        'test_type': stats_accumulator.get('test_type'),
        'begin_time': begin_time,
        'end_time': end_time,
    }


def run_all_configs_analysis(base_path, save_plots=False):
    """
    Run analysis on all configuration combinations.

    This is the --all-configs mode that tests multiple bin sizes and artifact filter combinations.
    """
    print(f"Analyzing test: {base_path}")
    print("Computing all configurations.")
    print("\n" + "="*60)

    # Extract server from speedtest_result.json one level above base_path
    parent_dir = os.path.dirname(base_path.rstrip('/'))
    speedtest_result_path = os.path.join(parent_dir, "speedtest_result.json")

    try:
        with open(speedtest_result_path, 'r') as f:
            speedtest_data = json.load(f)
            server = str(speedtest_data.get('server', 'Unknown')).capitalize()
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        print(f"Warning: Could not read server from {speedtest_result_path}: {e}")
        # Fallback to parsing from path
        server = os.path.basename(os.path.dirname(base_path) if base_path.endswith(('download','download/','upload/','upload')) else base_path).split('-')[0]

    print(f"Server: {server}\n")

    socket_file = os.path.join(base_path, "socketIds.json")

    # Create to hold all statistics computed throughput data pipeline
    stats_accumulator = StatisticsAccumulator(base_path)

    # Step 1 Data Normalization and Validation-----------------------

    # This code only needs to be run once for a test
    normalization_data = dn.run_normalization_driver(base_path, stats_accumulator, socket_file=socket_file)
    byte_list = normalization_data['byte_list']
    aggregated_time = normalization_data['aggregated_time']
    source_times = normalization_data['source_times']
    begin_time = normalization_data['begin_time']
    byte_count = normalization_data['byte_count']

    # Step 2: Data Selection -----------------------------------------
    # TODO Data selection, collect these metrics
    data_selection_results = data_selection.run_data_selection_driver(byte_count, aggregated_time, stats_accumulator)

    configs = {
        'all_data': [True, False], # True is all data, False is max flow only
        'artifact_filter': [True, False],
        #  'slow_start': [True, False],
        'bin_size': [1, 2, 5, 10, 50, 100]
    }

    if os.path.exists(os.path.join(base_path, "configuration_metrics.csv")):
        print("Configuration metrics CSV already exists. It will be overwritten with new results.")
        os.remove(os.path.join(base_path, "configuration_metrics.csv"))

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
                config_accumulator = StatisticsAccumulator(base_path)
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
                    folderpath=base_path,
                    plot_suffix=f"_{bin_size_option}_maxflow_{not data_selection_option}",
                    throughput_method="strict"
                )
                threshold_interval_throughput_results = None
                # threshold_interval_throughput_results = artifact.run_artifact_filter(
                #     config_accumulator,
                #     all_throughput_data['threshold_interval_throughput'],
                #     'throughput',
                #     artifact_filter=artifact_filter_option,
                #     folderpath=base_path,
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

                config_accumulator.append_to_csv('configuration_metrics.csv')
                i += 1

    stats_accumulator.print_summary()
    stats_accumulator.save_all()


if __name__ == '__main__':
    # Set up argument parsing to allow a base path as input
    parser = argparse.ArgumentParser(description='Process byte time and latency JSON files.')
    parser.add_argument('base_path', type=str, help='Base path to the JSON files')
    parser.add_argument('--save', action='store_true', help='Save plots to plot_images directory')
    parser.add_argument('--bin', type=int, default=1, help='Bin size for aggregating data')
    parser.add_argument('--all-configs', action='store_true', help='Run all 16 configurations (2 dbscan * 2 slow start * 4 bin sizes)')
    args = parser.parse_args()

    if args.all_configs:
        run_all_configs_analysis(args.base_path, args.save)
    else:
        # Run single configuration mode (can also be called programmatically)
        result = run_single_test_analysis(
            base_path=args.base_path,
            bin_size=args.bin,
            artifact_filter=False,  # Default configuration
            all_data=True,  # Default configuration
            save_plots=args.save
        )
