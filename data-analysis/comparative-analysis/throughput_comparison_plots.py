import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import matplotlib.colors as mcolors

def create_throughput_comparison_plots(csv_file_path, output_dir="./plots"):
    """
    Create scatter plots comparing Ookla reported throughput vs mean_throughput_2ms
    with categorical grouping by server and flow type.
    """
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(exist_ok=True)

    # Read the CSV data
    df = pd.read_csv(csv_file_path)

    # Convert throughput columns to numeric, handling any missing values
    df['ookla_reported_throughput'] = pd.to_numeric(df['ookla_reported_throughput'], errors='coerce')
    df['mean_throughput_2ms'] = pd.to_numeric(df['mean_throughput_2ms'], errors='coerce')

    # Remove rows with missing throughput data
    df_clean = df.dropna(subset=['ookla_reported_throughput', 'mean_throughput_2ms'])

    # Set up the plotting style
    plt.style.use('default')

    # Create separate plots for download and upload
    for direction in ['download', 'upload']:
        # Filter data for this direction
        direction_data = df_clean[df_clean['test_direction'] == direction].copy()

        if len(direction_data) == 0:
            print(f"No data found for {direction} tests")
            continue

        # Create the figure and axis
        fig, ax = plt.subplots(figsize=(12, 8))

        # Get unique servers and connection types for consistent coloring
        servers = sorted(direction_data['server'].unique())
        connection_types = sorted(direction_data['connection_type'].unique())

        # Create color palette for servers using matplotlib colors
        cmap = plt.cm.get_cmap('tab10')  # Use tab10 colormap for distinct colors
        server_colors = [cmap(i / len(servers)) for i in range(len(servers))]
        server_color_map = dict(zip(servers, server_colors))

        # Create marker styles for connection types
        markers = ['o', 's', '^', 'D', 'v']  # circle, square, triangle_up, diamond, triangle_down
        connection_marker_map = dict(zip(connection_types, markers[:len(connection_types)]))

        # Plot each server-connection_type combination
        for server in servers:
            for conn_type in connection_types:
                subset = direction_data[
                    (direction_data['server'] == server) &
                    (direction_data['connection_type'] == conn_type)
                ]

                if len(subset) > 0:
                    ax.scatter(
                        subset['ookla_reported_throughput'],
                        subset['mean_throughput_2ms'],
                        color=server_color_map[server],
                        marker=connection_marker_map[conn_type],
                        s=80,
                        alpha=0.7,
                        label=f"{server} ({conn_type})",
                        edgecolors='black',
                        linewidth=0.5
                    )

        # Add diagonal line (y=x) for perfect agreement
        max_val = max(
            direction_data['ookla_reported_throughput'].max(),
            direction_data['mean_throughput_2ms'].max()
        )
        min_val = min(
            direction_data['ookla_reported_throughput'].min(),
            direction_data['mean_throughput_2ms'].min()
        )

        ax.plot([min_val, max_val], [min_val, max_val],
                'k--', alpha=0.5, linewidth=2, label='Perfect Agreement (y=x)')

        # Customize the plot
        ax.set_xlabel('Ookla Reported Throughput (Mbps)', fontsize=12)
        ax.set_ylabel('Mean Throughput 2ms (Mbps)', fontsize=12)
        ax.set_title(f'{direction.title()} Tests: Ookla vs Mean 2ms Throughput Comparison',
                     fontsize=14, fontweight='bold')

        # Add grid
        ax.grid(True, alpha=0.3)

        # Add legend
        legend = ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

        # Set equal aspect ratio and adjust limits
        ax.set_aspect('equal', adjustable='box')
        margin = (max_val - min_val) * 0.05
        ax.set_xlim(min_val - margin, max_val + margin)
        ax.set_ylim(min_val - margin, max_val + margin)

        # Calculate statistics
        correlation = direction_data['ookla_reported_throughput'].corr(direction_data['mean_throughput_2ms'])
        mean_diff = (direction_data['mean_throughput_2ms'] - direction_data['ookla_reported_throughput']).mean()
        std_diff = (direction_data['mean_throughput_2ms'] - direction_data['ookla_reported_throughput']).std()

        # Add statistics text box outside the plot, below the legend
        stats_text = f'Correlation: {correlation:.3f}\nMean Diff: {mean_diff:.2f} Mbps\nStd Diff: {std_diff:.2f} Mbps\nN = {len(direction_data)}'

        # Position the stats text below the legend
        fig.text(1.05, 0.6, stats_text, transform=ax.transAxes,
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8),
                fontsize=10)

        # Adjust layout to prevent legend cutoff
        plt.tight_layout()

        # Save the plot
        output_file = f"{output_dir}/throughput_comparison_{direction}.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Saved {direction} plot to: {output_file}")

        # Show the plot
        plt.show()

        # Create a summary table for this direction
        print(f"\n{direction.title()} Tests Summary:")
        print("=" * 50)
        summary_stats = direction_data.groupby(['server', 'connection_type']).agg({
            'ookla_reported_throughput': ['count', 'mean', 'std'],
            'mean_throughput_2ms': ['mean', 'std']
        }).round(2)
        print(summary_stats)
        print()

