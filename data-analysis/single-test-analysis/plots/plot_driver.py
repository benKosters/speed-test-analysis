"""
Plot Driver - Orchestrates generation of all visualization outputs

This driver coordinates the creation of all plots for a single test analysis.
"""

import plots

def run_plot_driver(plot_data):
    if not plot_data["save"]:
        print("Plot generation skipped (--save flag not set)")
        return

    print("\n" + "=" * 60)
    print("Plot Generation")
    print("Begin time:", plot_data["begin_time"], "End time:", plot_data["end_time"])
    print("=" * 60)

    # === All plot functions now accept plot_data directly ===
    print("Generating plots...")
    print("Saving to:", plot_data["base_path"])

    # Threshold interval throughput plots
    # Uncomment the plotsto generate:
    # plots.plot_throughput_and_http_streams(plot_data)
    # plots.plot_throughput_scatter_max_flows_only(plot_data)
    # plots.plot_throughput_max_flow_only(plot_data, plot_type='line')
    # plots.plot_throughput_max_flow_only(plot_data, plot_type='scatter')
    # plots.plot_throughput_rema_separated_by_flows(plot_data, scatter=True)
    plots.plot_throughput_rema_separated_by_flows_socket_grouped(plot_data, scatter=True, rema = False)


    # Strict interval throughput plots
    # plots.plot_strict_throughput_scatter(plot_data, start_time=0, end_time=None, line = False)

    # plots.plot_strict_throughput_scatter(plot_data, start_time=0, end_time=None, line = True)




    print("=" * 60)
    print("✓ Plot generation complete")
