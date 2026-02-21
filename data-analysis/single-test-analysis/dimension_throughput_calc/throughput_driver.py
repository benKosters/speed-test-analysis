import dimension_throughput_calc as tp_calc

def run_throughput_calculation_driver(byte_count, aggregated_time, source_times, begin_time, bin_size, stats_accumulator):
    throughput_results = []
    num_flows = stats_accumulator.get("num_sockets")


    # For a full slate of tests for presenting the final product, calculate throughput for 2 and 10 second intervals with max flow ONLY
    throughput_results_2ms = tp_calc.calculate_interval_throughput(aggregated_time, byte_count, num_flows, bin_size, begin_time)
    throughput_results_50ms = tp_calc.calculate_interval_throughput(aggregated_time, byte_count, num_flows, 50, begin_time)

    throughput_results_2ms_tracking_loss, discarded_stats = tp_calc.calculate_interval_throughput_tracking_discarded_data(aggregated_time, byte_count, num_flows, 100, begin_time)
    print("Discarded Stats for 100ms throughput calculation:", discarded_stats)

    #throughput grouped by number of flows contributing - used to show there is still a throughput even though not all flows are contributing
    throughput_by_flows_2ms = {}
    for flow_count in range(1, num_flows + 1):
        throughput_by_flows_2ms[flow_count] = tp_calc.calculate_interval_throughput(aggregated_time, byte_count, flow_count, bin_size, begin_time)


    throughput_by_flows_50ms = {}
    for flow_count in range(1, num_flows + 1):
        throughput_by_flows_50ms[flow_count] = tp_calc.calculate_interval_throughput(aggregated_time, byte_count, flow_count, 50, begin_time)

    print(f"Statistics for the throughput calculated over {bin_size}ms intervals")

    #Generate throughput results using A and A's traditional method:
    throughput_results_traditional = tp_calc.calculate_traditional_throughput(aggregated_time, byte_count, num_flows, begin_time)

    return  {
                "throughput_results_2ms": throughput_results_2ms,
                "throughput_results_50ms": throughput_results_50ms,
                "throughput_by_flows_2ms": throughput_by_flows_2ms,
                "throughput_by_flows_50ms": throughput_by_flows_50ms,
                "throughput_results_traditional": throughput_results_traditional
            }
