import pandas as pd
import matplotlib.pyplot as plt
import argparse
from datetime import datetime

# Parse command line arguments
parser = argparse.ArgumentParser(description='Plot throughput time series by server and connection type')
parser.add_argument('-i', '--input', type=str, required=False,
                    default='/home/benk/cs390/speed-test-analysis/data-analysis/automating-scripts/csvs/latency_data.csv',
                    help='Path to input CSV file')
args = parser.parse_args()

# Load your data
df = pd.read_csv(args.input)

df['time'] = pd.to_datetime(df['time'], format='%H:%M:%S')
df = df.sort_values(by='time')

# Define color mapping for servers (same as the other script)
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
        import matplotlib.cm as cm
        color_idx = len(server_colors) % 10
        server_colors[server] = cm.tab10(color_idx)

# Create figure with 2x2 grid of subplots
fig, axes = plt.subplots(2, 2, figsize=(18, 12))

# Plot 1: Upload Speed - Single Flow (top left)
df_single = df[df['connection_type'] == 'single']
for server in unique_servers:
    subset = df_single[df_single['server'] == server]
    if len(subset) > 0:
        axes[0, 0].plot(subset['time'], subset['ookla_upload_speed'],
                       marker='o', markersize=4, linewidth=2,
                       color=server_colors[server], label=server, alpha=0.8)

axes[0, 0].set_title('Upload Speed Over Time - Single Flow',
                    fontsize=14, fontweight='bold')
axes[0, 0].set_xlabel('Time', fontsize=12)
axes[0, 0].set_ylabel('Upload Speed (Mbps)', fontsize=12)
axes[0, 0].grid(True, alpha=0.3)
axes[0, 0].legend(fontsize=10)
axes[0, 0].tick_params(axis='x', rotation=45)

# Plot 2: Download Speed - Single Flow (top right)
for server in unique_servers:
    subset = df_single[df_single['server'] == server]
    if len(subset) > 0:
        axes[0, 1].plot(subset['time'], subset['ookla_download_speed'],
                       marker='o', markersize=4, linewidth=2,
                       color=server_colors[server], label=server, alpha=0.8)

axes[0, 1].set_title('Download Speed Over Time - Single Flow',
                    fontsize=14, fontweight='bold')
axes[0, 1].set_xlabel('Time', fontsize=12)
axes[0, 1].set_ylabel('Download Speed (Mbps)', fontsize=12)
axes[0, 1].grid(True, alpha=0.3)
axes[0, 1].legend(fontsize=10)
axes[0, 1].tick_params(axis='x', rotation=45)

# Plot 3: Upload Speed - Multi Flow (bottom left)
df_multi = df[df['connection_type'] == 'multi']
for server in unique_servers:
    subset = df_multi[df_multi['server'] == server]
    if len(subset) > 0:
        axes[1, 0].plot(subset['time'], subset['ookla_upload_speed'],
                       marker='s', markersize=4, linewidth=2,
                       color=server_colors[server], label=server, alpha=0.8)

axes[1, 0].set_title('Upload Speed Over Time - Multi Flow',
                    fontsize=14, fontweight='bold')
axes[1, 0].set_xlabel('Time', fontsize=12)
axes[1, 0].set_ylabel('Upload Speed (Mbps)', fontsize=12)
axes[1, 0].grid(True, alpha=0.3)
axes[1, 0].legend(fontsize=10)
axes[1, 0].tick_params(axis='x', rotation=45)

# Plot 4: Download Speed - Multi Flow (bottom right)
for server in unique_servers:
    subset = df_multi[df_multi['server'] == server]
    if len(subset) > 0:
        axes[1, 1].plot(subset['time'], subset['ookla_download_speed'],
                       marker='s', markersize=4, linewidth=2,
                       color=server_colors[server], label=server, alpha=0.8)

axes[1, 1].set_title('Download Speed Over Time - Multi Flow',
                    fontsize=14, fontweight='bold')
axes[1, 1].set_xlabel('Time', fontsize=12)
axes[1, 1].set_ylabel('Download Speed (Mbps)', fontsize=12)
axes[1, 1].grid(True, alpha=0.3)
axes[1, 1].legend(fontsize=10)
axes[1, 1].tick_params(axis='x', rotation=45)

plt.tight_layout()
# filename = 'throughput_timeseries.png'
# plt.savefig(filename, dpi=300, bbox_inches='tight')
# print(f"Plot saved as {filename}")
plt.show()
