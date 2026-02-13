"""
Data Selection Dimension Module

This module handles the data selection phase of the pipeline, where
you can choose different strategies for which data points to include
in throughput calculations.

Selection Modes:
    - 'all': Include all data points regardless of flow count
    - 'max_flows_only': Only include points where all flows are contributing
"""

import sys
import os

# Add parent directories to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from .data_selection_driver import run_data_selection_driver

__all__ = [
    'run_data_selection_driver'
]

__version__ = '1.0.0'
__author__ = 'Ben Kosters'
