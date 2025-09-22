"""
Metadata Visualizations Module

This module contains visualization functions for analyzing test metadata
across multiple tests, such as test duration, server differences, etc.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import os
import json
import re

def plot_test_duration_comparison(selected_tests, params):
    """
    Compare upload and download test durations across different servers

    This visualization analyzes test metadata to compare how long
    upload and download tests take across different servers.
    """
    if len(selected_tests) < 3:
        return None

    sort_by = params.get("sort_by", "server")

    # Extract test durations and metadata
    test_data = []
    for test_name, test_info in selected_tests.items():
        data = test_info["data"]
        test_dir = test_info["path"]

        # Extract server information from test name or directory
        server_match = re.search(r'server-([a-zA-Z0-9_\-]+)', test_name)
        if server_match:
            server = server_match.group(1)
        else:
            server = "Unknown"

        # Extract test type (upload/download)
        test_type = data["test_type"]

        # Calculate test duration from begin_time and end_time
        if "begin_time" in data and "end_time" in data:
            duration = (data["end_time"] - data["begin_time"]) / 1000  # Convert to seconds
        else:
            # If we don't have begin/end times, check if we have source_times
            if "source_times" in data and data["source_times"]:
                # Calculate duration from min/max times in source_times
                all_times = []
                for info in data["source_times"].values():
                    all_times.extend(info["times"])
                duration = (max(all_times) - min(all_times)) / 1000
            else:
                duration = 0

        # Add to our dataset
        test_data.append({
            "test_name": test_name,
            "server": server,
            "test_type": test_type,
            "duration": duration
        })

    # Convert to DataFrame for easier manipulation
    df = pd.DataFrame(test_data)

    # Create a pivot table to compare upload vs download by server
    pivot_df = df.pivot_table(
        index="server",
        columns="test_type",
        values="duration",
        aggfunc="mean"
    ).reset_index()

    # Handle missing columns by adding with zeros
    if "upload" not in pivot_df.columns:
        pivot_df["upload"] = 0
    if "download" not in pivot_df.columns:
        pivot_df["download"] = 0

    # Calculate total duration
    pivot_df["total"] = pivot_df["upload"] + pivot_df["download"]

    # Sort based on the selected parameter
    if sort_by in ["upload", "download", "total"]:
        pivot_df = pivot_df.sort_values(by=sort_by)
    # Default is to sort by server name

    # Create a figure
    fig = Figure(figsize=(12, 8))
    ax = fig.add_subplot(1, 1, 1)

    # Set up bar positions
    servers = pivot_df["server"].tolist()
    x = np.arange(len(servers))
    width = 0.35

    # Plot bars
    ax.bar(x - width/2, pivot_df["upload"], width, label="Upload", color="blue", alpha=0.7)
    ax.bar(x + width/2, pivot_df["download"], width, label="Download", color="red", alpha=0.7)

    # Add labels and customize
    ax.set_xlabel("Server")
    ax.set_ylabel("Duration (seconds)")
    ax.set_title("Test Duration Comparison by Server")
    ax.set_xticks(x)
    ax.set_xticklabels(servers, rotation=45, ha="right")
    ax.legend()

    # Add data labels
    for i, v in enumerate(pivot_df["upload"]):
        ax.text(i - width/2, v + 0.1, f"{v:.1f}s", ha="center", va="bottom", fontsize=9)
    for i, v in enumerate(pivot_df["download"]):
        ax.text(i + width/2, v + 0.1, f"{v:.1f}s", ha="center", va="bottom", fontsize=9)

    # Add total durations as text
    for i, (_, row) in enumerate(pivot_df.iterrows()):
        ax.text(i, max(row["upload"], row["download"]) + 1.5,
                f"Total: {row['total']:.1f}s", ha="center", va="bottom", fontsize=10)

    # Adjust layout
    fig.tight_layout()

    return fig