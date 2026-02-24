import pandas as pd
import matplotlib.pyplot as plt
import argparse

# Parse command line arguments
parser = argparse.ArgumentParser(description='Plot latency vs throughput')
parser.add_argument('-s', '--server', type=str, required=False, default=None,
                    help='Server name to filter (e.g., ashburn, chicago, etc.). If not specified, plots all servers.')
args = parser.parse_args()

# Load your data
df = pd.read_csv('/home/benk/cs390/speed-test-analysis/data-analysis/automating-scripts/csvs/virginia-test-results.csv')

# Filter by server if specified
if args.server:
    df = df[df['server'] == args.server]

    if df.empty:
        print(f"Error: No data found for server '{args.server}'")
        available_servers = pd.read_csv('PLACEHOLDER_PATH_TO_CSV')['server'].unique()
        print(f"Available servers: {', '.join(sorted(available_servers))}")
        exit(1)

    server_label = args.server
else:
    server_label = "All Servers"

# Define marker mapping for connection types
connection_markers = {
    'single': 'o',  # Circle
    'multi': 's'    # Square
}

# Define color mapping for servers (you can adjust colors as needed)
# Using a colorblind-friendly palette
server_colors = {
    'ashburn': '#e41a1c',
    'michwave': "#67a1d0",
    'csl': '#ff7f00',
    'deutsche': '#ffff33',
    'spacelink': "#1805c5",
}

# Get unique servers and assign colors dynamically if not in predefined list
unique_servers = df['server'].unique()
for server in unique_servers:
    if server not in server_colors:
        # Generate a color for servers not in the predefined list
        import matplotlib.cm as cm
        import numpy as np
        color_idx = len(server_colors) % 10
        server_colors[server] = cm.tab10(color_idx)

# Create figure with 2x2 grid of subplots (bottom right will be empty)
fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# Create custom legend with two columns: one for shapes, one for colors
from matplotlib.lines import Line2D
legend_elements = []
# Add connection type markers
for conn_type, marker in connection_markers.items():
    legend_elements.append(Line2D([0], [0], marker=marker, color='gray',
                                  label=conn_type, markersize=8, linestyle='None',
                                  markeredgecolor='black', markeredgewidth=0.5))
# Add a separator
legend_elements.append(Line2D([0], [0], marker='', color='none', label=''))
# Add server colors
for server in unique_servers:
    legend_elements.append(Line2D([0], [0], marker='o', color=server_colors[server],
                                  label=server, markersize=8, linestyle='None',
                                  markeredgecolor='black', markeredgewidth=0.5))

# Plot 1: Throughput vs Ping Latency (top left)
# Each test contributes two points: one for download speed, one for upload speed
for server in unique_servers:
    for conn_type in ['single', 'multi']:
        subset = df[(df['server'] == server) & (df['connection_type'] == conn_type)]
        if len(subset) > 0:
            # Plot with download throughput
            axes[0, 0].scatter(subset['ookla_download_speed'],
                           subset['ping_latency'],
                           alpha=1,
                           color=server_colors[server],
                           marker=connection_markers[conn_type],
                           s=50,
                           edgecolors='black',
                           linewidths=0.5,
                           label=f'{server} - {conn_type}')
            # Plot with upload throughput
            axes[0, 0].scatter(subset['ookla_upload_speed'],
                           subset['ping_latency'],
                           alpha=1,
                           color=server_colors[server],
                           marker=connection_markers[conn_type],
                           s=50,
                           edgecolors='black',
                           linewidths=0.5)

axes[0, 0].set_title(f'Throughput vs Ping Latency ({server_label})',
                 fontsize=14, fontweight='bold')
axes[0, 0].set_xlabel('Ookla Reported Throughput (Mbps)', fontsize=12)
axes[0, 0].set_ylabel('Ping Latency (ms)', fontsize=12)
axes[0, 0].set_xlim(0, 50)
axes[0, 0].set_ylim(0, 400)
axes[0, 0].grid(True, alpha=0.3)

# Plot 2: Throughput vs Loaded Latency - Download (top right)
for server in unique_servers:
    for conn_type in ['single', 'multi']:
        subset = df[(df['server'] == server) & (df['connection_type'] == conn_type)]
        if len(subset) > 0:
            axes[0, 1].scatter(subset['ookla_download_speed'],
                           subset['download_latency'],
                           alpha=1,
                           color=server_colors[server],
                           marker=connection_markers[conn_type],
                           s=50,
                           edgecolors='black',
                           linewidths=0.5,
                           label=f'{server} - {conn_type}')

axes[0, 1].set_title(f'Throughput vs Loaded Latency - Download ({server_label})',
                 fontsize=14, fontweight='bold')
axes[0, 1].set_xlabel('Ookla Reported Throughput (Mbps)', fontsize=12)
axes[0, 1].set_ylabel('Loaded Latency (ms)', fontsize=12)
axes[0, 1].set_xlim(0, 50)
axes[0, 1].set_ylim(0, 400)
axes[0, 1].grid(True, alpha=0.3)

# Plot 3: Throughput vs Loaded Latency - Upload (bottom left)
for server in unique_servers:
    for conn_type in ['single', 'multi']:
        subset = df[(df['server'] == server) & (df['connection_type'] == conn_type)]
        if len(subset) > 0:
            axes[1, 0].scatter(subset['ookla_upload_speed'],
                           subset['upload_Latency'],
                           alpha=1,
                           color=server_colors[server],
                           marker=connection_markers[conn_type],
                           s=50,
                           edgecolors='black',
                           linewidths=0.5,
                           label=f'{server} - {conn_type}')

axes[1, 0].set_title(f'Throughput vs Loaded Latency - Upload ({server_label})',
                 fontsize=14, fontweight='bold')
axes[1, 0].set_xlabel('Ookla Reported Throughput (Mbps)', fontsize=12)
axes[1, 0].set_ylabel('Loaded Latency (ms)', fontsize=12)
axes[1, 0].set_xlim(0, 50)
axes[1, 0].set_ylim(0, 400)
axes[1, 0].grid(True, alpha=0.3)

# Hide the bottom right subplot and add the shared legend there
axes[1, 1].axis('off')
axes[1, 1].legend(handles=legend_elements, loc='center', fontsize=12, ncol=1,
                  frameon=True, title='Legend', title_fontsize=14)

plt.tight_layout()
filename = f'throughput_vs_latency_{args.server if args.server else "all_servers"}.png'
plt.savefig(filename, dpi=300, bbox_inches='tight')
plt.show()
