"""
Plot sorted throughput values to identify jumps between lower and higher throughput ranges.

This visualization helps identify:
- Distribution of throughput values
- Natural breaks or jumps in throughput ranges
- Bimodal or multimodal distributions
- Outliers and clusters

Usage:
    python3 plot_sorted_throughput.py <path_to_test_directory> --threshold 2
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import argparse
import os
import sys

import utilities
import dimension_throughput_calc as tp_calc

def plot_sorted_throughput(throughput_results, title=None, save_path=None,
                           show_jumps=True, jump_threshold=None):
    """
    Plot throughput values in sorted order to visualize distribution and jumps.

    Args:
        throughput_results: List of throughput dicts with 'time' and 'throughput' keys
        title: Optional plot title
        save_path: Optional path to save figure
        show_jumps: Whether to highlight large jumps in the sorted values
        jump_threshold: Threshold for detecting jumps (Mbps). If None, uses adaptive threshold
    """
    if not throughput_results:
        print("Error: No throughput data to plot")
        return

    # Extract and sort throughput values
    throughputs = [d['throughput'] for d in throughput_results]
    sorted_throughputs = sorted(throughputs)
    indices = np.arange(len(sorted_throughputs))

    # Calculate statistics
    mean_tp = np.mean(sorted_throughputs)
    median_tp = np.median(sorted_throughputs)
    std_tp = np.std(sorted_throughputs)
    min_tp = np.min(sorted_throughputs)
    max_tp = np.max(sorted_throughputs)

    # Detect jumps (large increases between consecutive sorted values)
    if show_jumps:
        diffs = np.diff(sorted_throughputs)

        if jump_threshold is None:
            # Adaptive threshold: mean + 2 * std of differences
            jump_threshold = np.mean(diffs) + 2 * np.std(diffs)

        jump_indices = np.where(diffs > jump_threshold)[0]
        jump_locations = jump_indices + 1  # Index after the jump

        print(f"\nDetected {len(jump_indices)} significant jumps (threshold: {jump_threshold:.2f} Mbps)")
        for idx in jump_indices:
            from_val = sorted_throughputs[idx]
            to_val = sorted_throughputs[idx + 1]
            diff = to_val - from_val
            print(f"  Jump at position {idx+1}: {from_val:.2f} → {to_val:.2f} Mbps (Δ = {diff:.2f} Mbps)")

    # Create figure with two subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

    # -------------------- Plot 1: Sorted Throughput Values --------------------
    ax1.scatter(indices, sorted_throughputs, s=2, color='red', alpha=0.5, zorder=3)

    # Add horizontal lines for statistics
    ax1.axhline(mean_tp, color='red', linestyle='--', linewidth=2, label=f'Mean: {mean_tp:.2f} Mbps')
    ax1.axhline(median_tp, color='green', linestyle='--', linewidth=2, label=f'Median: {median_tp:.2f} Mbps')
    ax1.axhline(mean_tp + std_tp, color='orange', linestyle=':', linewidth=1.5,
                label=f'Mean ± Std: [{mean_tp-std_tp:.2f}, {mean_tp+std_tp:.2f}] Mbps', alpha=0.7)
    ax1.axhline(mean_tp - std_tp, color='orange', linestyle=':', linewidth=1.5, alpha=0.7)

    # Highlight jumps
    if show_jumps and len(jump_indices) > 0:
        for jump_idx in jump_locations:
            ax1.axvline(jump_idx, color='red', linestyle=':', linewidth=1, alpha=0.5)
            ax1.scatter(jump_idx, sorted_throughputs[jump_idx], s=5, color='blue', zorder=5)

    ax1.set_xlabel('Index (sorted)', fontsize=12)
    ax1.set_ylabel('Throughput (Mbps)', fontsize=12)
    ax1.set_title('Sorted Throughput Values', fontsize=14, fontweight='bold')
    ax1.legend(loc='best', fontsize=10)
    ax1.grid(True, alpha=0.3)

    # Add statistics text box
    stats_text = (f'N = {len(sorted_throughputs)}\n'
                 f'Min = {min_tp:.2f} Mbps\n'
                 f'Max = {max_tp:.2f} Mbps\n'
                 f'Range = {max_tp - min_tp:.2f} Mbps\n'
                 f'Std = {std_tp:.2f} Mbps')
    ax1.text(0.02, 0.98, stats_text, transform=ax1.transAxes,
            fontsize=10, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    # -------------------- Plot 2: Difference Between Consecutive Values --------------------
    if len(sorted_throughputs) > 1:
        diffs = np.diff(sorted_throughputs)
        diff_indices = np.arange(len(diffs))

        ax2.bar(diff_indices, diffs, width=1.0, color='steelblue', alpha=0.7, edgecolor='black', linewidth=0.5)

        # Highlight large jumps
        if show_jumps and len(jump_indices) > 0:
            for jump_idx in jump_indices:
                ax2.bar(jump_idx, diffs[jump_idx], width=1.0, color='red',
                       alpha=0.8, edgecolor='darkred', linewidth=1.5)

        # Add threshold line if jumps are shown
        if show_jumps:
            ax2.axhline(jump_threshold, color='red', linestyle='--', linewidth=2,
                       label=f'Jump Threshold: {jump_threshold:.2f} Mbps', alpha=0.7)

        mean_diff = np.mean(diffs)
        ax2.axhline(mean_diff, color='green', linestyle='--', linewidth=1.5,
                   label=f'Mean Diff: {mean_diff:.2f} Mbps', alpha=0.7)

        ax2.set_xlabel('Index (sorted)', fontsize=12)
        ax2.set_ylabel('Throughput Difference (Mbps)', fontsize=12)
        ax2.set_title('Difference Between Consecutive Sorted Values', fontsize=14, fontweight='bold')
        ax2.legend(loc='best', fontsize=10)
        ax2.grid(True, alpha=0.3, axis='y')

    if title:
        fig.suptitle(title, fontsize=16, fontweight='bold', y=0.995)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"\nPlot saved to: {save_path}")

    plt.show()

    return {
        'sorted_throughputs': sorted_throughputs,
        'mean': mean_tp,
        'median': median_tp,
        'std': std_tp,
        'min': min_tp,
        'max': max_tp,
        'jump_indices': jump_indices if show_jumps else None,
        'jump_threshold': jump_threshold if show_jumps else None
    }


def plot_throughput_histogram_with_jumps(throughput_results, jump_info=None,
                                        title=None, save_path=None, bins=50):
    """
    Plot histogram of throughput values with jump locations marked.

    Args:
        throughput_results: List of throughput dicts
        jump_info: Dictionary returned from plot_sorted_throughput with jump information
        title: Optional plot title
        save_path: Optional path to save figure
        bins: Number of histogram bins
    """
    if not throughput_results:
        print("Error: No throughput data to plot")
        return

    throughputs = [d['throughput'] for d in throughput_results]

    fig, ax = plt.subplots(figsize=(14, 6))

    # Create histogram
    n, bins_edges, patches = ax.hist(throughputs, bins=bins, color='steelblue',
                                     alpha=0.7, edgecolor='black', linewidth=0.5)

    # Add statistics
    mean_tp = np.mean(throughputs)
    median_tp = np.median(throughputs)

    ax.axvline(mean_tp, color='red', linestyle='--', linewidth=2,
              label=f'Mean: {mean_tp:.2f} Mbps')
    ax.axvline(median_tp, color='green', linestyle='--', linewidth=2,
              label=f'Median: {median_tp:.2f} Mbps')

    # Mark jump locations if provided
    if jump_info and jump_info.get('jump_indices') is not None:
        sorted_throughputs = jump_info['sorted_throughputs']
        jump_indices = jump_info['jump_indices']

        for jump_idx in jump_indices:
            jump_value = sorted_throughputs[jump_idx + 1]
            ax.axvline(jump_value, color='orange', linestyle=':', linewidth=2, alpha=0.7)

        # Add legend entry for jumps
        if len(jump_indices) > 0:
            ax.axvline(0, color='orange', linestyle=':', linewidth=2, alpha=0.7,
                      label=f'Jump Locations ({len(jump_indices)})')

    ax.set_xlabel('Throughput (Mbps)', fontsize=12)
    ax.set_ylabel('Frequency', fontsize=12)
    ax.set_title('Throughput Distribution Histogram', fontsize=14, fontweight='bold')
    ax.legend(loc='best', fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')

    if title:
        fig.suptitle(title, fontsize=16, fontweight='bold')

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Histogram saved to: {save_path}")

    plt.show()


def main():
    parser = argparse.ArgumentParser(
        description='Plot sorted throughput values to identify distribution and jumps'
    )
    parser.add_argument('test_path', type=str, help='Path to test directory')
    parser.add_argument('--threshold', type=float, default=2,
                       help='Interval threshold for throughput calculation (ms)')
    parser.add_argument('--num-flows', type=int, default=None,
                       help='Number of flows to filter for (default: use max flows)')
    parser.add_argument('--jump-threshold', type=float, default=None,
                       help='Custom threshold for detecting jumps (Mbps)')
    parser.add_argument('--no-jumps', action='store_true',
                       help='Disable jump detection and highlighting')
    parser.add_argument('--histogram', action='store_true',
                       help='Also create histogram plot')
    parser.add_argument('--bins', type=int, default=50,
                       help='Number of bins for histogram (default: 50)')
    parser.add_argument('--title', type=str, default=None,
                       help='Custom plot title')
    parser.add_argument('--save', action='store_true',
                       help='Save the plots')

    args = parser.parse_args()

    # Load data
    byte_count_file = os.path.join(args.test_path, "byte_count.json")

    if not os.path.exists(byte_count_file):
        print(f"Error: byte_count.json not found in {args.test_path}")
        return

    print(f"Loading byte_count from: {byte_count_file}")
    byte_count_raw = utilities.load_json(byte_count_file)
    byte_count = {int(timestamp): value for timestamp, value in byte_count_raw.items()}

    # Get aggregated timestamps and begin_time
    timestamps = sorted(byte_count.keys())
    begin_time = timestamps[0]

    # Determine num_flows
    if args.num_flows is None:
        num_flows = max(byte_count[ts][1] for ts in timestamps if byte_count[ts][1] > 0)
        print(f"Auto-detected num_flows: {num_flows}")
    else:
        num_flows = args.num_flows
        print(f"Using specified num_flows: {num_flows}")

    # Calculate throughput
    print(f"\nCalculating throughput with {args.threshold}ms interval threshold...")
    throughput_results = tp_calc.calculate_interval_throughput(
        timestamps, byte_count, num_flows, args.threshold, begin_time
    )

    print(f"Generated {len(throughput_results)} throughput points")

    if not throughput_results:
        print("Error: No throughput results generated")
        return

    # Determine save paths
    save_path_sorted = None
    save_path_hist = None
    if args.save:
        save_path_sorted = os.path.join(args.test_path, 'sorted_throughput.png')
        save_path_hist = os.path.join(args.test_path, 'throughput_histogram_jumps.png')

    # Create sorted throughput plot
    print("\nGenerating sorted throughput plot...")
    jump_info = plot_sorted_throughput(
        throughput_results,
        title=args.title,
        save_path=save_path_sorted,
        show_jumps=not args.no_jumps,
        jump_threshold=args.jump_threshold
    )

    # Create histogram if requested
    if args.histogram:
        print("\nGenerating histogram plot...")
        plot_throughput_histogram_with_jumps(
            throughput_results,
            jump_info=jump_info if not args.no_jumps else None,
            title=args.title,
            save_path=save_path_hist,
            bins=args.bins
        )

    print("\nDone!")


if __name__ == "__main__":
    main()
