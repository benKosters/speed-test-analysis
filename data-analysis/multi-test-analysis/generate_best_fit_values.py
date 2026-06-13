#!/usr/bin/env python3
"""
Script to generate best fit values and statistical comparisons for throughput data.
Computes statistical tests (e.g., KS test) between different configurations.
Usage: python generate_best_fit_values.py <target_dir> [--bin BIN_SIZE]

Due to sake of time, this script was mainly written with AI
# TODO: Refactor how the KS test values are being computed for different configurations.
    The different comparisons are currently hardcoded and are updated manually.
"""
import argparse
import sys
import os
import numpy as np
import pandas as pd
from scipy import stats

# Save the original working directory and script directory
original_cwd = os.getcwd()
script_dir = os.path.dirname(os.path.abspath(__file__))

# Change to single-test-analysis directory for proper imports
single_test_dir = os.path.abspath(os.path.join(script_dir, '../single-test-analysis'))
os.chdir(single_test_dir)
sys.path.insert(0, single_test_dir)

from main import run_single_test_analysis

# Set up argument parsing
parser = argparse.ArgumentParser(
    description='Generate best fit values and statistical comparisons for throughput data.'
)
parser.add_argument('target_dir', type=str,
                    help='Target directory containing both upload/ and download/ subdirectories')
parser.add_argument('--bin', type=int, default=1,
                    help='Bin size for aggregating data (default: 1ms)')
args = parser.parse_args()

print("="*60)
print("BEST FIT VALUES AND STATISTICAL ANALYSIS")
print("="*60)
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

print("\n" + "="*60)
print("Running Configurations")
print("="*60)

art = False
db = False

# Run single test analysis for each configuration
# upload_all_data_no_filter = run_single_test_analysis( base_path=upload_path, bin_size=args.bin,artifact_filter=art,dbscan_option=db,all_data=True,save_plots=False)
# upload_max_flow_no_filter = run_single_test_analysis( base_path=upload_path, bin_size=args.bin,artifact_filter=art,dbscan_option=db,all_data=False,save_plots=False)
# upload_all_data_cs_filter = run_single_test_analysis( base_path=upload_path, bin_size=args.bin,artifact_filter=True,dbscan_option=True,all_data=True,save_plots=False)
# upload_max_flow_cs_filter = run_single_test_analysis( base_path=upload_path, bin_size=args.bin,artifact_filter=True,dbscan_option=True,all_data=False,save_plots=False)
upload_all_data_cs_1g_filter = run_single_test_analysis( base_path=upload_path, bin_size=args.bin,artifact_filter=True,dbscan_option=False,all_data=True,save_plots=False)
upload_max_flow_cs_1g_filter = run_single_test_analysis( base_path=upload_path, bin_size=args.bin,artifact_filter=True,dbscan_option=False,all_data=False,save_plots=False)


#download_all_data_no_filter = run_single_test_analysis( base_path=download_path, bin_size=args.bin,artifact_filter=art,dbscan_option=db,all_data=True,save_plots=False)
#download_max_flow_no_filter = run_single_test_analysis( base_path=download_path, bin_size=args.bin,artifact_filter=art,dbscan_option=db,all_data=False,save_plots=False)
download_all_data_cs_filter = run_single_test_analysis( base_path=download_path, bin_size=args.bin,artifact_filter=True,dbscan_option=True,all_data=True,save_plots=False)
download_max_flow_cs_filter = run_single_test_analysis( base_path=download_path, bin_size=args.bin,artifact_filter=True,dbscan_option=True,all_data=False,save_plots=False)
download_all_data_cs_1g_filter = run_single_test_analysis( base_path=download_path, bin_size=args.bin,artifact_filter=True,dbscan_option=False,all_data=True,save_plots=False)
download_max_flow_cs_1g_filter = run_single_test_analysis( base_path =download_path, bin_size=args.bin,artifact_filter=True,dbscan_option=False,all_data=False,save_plots=False)


print("="*60)

# Extract throughput values from each configuration
# upload_all_throughput = upload_all_data_no_filter['strict_interval_throughput_results']
# upload_max_throughput = upload_max_flow_no_filter['strict_interval_throughput_results']
# upload_all_throughput_cs = upload_all_data_cs_filter['strict_interval_throughput_results']
# upload_max_throughput_cs = upload_max_flow_cs_filter['strict_interval_throughput_results']
upload_all_throughput_cs_1g = upload_all_data_cs_1g_filter['strict_interval_throughput_results']
upload_max_throughput_cs_1g = upload_max_flow_cs_1g_filter['strict_interval_throughput_results']


