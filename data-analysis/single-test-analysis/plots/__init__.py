import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import high-level driver
from .plot_driver import run_plot_driver

# Import throughput plotting functions
from .throughput_plots import (
    plot_throughput_and_http_streams,
    plot_throughput_scatter_max_flows_only,
    plot_throughput_scatter_max_and_one_fewer_flows,
    plot_throughput_rema_separated_by_flows,
    plot_throughput_rema_separated_by_flows_socket_grouped,
    plot_aggregated_bytecount,
    plot_rema_per_http_stream
)

# Import sorted throughput and histogram plots
from .plot_sorted_throughput import (
    plot_sorted_throughput,
    plot_throughput_histogram_with_jumps
)

# Import plotting utilities
from .plotting_utilities import (
    ensure_plot_dir,
    save_figure
)

# Import heatmap functions
from .plot_heatmap_throughput import (
    load_byte_count as load_byte_count_heatmap,
    create_heatmap,
    create_stacked_area_heatmap
)

# Import socket throughput plots
from .plot_socket_throughput import (
    plot_throughput_separated_by_sockets
)

# Import bar chart functions
from .plot_bar_bytecount import (
    load_byte_count as load_byte_count_bar,
    create_bytecount_bar_chart
)

# Define what gets imported with "from plots import *"
__all__ = [
    # High-level driver
    'run_plot_driver',

    # Throughput plots
    'plot_throughput_and_http_streams',
    'plot_throughput_scatter_max_flows_only',
    'plot_throughput_scatter_max_and_one_fewer_flows',
    'plot_throughput_rema_separated_by_flows',
    'plot_throughput_rema_separated_by_flows_socket_grouped',
    'plot_aggregated_bytecount',
    'plot_rema_per_http_stream',

    # Sorted and histogram plots
    'plot_sorted_throughput',
    'plot_throughput_histogram_with_jumps',

    # Plotting utilities
    'ensure_plot_dir',
    'save_figure',

    # Heatmap plots
    'load_byte_count_heatmap',
    'create_heatmap',
    'create_stacked_area_heatmap',

    # Socket plots
    'plot_throughput_separated_by_sockets',

    # Bar chart plots
    'load_byte_count_bar',
    'create_bytecount_bar_chart',
]

# Module metadata
__version__ = '1.0.0'
__author__ = 'Ben Kosters'
