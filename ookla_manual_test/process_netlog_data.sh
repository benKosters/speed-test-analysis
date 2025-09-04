#!/bin/bash

# An automated script to generate the necessary files from raw Netlog data

# process_netlog.sh - Run url_filter.js and manual_netlog.js in succession
# Usage: ./process_netlog.sh <path/to/netlog/file>

# Check if a netlog file was provided
if [ $# -lt 1 ]; then
    echo "Error: Please provide the path to a netlog file."
    echo "Usage: $0 <path/to/netlog/file>"
    exit 1
fi

# Store the netlog file path
NETLOG_FILE="$1"

# Check if the netlog file exists
if [ ! -f "$NETLOG_FILE" ]; then
    echo "Error: The file '$NETLOG_FILE' does not exist."
    exit 1
fi

# Get directory of the netlog file
NETLOG_DIR=$(dirname "$NETLOG_FILE")

#------------------------------ Step 1: Run url_filter.js to extract URLs-----------------------
echo -e "\n=========Step 1: Extracting URLs with url_filter.js..."
#node /home/benk/cs390/speed-test-analysis/ookla_manual_test/url_filter.js "$NETLOG_FILE"
node ./url_filter.js "$NETLOG_FILE"

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

# -----------------Step 2: Run manual_netlog.js for download data -------------------------------
# Double check to make sure the download directory exists - the script should exit if there was an error previously
if [ -d "$DOWNLOAD_DIR" ] && [ -f "$DOWNLOAD_URLS_FILE" ]; then
    echo -e "\n==========Step 2: Processing download data with manual_netlog.js..."
    echo "Using URLs file: $DOWNLOAD_URLS_FILE"
    #node /home/benk/cs390/speed-test-analysis/ookla_manual_test/manual_netlog.js "$NETLOG_FILE" "$DOWNLOAD_URLS_FILE"
    node ./manual_netlog.js "$NETLOG_FILE" "$DOWNLOAD_URLS_FILE"
    if [ $? -ne 0 ]; then
        echo "Warning: manual_netlog.js failed for download data."
    else
        echo "Download data processed successfully."
    fi
else
    echo "Skipping download processing - no download directory or URLs file found."
fi

#---------------------------- Step 3: Run manual_netlog.js for upload data ---------------------------
if [ -d "$UPLOAD_DIR" ] && [ -f "$UPLOAD_URLS_FILE" ]; then
    echo -e "\n==========Step 3: Processing upload data with manual_netlog.js..."
    echo "Using URLs file: $UPLOAD_URLS_FILE"
    #node /home/benk/cs390/speed-test-analysis/ookla_manual_test/manual_netlog.js "$NETLOG_FILE" "$UPLOAD_URLS_FILE"
    node ./manual_netlog.js "$NETLOG_FILE" "$UPLOAD_URLS_FILE"
    if [ $? -ne 0 ]; then
        echo "Warning: manual_netlog.js failed for upload data."
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
        #python3 /home/benk/cs390/analysis_manual/latency/normalize_latency.py "$LATENCY_FILE"
        python3 ../latency/normalize_latency.py "$LATENCY_FILE"
    fi

    # Run the throughput calculation and plotting script
    #python3 /home/benk/cs390/speed-test-analysis/visualizations/calculate_plot_throughput.py "$DOWNLOAD_DIR" --save
    python3 ../visualizations/calculate_plot_throughput.py "$DOWNLOAD_DIR" --save
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
        #python3 /home/benk/cs390/analysis_manual/latency/normalize_latency.py "$LATENCY_FILE"
        python3 ../latency/normalize_latency.py "$LATENCY_FILE"
    fi

    # Run the throughput calculation and plotting script
    #python3 /home/benk/cs390/speed-test-analysis/visualizations/calculate_plot_throughput.py "$UPLOAD_DIR" --save
    python3 ../visualizations/calculate_plot_throughput.py "$UPLOAD_DIR" --save

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