#!/bin/bash

# An automated script to generate the necessary files from raw Netlog data

# process_netlog_data.sh - Process netlog data for both download and upload tests
# Usage: ./process_netlog_data.sh <test_output_directory>

# Check if a directory was provided
if [ $# -lt 1 ]; then
    echo "Error: Please provide the path to the test output directory."
    echo "Usage: $0 <test_output_directory>"
    exit 1
fi

# Store the test directory path
TEST_DIR="$1"

# Check if the test directory exists
if [ ! -d "$TEST_DIR" ]; then
    echo "Error: The directory '$TEST_DIR' does not exist."
    exit 1
fi

# Look for the netlog file in the test directory
NETLOG_FILE="$TEST_DIR/netlog.json"

# Check if the netlog file exists
if [ ! -f "$NETLOG_FILE" ]; then
    echo "Error: Netlog file not found at '$NETLOG_FILE'."
    exit 1
fi

# Set the netlog directory
NETLOG_DIR="$TEST_DIR"

#------------------------------ Step 1: Run url_filter.js to extract URLs-----------------------
echo -e "\n=========Step 1: Extracting URLs with url_filter.js..."

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
URL_FILTER_SCRIPT="${SCRIPT_DIR}/url_filter.js"

if [ ! -f "$URL_FILTER_SCRIPT" ]; then
    echo "Error: url_filter.js not found at $URL_FILTER_SCRIPT"
    exit 1
fi

node "$URL_FILTER_SCRIPT" "$NETLOG_FILE"

if [ $? -ne 0 ]; then
    echo "Error: url_filter.js failed."
    exit 1
fi
echo "URL extraction completed successfully."

# Check if download and upload directories were created
# Check if download and upload directories were created
DOWNLOAD_DIR="$NETLOG_DIR/download"
UPLOAD_DIR="$NETLOG_DIR/upload"
DOWNLOAD_URLS_FILE="$DOWNLOAD_DIR/download_urls.json"
UPLOAD_URLS_FILE="$UPLOAD_DIR/upload_urls.json"

# -----------------Step 2: Run filter-netlog-data.js for download data -------------------------------
# Define filter script path
FILTER_SCRIPT="${SCRIPT_DIR}/filter-netlog-data.js"

if [ ! -f "$FILTER_SCRIPT" ]; then
    echo "Error: filter-netlog-data.js not found at $FILTER_SCRIPT"
    exit 1
fi

# Double check to make sure the download directory exists - the script should exit if there was an error previously
if [ -d "$DOWNLOAD_DIR" ] && [ -f "$DOWNLOAD_URLS_FILE" ]; then
    echo -e "\n==========Step 2: Processing download data with filter-netlog-data.js..."
    echo "Using URLs file: $DOWNLOAD_URLS_FILE"
    node "$FILTER_SCRIPT" "$NETLOG_FILE" "$DOWNLOAD_URLS_FILE"
    if [ $? -ne 0 ]; then
        echo "Warning: filter-netlog-data.js failed for download data."
    else
        echo "Download data processed successfully."
    fi
else
    echo "Skipping download processing - no download directory or URLs file found."
fi

#---------------------------- Step 3: Run filter-netlog-data.js for upload data ---------------------------
if [ -d "$UPLOAD_DIR" ] && [ -f "$UPLOAD_URLS_FILE" ]; then
    echo -e "\n==========Step 3: Processing upload data with filter-netlog-data.js..."
    echo "Using URLs file: $UPLOAD_URLS_FILE"
    node "$FILTER_SCRIPT" "$NETLOG_FILE" "$UPLOAD_URLS_FILE"
    if [ $? -ne 0 ]; then
        echo "Warning: filter-netlog-data.js failed for upload data."
    else
        echo "Upload data processed successfully."
    fi
else
    echo "Skipping upload processing - no upload directory or URLs file found."
fi


#---------------------------- Step 4: Calculate and plot download throughput ---------------------------
if [ -d "$DOWNLOAD_DIR" ] && [ -f "$DOWNLOAD_DIR/byte_time_list.json" ]; then
    echo -e "\n==========Step 4: Calculating and plotting download throughput..."

    #Check if latency data needs normalization
    LATENCY_FILE="$DOWNLOAD_DIR/loaded_latency.json"
    NORMALIZED_LATENCY_FILE="$DOWNLOAD_DIR/normalized_latency.json"

    if [ -f "$LATENCY_FILE" ] && [ ! -f "$NORMALIZED_LATENCY_FILE" ]; then
        echo "Normalizing latency data for download..."
        LATENCY_SCRIPT="$(cd "$SCRIPT_DIR/../.." && pwd)/latency/normalize_latency.py"
        python3 "$LATENCY_SCRIPT" "$LATENCY_FILE"
    fi

    # Run the throughput calculation and plotting script
    THROUGHPUT_SCRIPT="$(cd "$SCRIPT_DIR/../.." && pwd)/data-analysis/exploratory/eda_driver.py"
    python3 "$THROUGHPUT_SCRIPT" "$DOWNLOAD_DIR" --save
    if [ $? -ne 0 ]; then
        echo "Warning: Throughput calculation/plotting failed for download data."
    else
        echo "Download throughput calculation and plotting completed successfully."
    fi
else
    echo "Skipping download throughput calculation - required files not found."
fi

#---------------------------- Step 5: Calculate and plot upload throughput ---------------------------
if [ -d "$UPLOAD_DIR" ] && [ -f "$UPLOAD_DIR/current_position_list.json" ]; then
    echo -e "\n==========Step 5: Calculating and plotting upload throughput..."

    # Check if latency data needs normalization
    LATENCY_FILE="$UPLOAD_DIR/loaded_latency.json"
    NORMALIZED_LATENCY_FILE="$UPLOAD_DIR/normalized_latency.json"

    if [ -f "$LATENCY_FILE" ] && [ ! -f "$NORMALIZED_LATENCY_FILE" ]; then
        echo "Normalizing latency data for upload..."
        LATENCY_SCRIPT="$(cd "$SCRIPT_DIR/../.." && pwd)/latency/normalize_latency.py"
        python3 "$LATENCY_SCRIPT" "$LATENCY_FILE"
    fi

    # Run the throughput calculation and plotting script
    THROUGHPUT_SCRIPT="$(cd "$SCRIPT_DIR/../.." && pwd)/data-analysis/exploratory/eda_driver.py"
    python3 "$THROUGHPUT_SCRIPT" "$UPLOAD_DIR" --save

    if [ $? -ne 0 ]; then
        echo "Warning: Throughput calculation/plotting failed for upload data."
    else
        echo "Upload throughput calculation and plotting completed successfully."
    fi
else
    echo "Skipping upload throughput calculation - required files not found."
fi


echo "Processing complete!"
exit 0