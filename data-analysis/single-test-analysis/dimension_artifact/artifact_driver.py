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
from kneed import KneeLocator

import dimension_throughput_calc as tp_calc

def run_artifact_filter(config_accumulator, data, filter_type='throughput', artifact_filter=True, folderpath=None, plot_suffix="", throughput_method = ""):
    if filter_type == 'bytecount':
        # Filter based on raw bytecount data (old method)
        return run_dbscan_driver_bytecount(
            folder=folderpath,
            dbscan_option=artifact_filter,
            byte_count=data,
            config_accumulator=config_accumulator
        )

    elif filter_type == 'throughput':
        # Filter based on throughput - applies both DBSCAN and 1Gbps threshold filters
        return run_throughput_artifact_filter(
            config_accumulator=config_accumulator,
            throughput_results=data,
            artifact_filter=artifact_filter,
            plot_suffix=plot_suffix,
            folderpath=folderpath,
            throughput_method=throughput_method
        )
    else:
        print("Please specify which version of artifact filtering to use.")


def run_throughput_artifact_filter(config_accumulator, throughput_results, artifact_filter=True, plot_suffix="", folderpath=None, throughput_method=""):
    """
    On throughput data, computes mean throughput for DBSCAN only, 1Gbps threshold only,
    and both filters. Always returns results with BOTH filters applied (if artifact_filter=True).
    If artifact_filter=False, fills mean values with 0 and returns original data.
    """
    if not artifact_filter:
        # Fill in zeros for all artifact filtering metrics
        config_accumulator.add(f'{throughput_method}_mean_throughput_mbps_dbscan_only', 0.0)
        config_accumulator.add(f'{throughput_method}_mean_throughput_mbps_1gbps_filter_only', 0.0)
        config_accumulator.add(f'{throughput_method}_mean_throughput_mbps_dbscan_and_1gbps', 0.0)
        config_accumulator.add(f'{throughput_method}_num_artifact_points', 0)
        config_accumulator.add(f'{throughput_method}_num_dbscan_identified_points', 0)
        config_accumulator.add(f'{throughput_method}_num_1gbps_identified_points', 0)
        config_accumulator.add(f'{throughput_method}_num_points_after_filtering', len(throughput_results))
        config_accumulator.add(f'{throughput_method}_percent_artifact_points', 0.0)
        config_accumulator.add(f'{throughput_method}_time_removed_by_filtering_ms', 0.0)
        config_accumulator.add(f'{throughput_method}_percent_time_removed_by_filtering', 0.0)
        return throughput_results

    df = pd.DataFrame(throughput_results)
    suffix = plot_suffix
    threshold = 1000

    # Step 1: Run DBSCAN artifact detection
    print(f"\n Artifact Filter", "="*30)
    # if folderpath is None:
    #     plot_knn_distance(df[["time", "throughput"]].values, dim=2,
    #                     title="DBSCAN k-NN Distance for Artifact Detection")

    dbscan_artifacts = detect_artifacts_dbscan(df, folder=folderpath, suffix=suffix)
    df["dbscan_artifact"] = dbscan_artifacts

    print(f"\nDBSCAN Artifact Points: {dbscan_artifacts.sum()}")

    # Step 2: Run threshold filtering
    print(f"\n APPLYING {threshold} Mbps THRESHOLD FILTER")
    threshold_artifacts = df["throughput"] > threshold
    df["threshold_artifact"] = threshold_artifacts

    print(f"Threshold Artifact Points: {threshold_artifacts.sum()}")

    # Step 3: Compute mean throughput for the different filtering variations

    # DBSCAN only
    dbscan_only_data = df[~df["dbscan_artifact"]].to_dict('records')
    dbscan_only_throughputs = [point['throughput'] for point in dbscan_only_data]
    mean_dbscan_only = float(np.mean(dbscan_only_throughputs)) if len(dbscan_only_throughputs) > 0 else 0.0
    config_accumulator.add(f'{throughput_method}_mean_throughput_mbps_dbscan_only', mean_dbscan_only)

    # Threshold only
    threshold_only_data = df[~df["threshold_artifact"]].to_dict('records')
    threshold_only_throughputs = [point['throughput'] for point in threshold_only_data]
    mean_threshold_only = float(np.mean(threshold_only_throughputs)) if len(threshold_only_throughputs) > 0 else 0.0
    config_accumulator.add(f'{throughput_method}_mean_throughput_mbps_1gbps_filter_only', mean_threshold_only)

    # Both filters (this is what we'll return)
    both_filters_data = df[~(df["dbscan_artifact"] | df["threshold_artifact"])].to_dict('records')
    both_filters_throughputs = [point['throughput'] for point in both_filters_data]
    mean_both_filters = float(np.mean(both_filters_throughputs)) if len(both_filters_throughputs) > 0 else 0.0
    config_accumulator.add(f'{throughput_method}_mean_throughput_mbps_dbscan_and_1gbps', mean_both_filters)

    # Step 4: Calculate metrics for both filters applied
    df["artifact"] = df["dbscan_artifact"] | df["threshold_artifact"]

    num_total_points = len(df)
    num_total_artifacts = df["artifact"].sum()
    num_points_remaining = num_total_points - num_total_artifacts

    if num_total_points > 0 and 'time' in df.columns:
        df_with_delta = df.copy()
        df_with_delta['delta_time'] = df_with_delta['time'].astype(float).diff().fillna(0)

        total_time_ms = df_with_delta['delta_time'].sum() * 1000  # convert to ms
        time_removed_total = df_with_delta[df['artifact']]['delta_time'].sum() * 1000  # convert to ms
        percent_time_total = (time_removed_total / total_time_ms * 100) if total_time_ms > 0 else 0.0
    else:
        time_removed_total = 0.0
        percent_time_total = 0.0

    # Add combined metrics (for both filters)
    config_accumulator.add(f'{throughput_method}_num_dbscan_identified_points', int(dbscan_artifacts.sum()))
    config_accumulator.add(f'{throughput_method}_num_1gbps_identified_points', int(threshold_artifacts.sum()))
    config_accumulator.add(f'{throughput_method}_num_artifact_points', int(num_total_artifacts))
    config_accumulator.add(f'{throughput_method}_num_points_after_filtering', int(num_points_remaining))
    config_accumulator.add(f'{throughput_method}_percent_artifact_points',
                         float(num_total_artifacts / num_total_points * 100) if num_total_points > 0 else 0)
    config_accumulator.add(f'{throughput_method}_time_removed_by_filtering_ms', float(time_removed_total))
    config_accumulator.add(f'{throughput_method}_percent_time_removed_by_filtering', float(percent_time_total))

    # Return filtered data with BOTH filters applied
    filtered_df = df[~df["artifact"]]
    result = filtered_df.to_dict('records')

    print(f"\nTotal Artifact Points: {num_total_artifacts} out of {num_total_points}")
    print(f"Points Remaining: {num_points_remaining}")
    print(f"Time Removed: {time_removed_total:.2f}ms ({percent_time_total:.2f}%)")

    return result


