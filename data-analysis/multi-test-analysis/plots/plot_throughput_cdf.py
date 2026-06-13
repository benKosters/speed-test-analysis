"""
#TODO: Update
"""

import argparse
import sys
import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

# Save the original working directory and script directory
original_cwd = os.getcwd()
script_dir = os.path.dirname(os.path.abspath(__file__))

# Change to single-test-analysis directory for proper imports
single_test_dir = os.path.abspath(os.path.join(script_dir, '../../single-test-analysis'))
os.chdir(single_test_dir)
sys.path.insert(0, single_test_dir)

from main import run_single_test_analysis

# Set up argument parsing
parser = argparse.ArgumentParser(description='Plot CDF of throughput values across upload and download tests.')
parser.add_argument('target_dir', type=str, help='Target directory containing both upload/ and download/ subdirectories')
parser.add_argument('--bin', type=int, default=1, help='Bin size for aggregating data (default: 1ms)')
parser.add_argument('--save', action='store_true', help='Save plot to plot_images directory')
args = parser.parse_args()

print(f"Bin size: {args.bin}ms")

# Convert target directory to absolute path before changing working directory
target_dir_abs = os.path.abspath(args.target_dir)

# Construct paths to upload and download directories (using absolute paths)
upload_path = os.path.join(target_dir_abs, "upload")
download_path = os.path.join(target_dir_abs, "download")

# Verify that both directories exist
if not os.path.exists(upload_path):
    raise FileNotFoundError(f"Upload directory not found: {upload_path}")
if not os.path.exists(download_path):
    raise FileNotFoundError(f"Download directory not found: {download_path}")

print("Running Configurations")
print("="*60)

# Turn off interactive mode to prevent accidental plot displays
plt.ioff()

art = False
db = False

# Configuration 1: Upload with specified bin size, no artifact filter, all data
upload_all_data_no_filter = run_single_test_analysis(base_path=upload_path,bin_size=args.bin, artifact_filter=art, dbscan_option=db, all_data=True,save_plots=False)
upload_max_flow_no_filter = run_single_test_analysis(base_path=upload_path,bin_size=args.bin, artifact_filter=art, dbscan_option=db, all_data=False,save_plots=False)
# upload_all_data_cs_only = run_single_test_analysis(base_path=upload_path,bin_size=args.bin, artifact_filter=True, dbscan_option=True, all_data=True,save_plots=False)
# upload_max_flow_cs_only = run_single_test_analysis(base_path=upload_path,bin_size=args.bin, artifact_filter=True, dbscan_option=True, all_data=False,save_plots=False)
download_all_data_no_filter = run_single_test_analysis(base_path=download_path,bin_size=args.bin,artifact_filter=art, dbscan_option=db, all_data=True,save_plots=False)
download_max_flow_no_filter = run_single_test_analysis(base_path=download_path,bin_size=args.bin, artifact_filter=art, dbscan_option=db, all_data=False, save_plots=False)

# ks_stat, p_value = stats.ks_2samp(download_all_data_no_filter, download_max_flow_no_filter)
# print("ks stat:", ks_stat)
# print("p value:", p_value)

print("="*60)

# Extract throughput values from each configuration
# The 'strict_interval_throughput_results' is a list/array of throughput values
upload1_throughput = upload_all_data_no_filter['strict_interval_throughput_results']
upload2_throughput = upload_max_flow_no_filter['strict_interval_throughput_results']
# upload3_throughput = upload_all_data_cs_only['strict_interval_throughput_results']
# upload4_throughput = upload_max_flow_cs_only['strict_interval_throughput_results']
download1_throughput = download_all_data_no_filter['strict_interval_throughput_results']
download2_throughput = download_max_flow_no_filter['strict_interval_throughput_results']

# Debug: Check data type
print(f"\nData type check:")
print(f"  Upload 1 type: {type(upload1_throughput)}")
if len(upload1_throughput) > 0:
    print(f"  First element type: {type(upload1_throughput[0])}")
    print(f"  First element: {upload1_throughput[0]}")
    if isinstance(upload1_throughput[0], dict):
        print(f"  Dict keys: {upload1_throughput[0].keys()}")

print(f"\nUpload Config 1: {len(upload1_throughput)} throughput values")
print(f"Upload Config 2: {len(upload2_throughput)} throughput values")
#print(f"Download Config 1: {len(download1_throughput)} throughput values")
# print(f"Download Config 2: {len(download2_throughput)} throughput values")

print("\n" + "="*60)
print("\n" + "="*60)
print("Generating CDF Plot")
print("="*60)

# Close any existing plots
plt.close('all')

