import matplotlib.pyplot as plt
import numpy as np

def plot_test_durations():
    """
    Create a grouped bar chart comparing upload and download durations
    across different speed tests.
    """
    # Hard-coded test data (in seconds)
    test_names = [
        "Michwave\nMultiflow\nTest 1",
        "Michwave\nMultiflow\nTest 2",
        "Michwave\nSingle Flow\nTest 1",
        "Michwave\nSingle Flow\nTest 2",
        "Spacelink\nMultiflow\nTest 1",
        "Spacelink\nMultiflow\nTest 2",
        "Spacelink\nSingle Flow\nTest 1",
        "Spacelink\nSingle Flow\nTest 2"
    ]

    download_times = [14.982, 15.028, 15.022, 15.015, 14.794, 14.852, 14.825, 14.842]
    upload_times = [15.046, 14.980, 15.045, 15.040, 14.845, 15.099, 15.125, 15.107]

    # Convert to milliseconds for better readability in the graph
    download_times_ms = [t * 1000 for t in download_times]
    upload_times_ms = [t * 1000 for t in upload_times]

    # Set up the figure and axes
    fig, ax = plt.subplots(figsize=(14, 8))

    # Set width of bars and positions
    bar_width = 0.35
    indices = np.arange(len(test_names))

    # Create bars
    download_bars = ax.bar(
        indices - bar_width/2,
        download_times_ms,
        bar_width,
        label='Download',
        color='skyblue'
    )
    upload_bars = ax.bar(
        indices + bar_width/2,
        upload_times_ms,
        bar_width,
        label='Upload',
        color='lightcoral'
    )

    # Add labels, title and custom x-axis tick labels
    ax.set_xlabel('Speed Test', fontsize=12)
    ax.set_ylabel('Duration (ms)', fontsize=12)
    #ax.set_title('Upload and Download Durations by Test Case', fontsize=14)
    ax.set_xticks(indices)
    ax.set_xticklabels(test_names)

    # Add exact time values above bars
    def add_labels(bars):
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'{height:.1f}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom')

    add_labels(download_bars)
    add_labels(upload_bars)

    # Add a horizontal grid for better readability
    # ax.grid(axis='y', linestyle='--', alpha=0.7)

    # Add legend
    ax.legend()

    # Set y-axis range
    ax.set_ylim(14700, 15200)

    # Add a baseline at 15000ms
    ax.axhline(y=15000, color='red', linestyle='-', alpha=0.5)
    # Update legend to include the baseline
    ax.legend()

    # Add group separators and labels
    def add_group_separator(start_idx, label, color='gray'):
        # Draw a vertical line to separate groups
        ax.axvline(x=start_idx - 0.5, color=color, linestyle='--', alpha=0.5)

    # Add separators between different test groups
    # add_group_separator(2, "Michwave Multiflow")
    # add_group_separator(4, "Michwave Single Flow")
    # add_group_separator(6, "Spacelink Multiflow")

    # Adjust layout to make room for labels
    plt.tight_layout()

    # Show plot
    #plt.savefig('test_durations_comparison.png', dpi=300, bbox_inches='tight')
    plt.show()

if __name__ == "__main__":
    plot_test_durations()