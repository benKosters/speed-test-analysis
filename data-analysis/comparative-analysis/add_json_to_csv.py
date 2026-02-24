import json
import csv
import sys
import os

"""
Usage <json_to_csv.py path/to/test_directory path/to/csv_file>
Starting with the shared data file, pull the relevant JSON data.
Next, move on to the download test directory, pulling the relevant JSON data
Finally, move on to the upload test directory, pulling the relevant JSON data

This should generate 2 rows in the CSV file: one for download, one for upload

"""
#given the test directory, look for the json file named speedtest_result.json
if(len(sys.argv) != 3):
    print("Usage: json_to_csv.py <test_directory> <output_csv_file>")
    sys.exit(1)

test_directory = sys.argv[1]
output_csv_file = sys.argv[2]

# Extract just the directory name from the full path
test_name = os.path.basename(test_directory.rstrip('/'))

speedtest_json_path = f"{test_directory}/speedtest_result.json"
with open(speedtest_json_path, 'r') as f:
    speedtest_data = json.load(f)

# Load download test data
download_http_stream_path = f"{test_directory}/download/http_stream_data.json"
with open(download_http_stream_path, 'r') as f:
    download_stream_data = json.load(f)

# Load upload test data
upload_http_stream_path = f"{test_directory}/upload/http_stream_data.json"
with open(upload_http_stream_path, 'r') as f:
    upload_stream_data = json.load(f)

# Load download test summary
download_summary_path = f"{test_directory}/download/test_summary.json"
with open(download_summary_path, 'r') as f:
    download_summary_data = json.load(f)

# Load upload test summary
upload_summary_path = f"{test_directory}/upload/test_summary.json"
with open(upload_summary_path, 'r') as f:
    upload_summary_data = json.load(f)

fieldnames = [
    'test_name', 'date', 'time', 'server', 'connection_type',
    'test_direction', 'ping_latency', 'loaded_latency', 'ookla_reported_throughput',
    'total_streams', 'total_sockets', 'mean_latency_between_streams_ms',
    'median_latency_between_streams_ms', 'min_latency_between_streams_ms',
    'max_latency_between_streams_ms', 'range_latency_between_streams_ms',
    'test_duration_ms', 'bin_size_ms', 'num_streams', 'num_timestamps',
    'total_raw_bytes', 'total_processed_bytes', 'list_duration_sec', 'count_duration_sec',
    'percent_byte_loss', 'data_selection_mode', 'points_selected', 'points_excluded',
    'impact_total_points', 'impact_total_bytes', 'impact_total_duration_ms',
    'impact_max_flow_points', 'impact_max_flow_bytes', 'impact_max_flow_duration_ms',
    'impact_percent_points_excluded_if_max_flows_only',
    'impact_percent_bytes_excluded_if_max_flows_only',
    'impact_percent_time_excluded_if_max_flows_only'
]

# Check if the file exists to determine if we need to write headers
file_exists = os.path.exists(output_csv_file)