def plot_cdf(data, label, color, linestyle='-'):
    """
    Plot the CDF for a given dataset.

    Args:
        data: Array/list of throughput values (can be dict with 'throughput' key, list of dicts, or list of numbers)
        label: Label for the plot legend
        color: Color for the line
        linestyle: Line style (default: solid)
    """
    # Handle different data structures
    throughput_values = []

    if isinstance(data, dict):
        # If data is a dict, try to extract throughput values
        if 'throughput' in data:
            throughput_values = data['throughput']
        else:
            print(f"Warning: Data for {label} is a dict but has no 'throughput' key. Keys: {data.keys()}")
            return
    elif isinstance(data, list) and len(data) > 0:
        # Check if it's a list of dictionaries
        if isinstance(data[0], dict):
            # Extract throughput values from list of dicts
            # Try common key names
            for item in data:
                if 'throughput' in item:
                    throughput_values.append(item['throughput'])
                elif 'throughput_mbps' in item:
                    throughput_values.append(item['throughput_mbps'])
                elif 'value' in item:
                    throughput_values.append(item['value'])
                else:
                    # If dict doesn't have expected keys, maybe the whole dict is the value
                    print(f"Warning: Dict item keys: {item.keys()}")
        else:
            # It's a simple list of numbers
            throughput_values = data
    else:
        throughput_values = data

    # Convert to list first to handle various input types
    if hasattr(throughput_values, 'tolist'):
        throughput_values = throughput_values.tolist()

    # Filter out None values and non-numeric values
    clean_data = []
    for x in throughput_values:
        if x is not None:
            try:
                # Try to convert to float
                val = float(x)
                # Check if it's a valid number (not NaN or inf)
                if np.isfinite(val):
                    clean_data.append(val)
            except (ValueError, TypeError):
                # Skip non-numeric values
                continue

    if len(clean_data) == 0:
        print(f"Warning: No valid data for {label}")
        print(f"  Original data type: {type(data)}")
        print(f"  Throughput values type: {type(throughput_values)}")
        print(f"  Throughput values length: {len(throughput_values) if hasattr(throughput_values, '__len__') else 'N/A'}")
        return

    # Convert to numpy array
    data_array = np.array(clean_data)

    # Sort the data
    sorted_data = np.sort(data_array)

    # Calculate the CDF values (proportion of data points <= each value)
    y = np.arange(1, len(sorted_data) + 1) / len(sorted_data)

    # Plot the CDF
    plt.plot(sorted_data, y, label=label, color=color, linestyle=linestyle, linewidth=2)

    # Print some statistics
    print(f"\n{label}:")
    print(f"  Count: {len(data_array)} values")
    print(f"  Mean: {np.mean(data_array):.2f} Mbps")
    print(f"  Median: {np.median(data_array):.2f} Mbps")
    print(f"  Min: {np.min(data_array):.2f} Mbps")
    print(f"  Max: {np.max(data_array):.2f} Mbps")

# Create the plot
plt.figure(figsize=(12, 8))

# Plot each configuration
plot_cdf(upload1_throughput, 'Upload - All Data NF', 'blue', '-')
plot_cdf(upload2_throughput, 'Upload - Maxflow NF', 'cornflowerblue', '--')
# plot_cdf(upload3_throughput, 'Upload - All Data CS', 'red', '-')
# plot_cdf(upload4_throughput, 'Upload - Maxflow CS', 'lightcoral', '--')
plot_cdf(download1_throughput, 'Download - All Data', 'red', '-')
plot_cdf(download2_throughput, 'Download - Maxflow', 'lightcoral', '--')

# Customize the plot
#plt.title("ALL/MAX_CS-1G")
plt.xlabel('Throughput (Mbps)', fontsize=30)
plt.ylabel('CDF', fontsize=30)
plt.legend(loc='best', fontsize=30)
plt.tick_params(axis='both', labelsize=30)
plt.grid(True, alpha=0.3)
plt.xlim(left=0, right = 4000)
plt.ylim([0, 1])

# Add horizontal line at median
plt.axhline(y=0.5, color='gray', linestyle=':', alpha=0.5, linewidth=1)

# Tight layout for better spacing
plt.tight_layout()

# Save or show the plot
if args.save:
    # Create plots directory in the target directory if it doesn't exist
    plot_dir = os.path.join(target_dir_abs, 'plots')
    print(f"\nSaving plot to directory: {plot_dir}")
    os.makedirs(plot_dir, exist_ok=True)

    prefix = ""
    if art and db:
        prefix += "cs-1g_"
    elif db and not art:
        prefix += "cs_"
    else:
        prefix += ""

    # Generate filename
    test_name = os.path.basename(target_dir_abs.rstrip('/'))
    filename = f'{prefix}throughput_cdf_{test_name}_bin{args.bin}ms.png'
    filepath = os.path.join(plot_dir, filename)

    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    print(f"Plot saved to: {filepath}")
else:
    print("\nDisplaying plot...")
    plt.show()

print("\nCDF plotting complete!")
