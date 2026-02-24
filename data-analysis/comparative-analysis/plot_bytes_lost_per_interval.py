import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import argparse

# Parse command line arguments
parser = argparse.ArgumentParser(description='Plot bytes lost per interval for a specific server or all servers')
parser.add_argument('-s', '--server', type=str, required=False, default=None,
                    help='Server name to filter (e.g., ashburn, chicago, etc.). If not specified, plots all servers.')
args = parser.parse_args()

# Load your data
df = pd.read_csv('/home/benk/cs390/speed-test-analysis/data-analysis/test-suite-scripts/bytes_lost_over_intervals.csv')

# Filter by server if specified
if args.server:
    df = df[df['server'] == args.server]

    if df.empty:
        print(f"Error: No data found for server '{args.server}'")
        available_servers = pd.read_csv('/home/benk/cs390/speed-test-analysis/data-analysis/test-suite-scripts/bytes_lost_over_intervals.csv')['server'].unique()
        print(f"Available servers: {', '.join(sorted(available_servers))}")
        exit(1)

    server_label = args.server
else:
    server_label = "All Servers"

# Filter out 1ms interval data
df = df[df['interval_ms'] != 1]

# Calculate percentage of bytes lost using actual total_bytes_sent from CSV
df['percent_bytes_lost'] = (df['discarded_bytes'] / df['total_bytes_sent']) * 100

# Define marker and color mapping for connection types
connection_config = {
    'single': {'marker': 'o', 'color': '#e41a1c'},  # Circle, red
    'multi': {'marker': 's', 'color': '#377eb8'}    # Square, blue
}

# Create figure with subplots for download and upload
fig, axes = plt.subplots(1, 2, figsize=(16, 6))

# Define colors for box plots
colors = ['#66c2a5', '#fc8d62', '#8da0cb', '#e78ac3', '#a6d854', '#ffd92f']

for idx, direction in enumerate(['download', 'upload']):
    data = df[df['test_direction'] == direction]

    # Get unique interval values and sort the
    intervals = sorted(data['interval_ms'].unique())

    # Prepare data for box plot
    box_data = [data[data['interval_ms'] == interval]['percent_bytes_lost'].values
                for interval in intervals]

    # Create box plot
    bp = axes[idx].boxplot(box_data,
                           positions=range(len(intervals)),
                           widths=0.6,
                           patch_artist=True,
                           showfliers=False,  # Don't show outliers, we'll add points manually
                           whis=[0, 100])  # Extend whiskers to min/max (all data points)

    # Color the boxes
    for patch, color in zip(bp['boxes'], colors):
        #patch.set_facecolor(color)
        patch.set_facecolor("green")  # Uniform light green color
        patch.set_alpha(0.4)

    # Style the box plot elements
    for element in ['whiskers', 'fliers', 'means', 'medians', 'caps']:
        plt.setp(bp[element], color='black', linewidth=1.5, alpha=0.4)

    # Add individual points with jitter, shaped and colored by connection type
    for i, interval in enumerate(intervals):
        interval_data = data[data['interval_ms'] == interval]

        for conn_type in ['single', 'multi']:
            subset = interval_data[interval_data['connection_type'] == conn_type]
            if len(subset) > 0:
                y_values = subset['percent_bytes_lost'].values
                # Add jitter to x positions
                x_values = np.random.normal(i, 0.04, size=len(y_values))
                axes[idx].scatter(x_values, y_values,
                                alpha=1.0,
                                color=connection_config[conn_type]['color'],
                                marker=connection_config[conn_type]['marker'],
                                s=40,
                                edgecolors='black',
                                linewidths=0.5)

    axes[idx].set_title(f'{direction.capitalize()} - Percent Bytes Lost by Interval ({server_label})',
                       fontsize=14, fontweight='bold')
    axes[idx].set_xlabel('Interval (ms)', fontsize=12)
    axes[idx].set_ylabel('Percent Bytes Lost (%)', fontsize=12)
    axes[idx].set_xticks(range(len(intervals))) # Dynamic ticks
    axes[idx].set_ylim(0, 15)
    axes[idx].set_xticklabels(intervals)
    axes[idx].grid(True, alpha=0.3, axis='y')

# Create legend for connection types
from matplotlib.lines import Line2D
legend_elements = []

for conn_type, config in connection_config.items():
    legend_elements.append(Line2D([0], [0], marker=config['marker'], color='w',
                                  markerfacecolor=config['color'],
                                  markersize=10, label=f'{conn_type}',
                                  markeredgecolor='black', markeredgewidth=0.5))

# Add legend to the figure
fig.legend(handles=legend_elements, loc='lower center', bbox_to_anchor=(0.5, -0.02),
          ncol=2, frameon=True, fontsize=11, title='Connection Type')

plt.subplots_adjust(bottom=0.15)  # Make room for the legend at the bottom
filename = f'percent_bytes_lost_by_interval_{args.server if args.server else "all_servers"}.png'
plt.savefig(filename, dpi=300, bbox_inches='tight')
plt.show()