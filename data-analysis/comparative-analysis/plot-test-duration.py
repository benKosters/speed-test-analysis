import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from collections import defaultdict
import argparse
import sys

def read_and_process_csv(file_path):
    """
    Read CSV file and process test duration data.
    Take rows at indices 1, 11, 21, etc. to get 10 samples per test type.
    """
    try:
        # Read the CSV file
        df = pd.read_csv(file_path)

        # Filter to get rows at indices 1, 11, 21, 31, etc.
        # This selects rows where (index - 1) % 10 == 0 and index > 0
        df_filtered = df[(df.index - 1) % 10 == 0].copy()

        print(f"Original rows: {len(df)}, Filtered rows: {len(df_filtered)}")
        print("Selected row indices:", df_filtered.index.tolist())

        # Group by server_location, multi_single_flow, and test_type to calculate means
        grouped_data = defaultdict(lambda: defaultdict(list))

        for _, row in df_filtered.iterrows():
            server = row['server_location']
            flow_type = row['multi_single_flow']  # 'single' or 'multi'
            test_type = row['test_type']  # 'download' or 'upload'
            duration = row['test_duration']  # in milliseconds

            # Create a key for the test configuration
            test_key = f"{server}_{flow_type}"
            grouped_data[test_key][test_type].append(duration)

        # Calculate means for each test configuration
        mean_durations = {}
        for test_key, test_data in grouped_data.items():
            mean_durations[test_key] = {}
            for test_type, durations in test_data.items():
                if durations:  # Check if list is not empty
                    mean_durations[test_key][test_type] = np.mean(durations)
                    print(f"{test_key} {test_type}: {len(durations)} samples, mean = {np.mean(durations):.1f}ms")

        return mean_durations

    except FileNotFoundError:
        print(f"Error: Could not find file {file_path}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        sys.exit(1)

def create_test_labels_and_data(mean_durations):
    """
    Create organized test labels and corresponding duration data for plotting.
    """
    test_names = []
    download_times = []
    upload_times = []

    # Sort the test configurations for consistent ordering
    sorted_tests = sorted(mean_durations.keys())

    for test_key in sorted_tests:
        # Parse the test key to create readable labels
        parts = test_key.split('_')
        if len(parts) >= 2:
            server = parts[0].capitalize()
            flow_type = parts[1].capitalize()

            # Create multi-line label
            label = f"{server}\n{flow_type} Flow"
            test_names.append(label)

            # Get download and upload times (default to 0 if missing)
            download_time = mean_durations[test_key].get('download', 0)
            upload_time = mean_durations[test_key].get('upload', 0)

            download_times.append(download_time)
            upload_times.append(upload_time)

    return test_names, download_times, upload_times

def plot_test_durations(file_path=None):
    """
    Create a grouped bar chart comparing upload and download durations
    across different speed tests, reading data from CSV file.
    """
    if file_path:
        # Read data from CSV
        mean_durations = read_and_process_csv(file_path)
        test_names, download_times, upload_times = create_test_labels_and_data(mean_durations)

        if not test_names:
            print("No test data found in CSV file.")
            return

    else:
        # Fallback to hard-coded data if no file provided
        print("No CSV file provided, using hard-coded data...")
        test_names = [
            "Michwave\nMultiflow",
            "Michwave\nSingle Flow",
            "Spacelink\nMultiflow",
            "Spacelink\nSingle Flow"
        ]
        # Convert to milliseconds for consistency with CSV data
        download_times = [14.982 * 1000, 15.022 * 1000, 14.794 * 1000, 14.825 * 1000]
        upload_times = [15.046 * 1000, 15.045 * 1000, 14.845 * 1000, 15.125 * 1000]

    # Set up the figure and axes
    fig, ax = plt.subplots(figsize=(14, 8))

    # Set width of bars and positions
    bar_width = 0.35
    indices = np.arange(len(test_names))

    # Create bars
    download_bars = ax.bar(
        indices - bar_width/2,
        download_times,
        bar_width,
        label='Download',
        color='skyblue'
    )
    upload_bars = ax.bar(
        indices + bar_width/2,
        upload_times,
        bar_width,
        label='Upload',
        color='lightcoral'
    )

    # Add labels, title and custom x-axis tick labels
    ax.set_xlabel('Speed Test Configuration', fontsize=12)
    ax.set_ylabel('Mean Duration (ms)', fontsize=12)
    ax.set_title('Mean Upload and Download Durations by Test Configuration', fontsize=14)
    ax.set_xticks(indices)
    ax.set_xticklabels(test_names)

    # Add exact time values above bars
    def add_labels(bars):
        for bar in bars:
            height = bar.get_height()
            if height > 0:  # Only add label if there's actual data
                ax.annotate(f'{height:.0f}',
                            xy=(bar.get_x() + bar.get_width() / 2, height),
                            xytext=(0, 3),  # 3 points vertical offset
                            textcoords="offset points",
                            ha='center', va='bottom',
                            fontsize=10)

    add_labels(download_bars)
    add_labels(upload_bars)

    # Add a horizontal grid for better readability
    ax.grid(axis='y', linestyle='--', alpha=0.3)

    # Add legend
    ax.legend()

    # Dynamically set y-axis range based on data
    if download_times and upload_times:
        min_time = min(min(download_times), min(upload_times))
        max_time = max(max(download_times), max(upload_times))
        margin = (max_time - min_time) * 0.1  # 10% margin
        ax.set_ylim(min_time - margin, max_time + margin)

    # Add a baseline at 15000ms if data is around that range
    if download_times and upload_times:
        avg_time = (np.mean(download_times) + np.mean(upload_times)) / 2
        if 14000 <= avg_time <= 16000:  # Only add baseline if data is in expected range
            ax.axhline(y=15000, color='red', linestyle='-', alpha=0.5, label='15s Baseline')
            ax.legend()

    # Adjust layout to make room for labels
    plt.tight_layout()

    # Show plot
    if file_path:
        output_file = file_path.replace('.csv', '_duration_comparison.png')
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Plot saved as: {output_file}")

    plt.show()

def main():
    """
    Main function to handle command line arguments and run the plotting function.
    """
    parser = argparse.ArgumentParser(description='Plot test duration comparison from CSV data')
    parser.add_argument('csv_file', nargs='?', help='Path to CSV file containing test data')

    args = parser.parse_args()

    if args.csv_file:
        print(f"Reading data from: {args.csv_file}")
        plot_test_durations(args.csv_file)
    else:
        print("Usage: python plot-test-duration.py <csv_file>")
        print("Or run without arguments to use hard-coded sample data")
        plot_test_durations()

if __name__ == "__main__":
    main()