def create_difference_analysis_plot(csv_file_path, output_dir="./plots"):
    """
    Create additional analysis showing the difference between measurements.
    """
    # Read the data
    df = pd.read_csv(csv_file_path)
    df['ookla_reported_throughput'] = pd.to_numeric(df['ookla_reported_throughput'], errors='coerce')
    df['mean_throughput_2ms'] = pd.to_numeric(df['mean_throughput_2ms'], errors='coerce')
    df_clean = df.dropna(subset=['ookla_reported_throughput', 'mean_throughput_2ms'])

    # Calculate difference and percentage difference
    df_clean['throughput_diff'] = df_clean['mean_throughput_2ms'] - df_clean['ookla_reported_throughput']
    df_clean['throughput_percent_diff'] = (df_clean['throughput_diff'] / df_clean['ookla_reported_throughput']) * 100

    # Create subplots for difference analysis
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))

    for i, direction in enumerate(['download', 'upload']):
        direction_data = df_clean[df_clean['test_direction'] == direction]

        if len(direction_data) == 0:
            continue

        # Box plot of differences by server and connection type
        ax1 = axes[i, 0]

        # Create manual boxplots grouped by server and connection type
        servers_list = sorted(direction_data['server'].unique())
        connection_types = sorted(direction_data['connection_type'].unique())

        box_data = []
        labels = []
        positions = []
        pos = 1

        for server in servers_list:
            for conn_type in connection_types:
                subset = direction_data[
                    (direction_data['server'] == server) &
                    (direction_data['connection_type'] == conn_type)
                ]['throughput_diff'].dropna()

                if len(subset) > 0:
                    box_data.append(subset)
                    labels.append(f"{server}\n({conn_type})")
                    positions.append(pos)
                    pos += 1

        if box_data:
            bp = ax1.boxplot(box_data, positions=positions, patch_artist=True)
            ax1.set_xticks(positions)
            ax1.set_xticklabels(labels, rotation=45, ha='right')

            # Color the boxes
            cmap = plt.cm.get_cmap('Set3')
            for patch, pos in zip(bp['boxes'], positions):
                patch.set_facecolor(cmap((pos-1) / len(positions)))

        ax1.set_title(f'{direction.title()}: Throughput Difference by Server')
        ax1.set_ylabel('Difference (Mean 2ms - Ookla) [Mbps]')
        ax1.axhline(y=0, color='red', linestyle='--', alpha=0.7)

        # Histogram of percentage differences
        ax2 = axes[i, 1]
        servers = direction_data['server'].unique()
        cmap = plt.cm.get_cmap('tab10')
        colors = [cmap(i / len(servers)) for i in range(len(servers))]

        for j, server in enumerate(servers):
            server_data = direction_data[direction_data['server'] == server]
            ax2.hist(server_data['throughput_percent_diff'], alpha=0.6,
                    label=server, color=colors[j], bins=20)

        ax2.set_title(f'{direction.title()}: Distribution of % Differences')
        ax2.set_xlabel('Percentage Difference (%)')
        ax2.set_ylabel('Frequency')
        ax2.legend()
        ax2.axvline(x=0, color='red', linestyle='--', alpha=0.7)

    plt.tight_layout()
    output_file = f"{output_dir}/throughput_difference_analysis.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved difference analysis plot to: {output_file}")
    plt.show()

if __name__ == "__main__":
    # Set the path to your CSV file
    csv_file = "./november_test_results.csv"  # Update this path as needed

    print("Creating throughput comparison plots...")
    create_throughput_comparison_plots(csv_file)

    print("\nCreating difference analysis plots...")
    create_difference_analysis_plot(csv_file)

    print("\nAll plots created successfully!")