"""
This class is used for accumulating statistics throughout the pipeline execution. It provides a structured way to add, organize, and save statistics derived from the data analysis process.
"""
import os
import json
from typing import Any, Dict


class StatisticsAccumulator:
    """
    Accumulates statistics throughout the pipeline execution.

    Usage:
        stats = StatisticsAccumulator(base_path)
        stats.add('num_flows', 16)
        stats.add('throughput', {'mean': 450.2, 'median': 448.1})
        stats.add_bulk({'bytes_sent': 1000000, 'duration_sec': 10.5})
        stats.save_summary()
    """

    def __init__(self, base_path):
        """
        Initialize the statistics collector.

        Args:
            base_path: Base directory for saving statistics files
        """
        self.base_path = base_path
        self.summary_stats = {}  # Single-value and nested dict metrics
        self.detailed_data = {}  # Complex structures saved to separate files

    def add(self, key: str, value: Any, detailed: bool = False):
        """
        Add a single statistic.

        Args:
            key: Name of the statistic (e.g., 'num_flows', 'throughput.mean')
            value: The value (scalar, dict, list, etc.)
            detailed: If True, saves to separate file; if False, adds to summary
        """
        if detailed:
            self.detailed_data[key] = value
        else:
            # Support nested keys like 'throughput.mean'
            if '.' in key:
                self._add_nested(key, value)
            else:
                self.summary_stats[key] = value

    def add_bulk(self, stats_dict: Dict[str, Any], detailed: bool = False):
        """
        Add multiple statistics at once.

        Args:
            stats_dict: Dictionary of statistics to add
            detailed: If True, all stats go to separate files
        """
        for key, value in stats_dict.items():
            self.add(key, value, detailed=detailed)

    def add_phase(self, phase_name: str, stats_dict: Dict[str, Any]):
        """
        Add statistics from a specific pipeline phase.

        Args:
            phase_name: Name of the phase (e.g., 'normalization', 'throughput')
            stats_dict: Statistics from that phase
        """
        self.summary_stats[phase_name] = stats_dict

    def _add_nested(self, key: str, value: Any):
        """Add a nested statistic using dot notation (e.g., 'throughput.mean')"""
        parts = key.split('.')
        current = self.summary_stats
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value

    def get(self, key: str, default=None):
        """Retrieve a statistic by key (supports dot notation)"""
        if '.' in key:
            parts = key.split('.')
            current = self.summary_stats
            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return default
            return current
        return self.summary_stats.get(key, default)

    def save_summary(self, filename: str = "test_summary.json"):
        """
        Save summary statistics (scalars and simple structures) to JSON.

        Args:
            filename: Name of the summary file
        """
        filepath = os.path.join(self.base_path, filename)
        with open(filepath, 'w') as f:
            json.dump(self.summary_stats, f, indent=4)
        print(f"Saved summary statistics to: {filepath}")
        return filepath

    def save_detailed(self, detailed_dir: str = "detailed_data"):
        """
        Save detailed data structures to separate JSON files.

        Args:
            detailed_dir: Subdirectory for detailed data files
        """
        if not self.detailed_data:
            return []

        detail_path = os.path.join(self.base_path, detailed_dir)
        os.makedirs(detail_path, exist_ok=True)

        saved_files = []
        for key, value in self.detailed_data.items():
            filename = f"{key}.json"
            filepath = os.path.join(detail_path, filename)
            with open(filepath, 'w') as f:
                json.dump(value, f, indent=4)
            saved_files.append(filepath)
            print(f"✓ Saved detailed data to: {filepath}")

        return saved_files

    def append_to_csv(self, filename: str = "configs_data.csv"):
        """
        Append summary statistics as a single row to a CSV file.
        Creates the file with headers if it doesn't exist.
        Only works with flat dictionaries (no nested structures).

        Args:
            filename: Name of the CSV file

        Usage:
            config_stats = StatisticsAccumulator(base_path)
            config_stats.add('dbscan_filter', True)
            config_stats.add('bin_size_ms', 5)
            config_stats.add('mean_throughput_mbps', 542.3)
            config_stats.append_to_csv()  # Writes one row to CSV
        """
        import pandas as pd

        filepath = os.path.join(self.base_path, filename)

        # Flatten nested dicts if any exist
        flat_stats = self._flatten_dict(self.summary_stats)

        # Create or append to CSV
        if os.path.exists(filepath):
            df = pd.read_csv(filepath)
            df = pd.concat([df, pd.DataFrame([flat_stats])], ignore_index=True)
        else:
            df = pd.DataFrame([flat_stats])

        df.to_csv(filepath, index=False)
        print(f"Appended statistics to: {filepath}")
        return filepath

    def _flatten_dict(self, d: Dict, parent_key: str = '', sep: str = '_') -> Dict:
        """
        Flatten a nested dictionary into a single-level dictionary.

        Args:
            d: Dictionary to flatten
            parent_key: Key prefix for nested items
            sep: Separator between parent and child keys

        Returns:
            Flattened dictionary
        """
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    def save_all(self):
        """Save both summary and detailed statistics"""
        self.save_summary()
        self.save_detailed()

    def print_summary(self):
        """Print a human-readable summary of collected statistics"""
        print("\n" + "=" * 60)
        print("STATISTICS SUMMARY")
        print("=" * 60)
        self._print_dict(self.summary_stats, indent=0)
        print("=" * 60 + "\n")

    def _print_dict(self, d: Dict, indent: int = 0):
        """Recursively print nested dictionaries"""
        for key, value in d.items():
            if isinstance(value, dict):
                print("  " * indent + f"{key}:")
                self._print_dict(value, indent + 1)
            else:
                print("  " * indent + f"{key}: {value}")
