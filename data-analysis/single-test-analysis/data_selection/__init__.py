"""
This module handles the data selection phase of the pipeline, where
you can choose different strategies for which data points to include
in throughput calculations.

We can select either all data points, or only those that where all flows are active.
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
