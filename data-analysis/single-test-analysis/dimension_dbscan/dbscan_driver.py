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

import throughput_calculation as tp_calc

# ---------------------------
# Annotate DataFrame
# ---------------------------
def annotate_bytecount(folder: str):
    df = load_bytecount_json(folder)
    # df["slow_start"] = filter_slow_start(df)
    df["artifact"]   = detect_artifacts_dbscan(df)
    
    # Remove first item where time == 0.0 and flows == 0
    mask = (df["time"] == 0.0) & (df["flows"] == 0)
    if mask.any():
        first_idx = mask.idxmax()
        df = df.drop(first_idx).reset_index(drop=True)
    
    df_out = df.set_index("time")
    df_path = Path(folder) / "annotated_bytecount.json"
    df_out.to_json(df_path, orient="index", indent=2)
    print(f"Annotated file saved to: {df_path}")
    return df


# ---------------------------
# Slow-start detection -- not used currently.
# ---------------------------

def filter_slow_start(df):
    df = df.copy()

    # windowed delivery rate (less noisy than instantaneous)
    w = 5
    rate = df["byte_transferred"].rolling(w).sum() / df["time"].diff(w)
    rate = rate.dropna()

    # find first point where variance drops sharply
    rolling_var = rate.rolling(5).var()

    # change point = first local minimum of variance
    cp_idx = rolling_var.idxmin()

    return df.index <= cp_idx