def run_dbscan_driver_bytecount(folder: str, dbscan_option: bool, byte_count, config_accumulator):
    # If Artifact filtering is disabled, fill in 0 for metrics.
    # TODO: Update the logic here to this is cleaner/metrics are saved in one place
    if not dbscan_option:
        config_accumulator.add('num_artifact_points', 0)
        config_accumulator.add('num_points_after_dbscan', 0)
        config_accumulator.add('percent_artifact_points', 0.0)
        config_accumulator.add('time_removed_by_dbscan_ms', 0.0)
        config_accumulator.add('percent_time_removed_by_dbscan', 0.0)
        return byte_count

    print(f"\n ARTIFACT FILTERING WITH DBSCAN")
    df = process_bytecount(folder)
    print(df.head())

    num_total_points = len(df)
    num_artifact_points = df["artifact"].sum()
    num_points_remaining = num_total_points - num_artifact_points

    # print artifact data points
    print(f"\nDBSCAN Artifact Points:")
    print(df[df["artifact"]][["time", "delta_time", "throughput", "byte_transferred"]].head(10))

    # Filter out artifacts
    df_filtered = df[~df["artifact"]].copy()

    # Calculate time metrics before dropping columns
    if num_total_points > 0:
        total_time_ms = df['delta_time'].sum()  # Sum of all time intervals
        time_removed_ms = df[df['artifact']]['delta_time'].sum()  # Sum of artifact time intervals
        percent_time_filtered = (time_removed_ms / total_time_ms * 100) if total_time_ms > 0 else 0.0
    else:
        time_removed_ms = 0.0
        percent_time_filtered = 0.0

    # Add metrics to config_accumulator
    config_accumulator.add('num_artifact_points', int(num_artifact_points))
    config_accumulator.add('num_points_after_dbscan', int(num_points_remaining))
    config_accumulator.add('percent_artifact_points', float(num_artifact_points / num_total_points * 100) if num_total_points > 0 else 0)
    config_accumulator.add('time_removed_by_dbscan_ms', float(time_removed_ms) )
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