download_all_throughput = download_all_data_no_filter['strict_interval_throughput_results']
download_max_throughput = download_max_flow_no_filter['strict_interval_throughput_results']
download_all_throughput_cs = download_all_data_cs_filter['strict_interval_throughput_results']
download_max_throughput_cs = download_max_flow_cs_filter['strict_interval_throughput_results']
download_all_throughput_cs_1g = download_all_data_cs_1g_filter['strict_interval_throughput_results']
download_max_throughput_cs_1g = download_max_flow_cs_1g_filter['strict_interval_throughput_results']


print(f"\nData Summary:")
# print(f"  Upload All Data: {len(upload_all_throughput)} values")
# print(f"  Upload Maxflow: {len(upload_max_throughput)} values")
# print(f"  Download All Data: {len(download_all_throughput)} values")
# print(f"  Download Maxflow: {len(download_max_throughput)} values")
# print(f"  Upload All Data CS Filter: {len(upload_all_throughput_cs)} values")
# print(f"  Upload Maxflow CS Filter: {len(upload_max_throughput_cs)} values")
print(f"  Download All Data CS Filter: {len(download_all_throughput_cs)} values")
print(f"  Download Maxflow CS Filter: {len(download_max_throughput_cs)} values")
print(f"  Download All Data CS 1G Filter: {len(download_all_throughput_cs_1g)} values")
print(f"  Download Maxflow CS 1G Filter: {len(download_max_throughput_cs_1g)} values")


print("\n" + "="*60)
print("STATISTICAL TESTS")
print("="*60)

def extract_throughput_values(data):
    """
    Extract clean throughput values from various data structures.

    Args:
        data: Array/list of throughput values (can be list of dicts or list of numbers)

    Returns:
        numpy array of clean throughput values
    """
    throughput_values = []

    if isinstance(data, list) and len(data) > 0:
        if isinstance(data[0], dict):
            # Extract throughput values from list of dicts
            for item in data:
                if 'throughput' in item:
                    throughput_values.append(item['throughput'])
                elif 'throughput_mbps' in item:
                    throughput_values.append(item['throughput_mbps'])
                elif 'value' in item:
                    throughput_values.append(item['value'])
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
                val = float(x)
                if np.isfinite(val):
                    clean_data.append(val)
            except (ValueError, TypeError):
                continue

    return np.array(clean_data)

def compute_statistics(data1, data2, label1, label2):
    """
    Compute statistical tests comparing two datasets.

    Args:
        data1: First dataset
        data2: Second dataset
        label1: Label for first dataset
        label2: Label for second dataset
    """
    # Extract clean values
    values1 = extract_throughput_values(data1)
    values2 = extract_throughput_values(data2)

    if len(values1) == 0 or len(values2) == 0:
        print(f"\nWarning: Cannot compare {label1} vs {label2} - insufficient data")
        return

    print(f"\n{label1} vs {label2}:")
    print(f"  {label1}: n={len(values1)}, mean={np.mean(values1):.2f}, median={np.median(values1):.2f}")
    print(f"  {label2}: n={len(values2)}, mean={np.mean(values2):.2f}, median={np.median(values2):.2f}")

    # Kolmogorov-Smirnov test
    ks_stat, ks_p_value = stats.ks_2samp(values1, values2)
    print(f"  KS value={ks_stat:.6f}, p-value={ks_p_value}")

# Compare Upload: All Data vs Maxflow
# compute_statistics(upload_all_throughput,upload_max_throughput,"Upload All Data","Upload Maxflow")
# Compare Download: All Data vs Maxflow
# compute_statistics(download_all_throughput,download_max_throughput,"Download All Data","Download Maxflow")
# Compare Upload: All Data No Filter vs Upload: All Data CS Filter
#compute_statistics(upload_all_throughput,upload_all_throughput_cs,"Upload All Data No Filter","Upload All Data CS Filter")

#Compre Upload: Max Flow No Filter vs Upload: Max Flow CS Filter
#compute_statistics(upload_max_throughput,upload_max_throughput_cs,"Upload Max Flow No Filter","Upload Max Flow CS Filter")
#compute_statistics(upload_all_throughput,upload_all_throughput_cs_1g,"1Upload All Data No Filter","Upload All Data CS 1G Filter")
#compute_statistics(upload_max_throughput,upload_max_throughput_cs_1g,"2Upload Max Flow No Filter","Upload Max Flow CS 1G Filter")

compute_statistics(download_all_throughput_cs_1g,download_max_flow_cs_1g_filter,"Download All Data CS 1G Filter","Download Max Flow CS 1G Filter")
compute_statistics(upload_all_throughput_cs_1g,upload_max_throughput_cs_1g,"Upload All Data CS 1G Filter","Upload Max Flow CS 1G Filter")

print("\n" + "="*60)
print("ANALYSIS COMPLETE")
print("="*60)
