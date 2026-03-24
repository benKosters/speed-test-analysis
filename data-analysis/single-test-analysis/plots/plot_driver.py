"""
Plot Driver - Orchestrates generation of all visualization outputs

This driver coordinates the creation of all plots for a single test analysis.
"""
from .plot_bar_bytecount import create_bytecount_bar_chart
import plots.throughput_plots as throughput_plots

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

    # Uncomment the plots you want to generate:
    # throughput_plots.plot_throughput_and_http_streams(plot_data)
    # throughput_plots.plot_throughput_scatter_max_flows_only(plot_data)
    throughput_plots.plot_throughput_max_flow_only(plot_data, plot_type='line')
    throughput_plots.plot_throughput_max_flow_only(plot_data, plot_type='scatter')
    #throughput_plots.plot_throughput_rema_separated_by_flows(plot_data, scatter=True)
    throughput_plots.plot_throughput_rema_separated_by_flows_socket_grouped(plot_data, scatter=True)

    print("=" * 60)
    print("✓ Plot generation complete")
