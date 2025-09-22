"""
Visualizations Package for the Speed Test Visualization GUI

This package contains different visualization modules for the Speed Test Visualization GUI.
Each module contains related visualization functions.
"""

from .registry import get_visualization_types
from .test_visualizations import (
    plot_throughput_with_streams,
    plot_throughput_by_flows,
    plot_latency_comparison,
    plot_throughput_per_http_stream
)
from .comparison_visualizations import (
    plot_multi_test_throughput,
    compare_throughput_and_streams
)
from .metadata_visualizations import (
    plot_test_duration_comparison
)

# Create a unified Visualizations class that the rest of the application can use
class Visualizations:
    """Unified interface for all visualization functions"""

    @staticmethod
    def get_visualization_types():
        """Return a dictionary of available visualization types"""
        return get_visualization_types()

    # Import all visualization functions to the class namespace
    plot_throughput_with_streams = staticmethod(plot_throughput_with_streams)
    plot_throughput_by_flows = staticmethod(plot_throughput_by_flows)
    plot_latency_comparison = staticmethod(plot_latency_comparison)
    plot_throughput_per_http_stream = staticmethod(plot_throughput_per_http_stream)
    plot_multi_test_throughput = staticmethod(plot_multi_test_throughput)
    compare_throughput_and_streams = staticmethod(compare_throughput_and_streams)
    plot_test_duration_comparison = staticmethod(plot_test_duration_comparison)