# ---------------------------
# Artifact detection
# ---------------------------

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
    DBSCAN-based artifact detection in (time, throughput) space.
    Noise points (label = -1) are considered artifacts.
    """
    X = df[["time", "throughput"]].values
    X = StandardScaler().fit_transform(X)
    eps, min_samples = estimate_eps_pre_wall(X, dim=2)
    plot_knn_distance(X, dim=2, eps=eps, title="DBSCAN k-NN Distance for Artifact Detection")
    labels = DBSCAN(eps=eps, min_samples=min_samples).fit_predict(X)

    return labels == -1

# CDF

def cdf(series):
    """Return sorted X values and their CDF (fraction ≤ x)."""
    data = np.sort(series.dropna().values)
    y = np.arange(1, len(data) + 1) / len(data)
    return data, y

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

    # sort by time
    df["time"] = df["time"].astype(float)
    df = df.sort_values("time").reset_index(drop=True)

    # normalize time to start at 0
    start_time = df["time"].iloc[0]
    df["time"] = df["time"] - start_time

    # compute delta time
    df["delta_time"] = df["time"].diff()

    # handle first row safely
    df.loc[0, "delta_time"] = 1.0

    # compute throughput
    df["throughput"] = df["byte_transferred"] / df["delta_time"]

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
    df = df.copy()
    mask = detect_artifacts_dbscan(df)

    out = Path(folder) / "plot_images"
    out_file = out / "dbscan_artifacts.png"

    plt.figure(figsize=(12, 7))
    # convert throughput to bytes/ms for better scaling (multiply by 8/1000 = devide by 125)
    plt.scatter(df["time"], df["throughput"]/125, s=20, c="black", alpha=0.6)
    plt.scatter(
        df.loc[mask, "time"],
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



def plot_filter_cdf(folder: str, df):
    """
    Create two CDF curves:
      (1) Unfiltered data (both slow_start=False AND artifact=False)
      (2) Full dataset (filtered data)
    """

    # ---- Build datasets ----
    unfiltered = df[(df["slow_start"] == False) & (df["artifact"] == False)]["throughput"]
    filtered = df[(df["slow_start"] != False) | (df["artifact"] != False)]["throughput"]
    #full = df["throughput"]

    # Sort them
    unfiltered_sorted = np.sort(unfiltered)
    filtered_sorted = np.sort(filtered)

    # Y-values for CDF
    unfiltered_cdf = np.arange(1, len(unfiltered_sorted)+1) / len(unfiltered_sorted)
    filtered_cdf = np.arange(1, len(filtered_sorted)+1) / len(filtered_sorted)

    # ---- Plot ----
    plt.figure(figsize=(10, 6))

    # full dataset first
    plt.plot(filtered_sorted, filtered_cdf, linewidth=2, alpha=0.8, label="CDF (Slow Start + Artifact Points)")

    # unfiltered dataset
    plt.plot(unfiltered_sorted, unfiltered_cdf, linewidth=2, alpha=0.8, label="CDF (No Slow Start / No Artifact)")
    title_prefix = Path(folder).parents[0].name
    plt.title(f"{title_prefix} — Filtered vs Unfiltered CDF", fontsize=16)
    plt.xlabel("Throughput", fontsize=14)
    plt.ylabel("CDF", fontsize=14)
    plt.grid(alpha=0.3)
    plt.legend(fontsize=12)

    plt.xlim(left=0)

    # ---- Save ----
    out = Path(folder) / "plot_images"
    out_file = out / "cdf_throughput_overlay.png"
    if out_file.exists():
        print(f"Skipping existing plot: {out_file}")
        return

    out.mkdir(exist_ok=True)

    plt.savefig(out_file, dpi=300, bbox_inches="tight")
    plt.close()

def plot_maxflow_cdf(folder: str, df):
    out = Path(folder) / "plot_images"
    out_file = out / "cdf_maxflow_vs_nonmaxflow.png"
    if out_file.exists():
        print(f"Skipping existing plot: {out_file}")
        return

    title_prefix = Path(folder).parents[0].name

    max_flow = df["flows"].max()

    max_flow_pts = df[df["flows"] == max_flow]["throughput"]
    non_max_flow_pts = df[df["flows"] != max_flow]["throughput"]

    plt.figure(figsize=(10, 6))

    # max flow CDF
    x_m, y_m = cdf(max_flow_pts)
    plt.plot(x_m, y_m, label=f"Flow = {max_flow} (Max)", linewidth=2)

    # non-max CDF
    if len(non_max_flow_pts) > 0:
        x_n, y_n = cdf(non_max_flow_pts)
        plt.plot(x_n, y_n, label="Non-max Flows", linewidth=2)

    plt.xlabel("Throughput")
    plt.ylabel("CDF")
    plt.title(f"{title_prefix} — Max Flow vs Non-Max Flow CDF")
    plt.grid(alpha=0.3)
    plt.legend()

    out.mkdir(exist_ok=True)
    plt.savefig(out_file, dpi=300, bbox_inches="tight")
    plt.close()



def plot_binned_with_artifacts(folder: str, df, bin_size, byte_transferred="byte_transferred", time_col="time", delta_col="delta_time", use_max=False):
    """
    Plot binned throughput data with artifacts highlighted in red.
    
    Parameters
    ----------
    folder : str
        Output folder path
    df : pd.DataFrame
        Input dataframe
    bin_size : int
        Bin size in ms (2 or 10)
    use_max : bool
        If True, use max throughput in bin. If False, use bytes/duration (default)
    """
    print(f"\n📊 Creating {bin_size}ms binned plot with artifacts...")
    
    # Debug: Check input data
    print(f"\n  INPUT DATA:")
    print(f"  Number of rows: {len(df)}")
    print(f"  Total bytes (sum): {df[byte_transferred].sum():.0f}")
    print(f"  Total delta_time (sum): {df[delta_col].sum():.0f}")
    print(f"  Time range: {df[time_col].min():.1f} to {df[time_col].max():.1f}")
    
    # Expand intervals to 1ms resolution
    expanded_rows = []
    for idx, row in df.iterrows():
        t_end = int(row[time_col])
        delta = int(row[delta_col])
        bytes_val = row[byte_transferred]
        t_start = t_end - delta
        
        # Distribute bytes uniformly across the interval
        bytes_per_ms = bytes_val / delta if delta > 0 else 0
        
        for t in range(t_start + 1, t_end + 1):
            expanded_rows.append({
                "time": t,
                byte_transferred: bytes_per_ms,
                "duration": 1,
                "throughput_1ms": bytes_per_ms  # Store 1ms throughput for max calculation
            })
    
    expanded_df = pd.DataFrame(expanded_rows)
    
    print(f"\n  EXPANDED DATA:")
    print(f"  Expanded to {len(expanded_df)} 1ms samples")
    print(f"  Total bytes in expanded: {expanded_df[byte_transferred].sum():.0f}")
    print(f"  Total duration in expanded: {expanded_df['duration'].sum():.0f} ms")
    
    # Assign bins
    expanded_df["bin"] = (expanded_df["time"] // bin_size) * bin_size
    
    # Aggregate
    if use_max:
        binned_df = (
            expanded_df
            .groupby("bin")
            .agg({
                byte_transferred: "sum",
                "duration": "sum",
                "throughput_1ms": "max"  # Take max 1ms throughput in the bin
            })
            .reset_index()
            .rename(columns={"bin": "time", "throughput_1ms": "throughput"})
        )
    else:
        binned_df = (
            expanded_df
            .groupby("bin")
            .agg({
                byte_transferred: "sum",
                "duration": "sum"
            })
            .reset_index()
            .rename(columns={"bin": "time"})
        )
        # Calculate throughput for each bin (bytes/duration)
        binned_df["throughput"] = binned_df[byte_transferred] / binned_df["duration"]
    
    print(f"\n  BINNED DATA ({bin_size}ms, {'MAX' if use_max else 'AVG'} method):")
    print(f"  After binning: {len(binned_df)} bins")
    print(f"  Total bytes in binned: {binned_df[byte_transferred].sum():.0f}")
    print(f"  Total duration in binned: {binned_df['duration'].sum():.0f} ms")
    
    print(f"\n  THROUGHPUT CALCULATIONS (BEFORE FILTERING):")
    # Convert throughput from bytes/ms to Magabits per second (Mbps) for better interpretability (1 byte/ms = 1/125 Mbps)
    print(f"  Min throughput: {binned_df['throughput'].min():.2f} bytes/ms = {binned_df['throughput'].min()/125:.2f} Mbps")
    print(f"  Max throughput: {binned_df['throughput'].max():.2f} bytes/ms = {binned_df['throughput'].max()/125:.2f} Mbps")
    print(f"  Mean throughput: {binned_df['throughput'].mean():.2f} bytes/ms = {binned_df['throughput'].mean()/125:.2f} Mbps")
    print(f"  Overall throughput: {binned_df[byte_transferred].sum() / binned_df['duration'].sum():.2f} bytes/ms = {binned_df[byte_transferred].sum() / binned_df['duration'].sum() / 125:.2f} Mbps")
    
    # Detect artifacts on binned data
    artifacts = detect_artifacts_dbscan(binned_df)
    
    # Filter out artifacts
    filtered_binned_df = binned_df[~artifacts].copy()
    
    print(f"\n  ARTIFACT DETECTION:")
    print(f"  Artifacts detected: {artifacts.sum()}")
    print(f"  Bins after filtering: {len(filtered_binned_df)}")
    
    print(f"\n  THROUGHPUT CALCULATIONS (AFTER FILTERING):")
    if len(filtered_binned_df) > 0:
        # Convert throughput from bytes/ms to Magabits per second (Mbps) for better interpretability (1 byte/ms = 1/125 Mbps)
        print(f"  Min throughput: {filtered_binned_df['throughput'].min():.2f} bytes/ms = {filtered_binned_df['throughput'].min()/125:.2f} Mbps")
        print(f"  Max throughput: {filtered_binned_df['throughput'].max():.2f} bytes/ms = {filtered_binned_df['throughput'].max()/125:.2f} Mbps")
        print(f"  Mean throughput: {filtered_binned_df['throughput'].mean():.2f} bytes/ms = {filtered_binned_df['throughput'].mean()/125:.2f} Mbps")
        print(f"  Overall throughput: {filtered_binned_df[byte_transferred].sum() / filtered_binned_df['duration'].sum():.2f} bytes/ms = {filtered_binned_df[byte_transferred].sum() / filtered_binned_df['duration'].sum() / 125:.2f} Mbps")
    else:
        print(f"  WARNING: No data remaining after filtering!")
    
    # Create plot
    plt.figure(figsize=(12, 7))
    
    # Plot non-artifact bins in black
    non_artifact_df = binned_df[~artifacts]
    plt.bar(
        non_artifact_df["time"],
        # Convert throughput from bytes/ms to Magabits per second (Mbps) for better interpretability (1 byte/ms = 1/125 Mbps)
        non_artifact_df["throughput"] / 125,
        width=bin_size,
        align="edge",
        alpha=0.8,
        color="black",
        label="Normal Throughput"
    )
    
    # Plot artifact bins in red
    artifact_df = binned_df[artifacts]
    if len(artifact_df) > 0:
        plt.bar(
            artifact_df["time"],
            # Convert throughput from bytes/ms to Magabits per second (Mbps) for better interpretability (1 byte/ms = 1/125 Mbps)
            artifact_df["throughput"] / 125,
            width=bin_size,
            align="edge",
            alpha=0.8,
            color="red",
            label="DBSCAN Artifact"
        )
    
    method_str = " (Max)" if use_max else ""
    plt.title(f"Throughput with {bin_size}ms Binning{method_str} - Artifacts Highlighted", fontsize=16)
    plt.xlabel("Time (ms)", fontsize=14)
    plt.ylabel("Throughput (bytes/ms)", fontsize=14)
    plt.legend(fontsize=12)
    plt.grid(alpha=0.3)
    plt.xlim(left=0)
    plt.ylim(bottom=0)
    
    # Save plot
    out = Path(folder) / "plot_images"
    out.mkdir(exist_ok=True)
    method_suffix = "_max" if use_max else ""
    out_file = out / f"throughput_{bin_size}ms_binning{method_suffix}_artifacts.png"
    
    plt.savefig(out_file, dpi=300, bbox_inches="tight")
    plt.close()
    
    print(f"\n  OUTPUT:")
    print(f"  Saved: {out_file}")
    print(f"  Total bins: {len(binned_df)}")
    print(f"  Artifact bins: {artifacts.sum()}")
    print(f"  Normal bins: {(~artifacts).sum()}")
    
    # Return the filtered throughput for summary
    if len(filtered_binned_df) > 0:
        # Convert throughput from bytes/ms to Magabits per second (Mbps) for better interpretability (1 byte/ms = 1/125 Mbps)
        filtered_throughput_mbps = filtered_binned_df[byte_transferred].sum() / filtered_binned_df['duration'].sum() / 125
    else:
        filtered_throughput_mbps = 0
    
    return filtered_throughput_mbps


# ---------------------------
# main()
# ---------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Analyze byte_count.json and highlight slow-start + artifacts."
    )
    parser.add_argument(
        "folder",
        type=str,
        help="Folder containing byte_count.json"
    )

    args = parser.parse_args()

    print(f"\n📁 Loading data from: {args.folder}")

    df = annotate_bytecount(args.folder)
    
    # 1ms binning plot
    plot_binned_with_artifacts(folder=args.folder, df=df, bin_size=1)

    # 2ms binning plot
    plot_binned_with_artifacts(folder=args.folder, df=df, bin_size=2)

    # 5ms binning plot
    plot_binned_with_artifacts(folder=args.folder, df=df, bin_size=5)
    
    # 10ms binning plot
    plot_binned_with_artifacts(folder=args.folder, df=df, bin_size=10)

    print("\n🔍 Annotated DataFrame preview:")
    print(df.head())

    parent = Path(args.folder).parent.name

    # Only run when this is a **multi** test, not a **single** test
    if "multi" in parent:
        print("\n📈 Generating Max Flow vs Non-Max Flow CDF plot...")
        plot_maxflow_cdf(args.folder, df)
    else:
        print(f"Skipping CDF for single-flow folder: {parent}")
   
    print("\n✨ Done.")



# Run main() only if executed directly
if __name__ == "__main__":
    main()
