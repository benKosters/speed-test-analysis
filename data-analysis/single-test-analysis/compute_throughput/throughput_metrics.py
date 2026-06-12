import numpy as np


def compute_throughput_metrics(throughput_results, throughput_method):
    """
    Calculate throughput statistics from throughput results.

    Args:
        throughput_results: List of dicts with 'throughput' values, or empty list.
        throughput_method: The name of the model used for computing throughput

    Returns:
        dict: Dictionary containing all throughput metrics:
            - {throughput_method}_mean_throughput_mbps
            - {throughput_method}_median_throughput_mbps
            - {throughput_method}_std_throughput_mbps
            - {throughput_method}_min_throughput_mbps
            - {throughput_method}_max_throughput_mbps
            - {throughput_method}_95th_percentile_throughput_mbps
            - {throughput_method}_coefficient_of_variation
            - {throughput_method}_variance_throughput_mbps
            - {throughput_method}_num_throughput_bins
    """
    if throughput_results:
        throughputs = [point['throughput'] for point in throughput_results]
        mean_val = float(np.mean(throughputs))

        metrics = {
            f'{throughput_method}_mean_throughput_mbps': mean_val,
            f'{throughput_method}_median_throughput_mbps': float(np.median(throughputs)),
            f'{throughput_method}_std_throughput_mbps': float(np.std(throughputs)),
            f'{throughput_method}_min_throughput_mbps': float(np.min(throughputs)),
            f'{throughput_method}_max_throughput_mbps': float(np.max(throughputs)),
            f'{throughput_method}_95th_percentile_throughput_mbps': float(np.percentile(throughputs, 95)),
            f'{throughput_method}_coefficient_of_variation': float(np.std(throughputs) / mean_val) if mean_val > 0 else 0.0,
            f'{throughput_method}_variance_throughput_mbps': float(np.var(throughputs)),
            f'{throughput_method}_num_throughput_bins': len(throughput_results)
        }
    else:
        metrics = {
            f'{throughput_method}_mean_throughput_mbps': 0.0,
            f'{throughput_method}_median_throughput_mbps': 0.0,
            f'{throughput_method}_std_throughput_mbps': 0.0,
            f'{throughput_method}_min_throughput_mbps': 0.0,
            f'{throughput_method}_max_throughput_mbps': 0.0,
            f'{throughput_method}_95th_percentile_throughput_mbps': 0.0,
            f'{throughput_method}_coefficient_of_variation': 0.0,
            f'{throughput_method}_variance_throughput_mbps': 0.0,
            f'{throughput_method}_num_throughput_bins': 0
        }

    return metrics
