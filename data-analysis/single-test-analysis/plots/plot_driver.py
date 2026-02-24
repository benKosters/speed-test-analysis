"""
Plot Driver - Orchestrates generation of all visualization outputs

This driver coordinates the creation of all plots for a single test analysis.
"""
import os
import pandas as pd
from .plot_bar_bytecount import create_bytecount_bar_chart
from .throughput_plots import plot_throughput_rema_separated_by_flows

def run_plot_driver(
    byte_count,
    throughput_results,
    throughput_by_flows,
    source_times,
    begin_time,
    base_path,
    save=True
):
    if not save:
        print("Plot generation skipped (--save flag not set)")
        return

    print("\n" + "=" * 60)
    print("Plot Generation")
    print("=" * 60)

    df = pd.DataFrame(throughput_results)

    # === Plot 1: Bytecount Bar Chart ===
    print("  [1/1] Generating bytecount bar chart...")
    print("Saving to:", base_path)
    create_bytecount_bar_chart(
        byte_count=byte_count,
        begin_time=begin_time,
        title="Bytes Transferred per Time Interval",
        save_path=base_path,
        max_time=None,
        source_times=source_times
    )

    # === Additional plots (currently commented out, uncomment when needed) ===

    # Plot 2: Throughput separated by flows (2ms)
    print("  [2/N] Generating throughput by flows plot (2ms)...")
    plot_throughput_rema_separated_by_flows(
        throughput_by_flows,
        start_time=0,
        end_time=16,
        source_times=source_times,
        begin_time=begin_time,
        title=None,
        scatter=True,
        save=True,
        base_path=base_path
    )

    # Plot 3: Throughput separated by flows and sockets (2ms)
    # print("  [3/N] Generating throughput by flows and sockets plot (2ms)...")
    # plot_throughput_rema_separated_by_flows_socket_grouped(
    #     throughput_by_flows_2ms,
    #     start_time=0,
    #     end_time=16,
    #     source_times=source_times,
    #     begin_time=begin_time,
    #     title=None,
    #     scatter=True,
    #     save=True,
    #     base_path=base_path
    # )

    print("=" * 60)
    print("✓ Plot generation complete")