def run_dbscan_driver_throughput(config_accumulator, dbscan_option, throughput_results, bin_size, maxflow, folderpath=None, threshold=1000):
    """
    Apply DBSCAN artifact filtering to a list of dicts with 'time' and 'throughput'.
    Returns the filtered list without artifacts.
    """
    if not dbscan_option:
        # TODO: streamline how 0s are filled in the CSV when dbscan is disabled
        config_accumulator.add('num_artifact_points', 0)
        config_accumulator.add('num_points_after_dbscan', 0)
        config_accumulator.add('percent_artifact_points', 0.0)
        config_accumulator.add('time_removed_by_dbscan_ms', 0.0)
        config_accumulator.add('percent_time_removed_by_dbscan', 0.0)
        config_accumulator.add('mean_throughput_mbps_with_1gbps_threshold', 0.0)
        config_accumulator.add('median_throughput_mbps_with_1gbps_threshold', 0.0)
        config_accumulator.add('std_throughput_mbps_with_1gbps_threshold', 0.0)
        config_accumulator.add('min_throughput_mbps_with_1gbps_threshold', 0.0)
        config_accumulator.add('max_throughput_mbps_with_1gbps_threshold', 0.0)
        config_accumulator.add('95th_percentile_throughput_mbps_with_1gbps_threshold', 0.0)
        config_accumulator.add('coefficient_of_variation_with_1gbps_threshold', 0.0)
        config_accumulator.add('variance_throughput_mbps_with_1gbps_threshold', 0.0)
        config_accumulator.add('num_throughput_bins_with_1gbps_threshold', 0)

        return throughput_results

    print(f"\n ARTIFACT FILTERING WITH DBSCAN ON THROUGHPUT DATA")
    df = pd.DataFrame(throughput_results)
    # print(df.head())
    suffix = f"_{bin_size}_{maxflow}"
    # if folderpath is None:
    #     plot_knn_distance(df[["time", "throughput"]].values, dim=2, title="DBSCAN k-NN Distance for Artifact Detection")
    # DBSCAN artifact detection
    df["artifact"] = detect_artifacts_dbscan(df, folder=folderpath, suffix=suffix)

    # Calculate metrics for config_accumulator
    num_total_points = len(df)
    num_artifact_points = df["artifact"].sum()
    num_points_remaining = num_total_points - num_artifact_points

    # Calculate time metrics if time data is available
    if num_total_points > 0 and 'time' in df.columns:
        # Calculate delta_time (time intervals between measurements)
        df_with_delta = df.copy()
        df_with_delta['delta_time'] = df_with_delta['time'].astype(float).diff().fillna(0)

        total_time_ms = df_with_delta['delta_time'].sum()
        time_removed_ms = df_with_delta[df_with_delta['artifact']]['delta_time'].sum()
        percent_time_filtered = (time_removed_ms / total_time_ms * 100) if total_time_ms > 0 else 0.0
    else:
        time_removed_ms = 0.0
        percent_time_filtered = 0.0

    # Add metrics to config_accumulator
    config_accumulator.add('num_artifact_points', int(num_artifact_points))
    config_accumulator.add('num_points_after_dbscan', int(num_points_remaining))
    config_accumulator.add('percent_artifact_points', float(num_artifact_points / num_total_points * 100) if num_total_points > 0 else 0)
    config_accumulator.add('time_removed_by_dbscan_ms', float(time_removed_ms))
    config_accumulator.add('percent_time_removed_by_dbscan', float(percent_time_filtered))

    # Plot artifacts
    # plot_dbscan(folderpath, df, suffix)
    # Plot threshold
    # plot_threshold(config_accumulator, folderpath, throughput_results, df, threshold, suffix)
    # Print artifact data points
    print(f"\nDBSCAN Artifact Points:")
    print(df[df["artifact"]][["time", "throughput"]].head(10))
    # Return only data that's not artifact
    filtered_df = df[~df["artifact"]]
    # Convert back to list of dicts
    result = filtered_df.to_dict('records')
    return result

def estimate_eps_kneedle(X, dim=2):
    minPts = 2 * dim
    k = minPts - 1

    nbrs = NearestNeighbors(n_neighbors=k)
    nbrs.fit(X)
    distances, _ = nbrs.kneighbors(X)

    k_distances = np.sort(distances[:, -1])
    x = np.arange(len(k_distances))

    kneedle = KneeLocator(x, k_distances, curve='convex', direction='increasing')
    eps = k_distances[kneedle.knee]

    print(f"Estimated eps: {eps:.4f}, minPts: {minPts}")
    return eps, minPts

