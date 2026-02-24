from pathlib import Path
import pandas as pd
import numpy as np
import json
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import argparse
from sklearn.cluster import KMeans
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import NearestNeighbors
import sys

from dimension_throughput_calc import throughput_calculation as tp_calc

def run_dbscan_driver(folder: str, generate_plot: bool, config_accumulator):
    print(f"\n ARTIFACT FILTERING WITH DBSCAN")
    df = process_bytecount(folder)
    print(df.head())

    num_total_points = len(df)
    num_artifact_points = df["artifact"].sum()
    num_points_remaining = num_total_points - num_artifact_points

    # Plot artifacts
    if generate_plot:
        plot_dbscan(folder, df)

    # print artifact data points
    print(f"\nDBSCAN Artifact Points:")
    print(df[df["artifact"]][["time", "delta_time", "throughput", "byte_transferred"]].head(10))

    # Filter out artifacts
    df_filtered = df[~df["artifact"]].copy()

    # Calculate time metrics before dropping columns
    if num_total_points > 0:
        total_time_ms = df['time'].astype(int).max() - df['time'].astype(int).min()
        filtered_time_ms = df_filtered['time'].astype(int).max() - df_filtered['time'].astype(int).min() if len(df_filtered) > 0 else 0
        time_removed_ms = total_time_ms - filtered_time_ms
        percent_time_filtered = (time_removed_ms / total_time_ms * 100) if total_time_ms > 0 else 0.0
    else:
        time_removed_ms = 0.0
        percent_time_filtered = 0.0

    # Add metrics to config_accumulator
    config_accumulator.add('num_artifact_points', int(num_artifact_points))
    config_accumulator.add('num_points_after_dbscan', int(num_points_remaining))
    config_accumulator.add('percent_artifact_points', float(num_artifact_points / num_total_points * 100) if num_total_points > 0 else 0.0)
    config_accumulator.add('time_removed_by_dbscan_ms', float(time_removed_ms))
    config_accumulator.add('percent_time_removed_by_dbscan', float(percent_time_filtered))

    # Turn it back to json - drop extra columns
    df_filtered = df_filtered.drop(columns=["artifact", "throughput", "delta_time"], errors="ignore")

    # Build JSON structure
    result = {
        int(row["time"]): [
            int(row["byte_transferred"]),
            int(row["flows"])
        ]
        for _, row in df_filtered.iterrows()
    }

    return result

def estimate_eps_pre_wall(X, dim=2):
    # Heuristic:
    minPts = 2 * dim
    k = minPts - 1
    # find the k-nn distance
    nbrs = NearestNeighbors(n_neighbors=k)
    nbrs.fit(X)
    distances, _ = nbrs.kneighbors(X)
    # sort the k-nn distances and find the slopes
    k_distances = np.sort(distances[:, -1])
    slopes = np.diff(k_distances)
    # find where slope increases sharply (knee point)
    ratio = slopes[1:] / (slopes[:-1] + 1e-8) # add this small amount to avoid division by zero
    knee_idx = np.argmax(ratio)
    # find the eps corresponding to the knee point
    eps = k_distances[knee_idx]
    print(f"Estimated eps: {eps:.4f}, minPts: {minPts}")
    return eps, minPts

def detect_artifacts_dbscan(df):
    """
    DBSCAN-based artifact detection in (time, byte_transferred) space.
    Noise points (label = -1) are considered artifacts.
    """
    X = df[["time", "throughput"]].values
    X = StandardScaler().fit_transform(X)
    eps, min_samples = estimate_eps_pre_wall(X, dim=2)
    plot_knn_distance(X, dim=2, eps=eps, title="DBSCAN k-NN Distance for Artifact Detection")
    labels = DBSCAN(eps=eps, min_samples=min_samples).fit_predict(X)

    # Treat the first point as non-artifact to avoid removing the initial measurement.
    artifact_mask = (labels == -1)
    if artifact_mask.size > 0:
        artifact_mask[0] = False

    n_artifacts = int(artifact_mask.sum())
    pct = (n_artifacts / len(df) * 100) if len(df) > 0 else 0.0
    print(f"artifact points detected: {n_artifacts} out of {len(df)}, percentage: {pct:.2f}%   ")
    return artifact_mask

def process_bytecount(folder: str):
    df = load_bytecount_json(folder)
    df = bytecount_to_throughput(df)
    # DBSCAN artifact detection
    df["artifact"] = detect_artifacts_dbscan(df)
    return df

def bytecount_to_throughput(df):
    df = df.copy()
    # delta_time = time difference between consecutive rows
    df["delta_time"] = df["time"].astype(int).diff().fillna(0)
    df["throughput"] = df["byte_transferred"] / (df["delta_time"] + 1e-6)  # avoid division by zero
    return df

# Load Json and build DataFrame

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



# ---------------------------
# Plotting
# ---------------------------

def plot_knn_distance(
    X,
    dim=2,
    eps=None,
    title=None,
    figsize=(7, 5)
):
    """
    Plot sorted k-NN distance curve for DBSCAN eps selection.

    Parameters
    ----------
    X : array-like, shape (n_samples, n_features)
    dim : intrinsic dimension (used for minPts = 2*dim)
    eps : optional float, eps to overlay
    title : optional str
    """

    minPts = 2 * dim
    k = minPts - 1

    nbrs = NearestNeighbors(n_neighbors=k)
    nbrs.fit(X)
    distances, _ = nbrs.kneighbors(X)

    k_distances = np.sort(distances[:, -1])

    plt.figure(figsize=figsize)
    plt.plot(k_distances, linewidth=2)
    plt.xlabel("Points sorted by distance")
    plt.ylabel(f"{k}-NN distance")
    plt.grid(True, alpha=0.3)

    if eps is not None:
        plt.axhline(eps, linestyle="--", linewidth=2, label=f"eps = {eps:.3f}")
        plt.legend()

    if title:
        plt.title(title)
    else:
        plt.title(f"{k}-NN distance plot (minPts={minPts})")

    plt.tight_layout()
    # this is not saved to file, just shown interactively
    # plt.show()


def plot_dbscan(folder, df):
    mask = df["artifact"]
    t0 = df["time"].iloc[0]
    time_normalized = pd.to_numeric(df["time"]) - int(t0)
    out = Path(folder) / "plot_images"
    out_file = out / "dbscan_artifacts.png"

    plt.figure(figsize=(12, 7))
    # convert throughput to bytes/ms for better scaling (multiply by 8/1000 = devide by 125)
    plt.scatter(time_normalized, df["throughput"]/125, s=20, c="black", alpha=0.6)
    plt.scatter(
        time_normalized[mask],
        df.loc[mask, "throughput"]/125,
        s=25,
        c="red",
        label="DBSCAN Artifact"
    )

    plt.title("DBSCAN Artifact Detection")
    plt.xlabel("Time")
    plt.ylabel("Throughput")
    plt.legend()
    plt.grid(alpha=0.3)

    out.mkdir(exist_ok=True)
    plt.savefig(out_file, dpi=300, bbox_inches="tight")
    plt.close()

