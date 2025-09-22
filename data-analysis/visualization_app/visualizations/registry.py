"""
Registry module for visualizations

This module maintains a registry of all available visualizations and their metadata.
New visualizations should be registered here to be available in the GUI.
"""

def get_visualization_types():
    """Return a dictionary of available visualization types"""
    return {
        # Test visualizations (for single test analysis)
        "Throughput with HTTP Streams": {
            "function": "plot_throughput_with_streams",
            "description": "Plot throughput with HTTP streams as a Gantt chart below",
            "params": {
                "interval": {"type": "numeric", "default": 2, "label": "Interval (ms)"},
                "ymin": {"type": "numeric", "default": 20, "label": "Y-axis Min (Mbps)"},
                "ymax": {"type": "numeric", "default": 250, "label": "Y-axis Max (Mbps)"}
            },
            "min_tests": 1,
            "max_tests": 1,
            "category": "single_test"
        },
        "Throughput by Flow Count": {
            "function": "plot_throughput_by_flows",
            "description": "Plot throughput with points colored by the number of flows",
            "params": {
                "interval": {"type": "numeric", "default": 10, "label": "Interval (ms)"},
                "scatter": {"type": "boolean", "default": True, "label": "Show Scatter"},
                "start_time": {"type": "numeric", "default": 0, "label": "Start Time (s)"},
                "end_time": {"type": "numeric", "default": 15, "label": "End Time (s)"}
            },
            "min_tests": 1,
            "max_tests": 1,
            "category": "single_test"
        },
        "Latency Comparison": {
            "function": "plot_latency_comparison",
            "description": "Compare idle and loaded latency values",
            "params": {},
            "min_tests": 1,
            "max_tests": 1,
            "category": "single_test"
        },
        "Throughput Per-HTTP Stream": {
            "function": "plot_throughput_per_http_stream",
            "description": "Show individual HTTP stream data",
            "params": {},
            "min_tests": 1,
            "max_tests": 1,
            "category": "single_test"
        },

        # Comparison visualizations (for multiple tests)
        "Multi-Test Throughput Comparison": {
            "function": "plot_multi_test_throughput",
            "description": "Compare throughput across multiple tests",
            "params": {
                "interval": {"type": "numeric", "default": 10, "label": "Interval (ms)"}
            },
            "min_tests": 2,
            "max_tests": 10,
            "category": "comparison"
        },
        "Compare Throughput with HTTP Streams": {
            "function": "compare_throughput_and_streams",
            "description": "Compare throughput and HTTP streams from two tests side by side",
            "params": {
                "interval": {"type": "numeric", "default": 2, "label": "Interval (ms)"},
                "ymin": {"type": "numeric", "default": 20, "label": "Y-axis Min (Mbps)"},
                "ymax": {"type": "numeric", "default": 250, "label": "Y-axis Max (Mbps)"}
            },
            "min_tests": 2,
            "max_tests": 2,
            "category": "comparison"
        },

        # Metadata visualizations (for test metadata analysis)
        "Test Duration Comparison": {
            "function": "plot_test_duration_comparison",
            "description": "Compare upload and download test durations across different servers",
            "params": {
                "sort_by": {"type": "choice", "default": "server",
                           "choices": ["server", "upload", "download", "total"],
                           "label": "Sort By"}
            },
            "min_tests": 3,
            "max_tests": 20,
            "category": "metadata"
        }
    }