def detect_artifacts_dbscan(df, folder=None, suffix=""):
    """
    DBSCAN-based artifact detection in (time, byte_transferred) space.
    Noise points (label = -1) are considered artifacts.
    """
    X = df[["time", "throughput"]].values
    X = StandardScaler().fit_transform(X)
    eps, min_samples = estimate_eps_kneedle(X, dim=2)
    # plot_knn_distance(X, dim=2, eps=eps, title="DBSCAN k-NN Distance for Artifact Detection", folder=folder, suffix=suffix)
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
    df["artifact"] = detect_artifacts_dbscan(df, folder=None, suffix="")
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
    figsize=(7, 5),
    folder=None,
    suffix=""
):
    """
    Plot sorted k-NN distance curve for DBSCAN eps selection.

    Parameters
    ----------
    X : array-like, shape (n_samples, n_features)
    dim : intrinsic dimension (used for minPts = 2*dim)
    eps : optional float, eps to overlay
    title : optional str
    figsize : tuple
    folder : optional str, folder to save plot
    suffix : str, suffix for filename
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

    if folder is not None:
        out = Path(folder) / "plot_images"
        out.mkdir(exist_ok=True)
        out_file = out / f"knn{suffix}.png"
        plt.savefig(out_file, dpi=300, bbox_inches="tight")
        plt.close()
    else:
        plt.show()


def plot_dbscan(folder, df, suffix=""):
    mask = df["dbscan_artifact"]
    t0 = df["time"].iloc[0]
    time_normalized = pd.to_numeric(df["time"]) - int(t0)
    if folder is not None:
        out = Path(folder) / "plot_images"
        out_file = out / f"dbscan{suffix}.png"

    plt.figure(figsize=(12, 7))
    # convert throughput to bytes/ms for better scaling (multiply by 8/1000 = devide by 125)
    plt.scatter(time_normalized, df["throughput"], s=20, c="black", alpha=0.6)
    plt.scatter(
        time_normalized[mask],
        df.loc[mask, "throughput"],
        s=25,
        c="red",
        label="DBSCAN Artifact"
    )

    plt.title("DBSCAN Artifact Detection")
    plt.xlabel("Time")
    plt.ylabel("Throughput")
    plt.legend()
    plt.grid(alpha=0.3)

    if folder is not None:
        out.mkdir(exist_ok=True)
        plt.savefig(out_file, dpi=300, bbox_inches="tight")
        plt.close()
    else:
        plt.show()

def plot_threshold(config_accumulator, folder, throughput_results, df, threshold, suffix=""):
    """
    Only called by run_dbscan_throughput
    """
    t0 = df["time"].iloc[0]
    time_normalized = pd.to_numeric(df["time"]) - int(t0)
    y = pd.to_numeric(df["throughput"])  # Mbps
    #TODO: Fix parameter passing here - we compute throughput metrics on all points under 1Gbps threshold
    throughput_under_threshold_metrics = tp_calc.compute_throughput_metrics(df[df["throughput"] <= threshold].to_dict('records'))
    for metric_name, metric_value in throughput_under_threshold_metrics.items():
        config_accumulator.add(f"{metric_name}_with_1gbps_threshold", metric_value)

    threshold = float(threshold)  # convert to Mbps
    above_mask = y > threshold
    pct_above = 100.0 * above_mask.sum() / len(df) if len(df) > 0 else 0.0

    if folder is not None:
        out = Path(folder) / "plot_images"
        out_file = out / f"threshold{suffix}.png"

    plt.figure(figsize=(10, 6))
    plt.scatter(
        time_normalized[~above_mask],
        y[~above_mask],
        label="Below threshold",
        color="blue",
        alpha=0.6,
        s=30,
    )
    plt.scatter(
        time_normalized[above_mask],
        y[above_mask],
        label="Above threshold",
        color="red",
        alpha=0.7,
        s=30,
    )
    plt.axhline(y=threshold, color="black", linestyle="--", label=f"Threshold ({threshold:.2f} Mbps)")

    plt.xlabel("Time (ms)")
    plt.ylabel("Throughput (Mbps)")
    plt.title(f"Throughput Over Time with Y Threshold ({pct_above:.1f}% above)")
    plt.legend()
    plt.grid()
    plt.tight_layout()

    if folder is not None:
        out.mkdir(exist_ok=True)
        plt.savefig(out_file, dpi=300, bbox_inches="tight")
        plt.close()
    else:
        plt.show()
