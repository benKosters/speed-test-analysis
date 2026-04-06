import numpy as np
import json
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import argparse
import pandas as pd
from pathlib import Path
import sys


def run_slowstart_driver(folder: str, stats_accumulator, config_accumulator, byte_count=None):
    print(f"\n SLOW START FILTERING")
    if byte_count is not None:
        # Use the provided byte_count dict (already filtered by DBSCAN)
        df = (
            pd.DataFrame.from_dict(
                byte_count,
                orient="index",
                columns=["byte_transferred", "flows"]
            )
            .reset_index()
            .rename(columns={"index": "time"})
        )
    else:
        df = load_bytecount_json(folder)
    df = bytecount_to_throughput(df)
    print(df.head())
    # Plot artifacts
    ss_threshold = detect_slow_start(df["time"], df["throughput"])
    plot_slowstart(folder, df, ss_threshold)
    ss_threshold = int(ss_threshold)

    # Calculate metrics
    ss_threshold_normalized = ss_threshold - int(df['time'].iloc[0])
    num_points_removed = len(df[pd.to_numeric(df['time']) < ss_threshold])
    percent_points_removed = num_points_removed / len(df) * 100

    # print slow start threshold
    print(f"\nSlow Start Threshold: {ss_threshold_normalized} ms")
    print(f"\nNumber of points that's removed by slow start filter: {num_points_removed} ")
    print(f"\nPercentage of points removed by slow start filter: {percent_points_removed:.2f}%")

    # Save to config accumulator
    config_accumulator.add("slow_start_threshold_ms", ss_threshold_normalized)
    config_accumulator.add("slow_start_points_removed", num_points_removed)
    config_accumulator.add("slow_start_percent_removed", percent_points_removed)

    # return only data that's not artifact
    df = df[pd.to_numeric(df["time"]) >= ss_threshold]
    # Turn it back to json.
    df = df.drop(columns=["throughput", "delta_time"], errors="ignore")
    # Build JSON structure
    result = {
        int(row["time"]): [
            int(row["byte_transferred"]),
            int(row["flows"])
        ]
        for _, row in df.iterrows()
    }
    return result


def plot_slowstart(folder, df, threshold):
    t0 = df["time"].iloc[0]
    threshold = pd.to_numeric(threshold) - int(t0)
    time_normalized = pd.to_numeric(df["time"]) - int(t0)
    out = Path(folder) / "plot_images"
    out_file = out / "slowstart.png"
    plt.figure(figsize=(10, 6))
    plt.plot(time_normalized, df["throughput"]/125, label="Throughput", color="blue")
    plt.axvline(x=threshold, color="red", linestyle="--", label="Slow Start Threshold")
    plt.xlabel("Time (ms)")
    plt.ylabel("Throughput (Mbps)")
    plt.title("Throughput Over Time with Slow Start Threshold")
    plt.legend()
    plt.grid()
    plt.tight_layout()
    out.mkdir(exist_ok=True)
    plt.savefig(out_file, dpi=300, bbox_inches="tight")
    plt.close()

def load_bytecount_json(folder: str):
    json_path = Path(folder) / "byte_count.json"
    if not json_path.exists():
        raise FileNotFoundError(f"No byte_count.json found in {folder}")

    with open(json_path, "r") as f:
        raw = json.load(f)     # original stays untouched

    # Build dataframe
    df = (
        pd.DataFrame.from_dict(
            raw,
            orient="index",
            columns=["byte_transferred", "flows"]
        )
        .reset_index()
        .rename(columns={"index": "time"})
    )
    return df


def bytecount_to_throughput(df):
    df = df.copy()
    # delta_time = time difference between consecutive rows
    df["delta_time"] = df["time"].astype(int).diff().fillna(0)
    df["throughput"] = df["byte_transferred"] / (df["delta_time"] + 1e-6)  # avoid division by zero
    return df

def detect_slow_start(timestamps, throughput,
                             growth_threshold=1.5,
                             consecutive=3,
                             min_samples=5):

    throughput = np.array(throughput)

    # Smooth lightly to reduce noise
    window = 5
    smoothed = np.convolve(throughput,
                           np.ones(window)/window,
                           mode='valid')

    growth_ratio = smoothed[1:] / smoothed[:-1]

    violation_count = 0

    for i in range(len(growth_ratio)):
        if i < min_samples:
            continue

        if growth_ratio[i] < growth_threshold:
            violation_count += 1
        else:
            violation_count = 0

        if violation_count >= consecutive:
            return timestamps[i + window]

    # No slow start detected
    return timestamps.iloc[0] if hasattr(timestamps, 'iloc') else timestamps[0]