with open(output_csv_file, 'a', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

    # Only write header if file didn't exist or is empty
    if not file_exists or os.path.getsize(output_csv_file) == 0:
        writer.writeheader()

    # Write download test row
    download_socket_stats = download_stream_data.get('socket_statistics', {})
    download_test_data = download_stream_data.get('test_data', {})
    download_data_selection = download_summary_data.get('data_selection', {})
    download_impact_metrics = download_data_selection.get('impact_metrics', {})

    writer.writerow({
        'test_name': test_name,
        'date': speedtest_data['date'],
        'time': speedtest_data['time'],
        'server': speedtest_data['server'],
        'connection_type': speedtest_data['connection_type'],
        'test_direction': 'download',
        'ping_latency': speedtest_data['ping_latency'],
        'loaded_latency': speedtest_data['download_latency'],
        'ookla_reported_throughput': speedtest_data['ookla_download_speed'],
        'total_streams': download_socket_stats.get('total_streams', ''),
        'total_sockets': download_socket_stats.get('total_sockets', ''),
        'mean_latency_between_streams_ms': download_socket_stats.get('mean_latency_between_streams_ms', ''),
        'median_latency_between_streams_ms': download_socket_stats.get('median_latency_between_streams_ms', ''),
        'min_latency_between_streams_ms': download_socket_stats.get('min_latency_between_streams_ms', ''),
        'max_latency_between_streams_ms': download_socket_stats.get('max_latency_between_streams_ms', ''),
        'range_latency_between_streams_ms': download_socket_stats.get('range_latency_between_streams_ms', ''),
        'test_duration_ms': download_test_data.get('test_duration_ms', ''),
        'bin_size_ms': download_summary_data.get('bin_size_ms', ''),
        'num_streams': download_summary_data.get('num_streams', ''),
        'num_timestamps': download_summary_data.get('num_timestamps', ''),
        'total_raw_bytes': download_summary_data.get('total_raw_bytes', ''),
        'total_processed_bytes': download_summary_data.get('total_processed_bytes', ''),
        'list_duration_sec': download_summary_data.get('list_duration_sec', ''),
        'count_duration_sec': download_summary_data.get('count_duration_sec', ''),
        'percent_byte_loss': download_summary_data.get('percent_byte_loss', ''),
        'data_selection_mode': download_data_selection.get('mode', ''),
        'points_selected': download_data_selection.get('points_selected', ''),
        'points_excluded': download_data_selection.get('points_excluded', ''),
        'impact_total_points': download_impact_metrics.get('total_points', ''),
        'impact_total_bytes': download_impact_metrics.get('total_bytes', ''),
        'impact_total_duration_ms': download_impact_metrics.get('total_duration_ms', ''),
        'impact_max_flow_points': download_impact_metrics.get('max_flow_points', ''),
        'impact_max_flow_bytes': download_impact_metrics.get('max_flow_bytes', ''),
        'impact_max_flow_duration_ms': download_impact_metrics.get('max_flow_duration_ms', ''),
        'impact_percent_points_excluded_if_max_flows_only': download_impact_metrics.get('percent_points_excluded_if_max_flows_only', ''),
        'impact_percent_bytes_excluded_if_max_flows_only': download_impact_metrics.get('percent_bytes_excluded_if_max_flows_only', ''),
        'impact_percent_time_excluded_if_max_flows_only': download_impact_metrics.get('percent_time_excluded_if_max_flows_only', '')
    })

    # Write upload test row
    upload_socket_stats = upload_stream_data.get('socket_statistics', {})
    upload_test_data = upload_stream_data.get('test_data', {})
    upload_data_selection = upload_summary_data.get('data_selection', {})
    upload_impact_metrics = upload_data_selection.get('impact_metrics', {})

    writer.writerow({
        'test_name': test_name,
        'date': speedtest_data['date'],
        'time': speedtest_data['time'],
        'server': speedtest_data['server'],
        'connection_type': speedtest_data['connection_type'],
        'test_direction': 'upload',
        'ping_latency': speedtest_data['ping_latency'],
        'loaded_latency': speedtest_data['upload_Latency'],
        'ookla_reported_throughput': speedtest_data['ookla_upload_speed'],
        'total_streams': upload_socket_stats.get('total_streams', ''),
        'total_sockets': upload_socket_stats.get('total_sockets', ''),
        'mean_latency_between_streams_ms': upload_socket_stats.get('mean_latency_between_streams_ms', ''),
        'median_latency_between_streams_ms': upload_socket_stats.get('median_latency_between_streams_ms', ''),
        'min_latency_between_streams_ms': upload_socket_stats.get('min_latency_between_streams_ms', ''),
        'max_latency_between_streams_ms': upload_socket_stats.get('max_latency_between_streams_ms', ''),
        'range_latency_between_streams_ms': upload_socket_stats.get('range_latency_between_streams_ms', ''),
        'test_duration_ms': upload_test_data.get('test_duration_ms', ''),
        'bin_size_ms': upload_summary_data.get('bin_size_ms', ''),
        'num_streams': upload_summary_data.get('num_streams', ''),
        'num_timestamps': upload_summary_data.get('num_timestamps', ''),
        'total_raw_bytes': upload_summary_data.get('total_raw_bytes', ''),
        'total_processed_bytes': upload_summary_data.get('total_processed_bytes', ''),
        'list_duration_sec': upload_summary_data.get('list_duration_sec', ''),
        'count_duration_sec': upload_summary_data.get('count_duration_sec', ''),
        'percent_byte_loss': upload_summary_data.get('percent_byte_loss', ''),
        'data_selection_mode': upload_data_selection.get('mode', ''),
        'points_selected': upload_data_selection.get('points_selected', ''),
        'points_excluded': upload_data_selection.get('points_excluded', ''),
        'impact_total_points': upload_impact_metrics.get('total_points', ''),
        'impact_total_bytes': upload_impact_metrics.get('total_bytes', ''),
        'impact_total_duration_ms': upload_impact_metrics.get('total_duration_ms', ''),
        'impact_max_flow_points': upload_impact_metrics.get('max_flow_points', ''),
        'impact_max_flow_bytes': upload_impact_metrics.get('max_flow_bytes', ''),
        'impact_max_flow_duration_ms': upload_impact_metrics.get('max_flow_duration_ms', ''),
        'impact_percent_points_excluded_if_max_flows_only': upload_impact_metrics.get('percent_points_excluded_if_max_flows_only', ''),
        'impact_percent_bytes_excluded_if_max_flows_only': upload_impact_metrics.get('percent_bytes_excluded_if_max_flows_only', ''),
        'impact_percent_time_excluded_if_max_flows_only': upload_impact_metrics.get('percent_time_excluded_if_max_flows_only', '')
    })




