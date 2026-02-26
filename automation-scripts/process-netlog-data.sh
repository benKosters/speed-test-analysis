#!/bin/bash

# An automated script to process netlog data and run analysis

show_help() {
    echo "Usage: ./process_netlog_data.sh <test_output_directory> [options]"
    echo ""
    echo "Required:"
    echo "  <test_directory>     Path to the test output directory"
    echo ""
    echo "Options:"
    echo "  -upload              Process only upload data"
    echo "  -download            Process only download data"
    echo "  --save               Save plots (passed to main.py)"
    echo "  --bin <n>            Bin size for aggregating data (passed to main.py)"
    echo "  --all-configs        Run all 16 configurations (passed to main.py)"
    echo "  -h, --help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./process_netlog_data.sh /path/to/test/directory"
    echo "  ./process_netlog_data.sh /path/to/test/directory -download --save"
    echo "  ./process_netlog_data.sh /path/to/test/directory --save --bin 5"
    echo "  ./process_netlog_data.sh /path/to/test/directory -upload --bin 10"
    echo "  ./process_netlog_data.sh /path/to/test/directory --all-configs"
    exit 0
}

# Parse command-line arguments
TEST_DIR=""
FILTER_MODE=""
SAVE_FLAG=""
BIN_FLAG=""
ALL_CONFIGS_FLAG=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        -upload|-download)
            if [ -n "$FILTER_MODE" ]; then
                echo "Error: Cannot specify both -upload and -download"
                exit 1
            fi
            FILTER_MODE="$1"
            shift
            ;;
        --save)
            SAVE_FLAG="--save"
            shift
            ;;
        --bin)
            if [ -z "$2" ] || ! [[ "$2" =~ ^[0-9]+$ ]]; then
                echo "Error: --bin requires a positive integer"
                exit 1
            fi
            BIN_FLAG="--bin $2"
            shift 2
            ;;
        --all-configs)
            ALL_CONFIGS_FLAG="--all-configs"
            shift
            ;;
        -h|--help)
            show_help
            ;;
        -*)
            echo "Error: Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
        *)
            if [ -z "$TEST_DIR" ]; then
                TEST_DIR="$1"
            else
                echo "Error: Multiple directories specified"
                exit 1
            fi
            shift
            ;;
    esac
done

# Validate test directory
if [ -z "$TEST_DIR" ]; then
    echo "Error: Please provide the path to the test output directory."
    echo "Use -h or --help for usage information"
    exit 1
fi

if [ ! -d "$TEST_DIR" ]; then
    echo "Error: The directory '$TEST_DIR' does not exist."
    exit 1
fi

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Set the netlog directory
NETLOG_DIR="$TEST_DIR"
DOWNLOAD_DIR="$NETLOG_DIR/download"
UPLOAD_DIR="$NETLOG_DIR/upload"

# Check if Node.js is installed
if ! command -v node >/dev/null 2>&1; then
    echo "Error: Node.js not installed. Please install Node.js to run netlog filtering."
    exit 1
fi

# Check if Python3 is installed
if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: Python3 not installed. Please install Python3 to run data analysis."
    exit 1
fi

#------------------------------ Step 1: Run netlog filtering -----------------------
echo -e "\n========= Step 1: Filtering netlog data ========="
echo "Test directory: $TEST_DIR"
if [ -n "$FILTER_MODE" ]; then
    echo "Filter mode: $FILTER_MODE"
fi

NETLOG_FILTER_SCRIPT="../ookla/netlog-filter/main.js"

if [ ! -f "$NETLOG_FILTER_SCRIPT" ]; then
    echo "Error: Netlog filter script not found at $NETLOG_FILTER_SCRIPT"
    exit 1
fi

# Run the netlog filter with appropriate flags
if [ -n "$FILTER_MODE" ]; then
    node "$NETLOG_FILTER_SCRIPT" "$TEST_DIR" "$FILTER_MODE"
else
    node "$NETLOG_FILTER_SCRIPT" "$TEST_DIR"
fi

if [ $? -ne 0 ]; then
    echo "Error: Netlog filtering failed."
    exit 1
fi
echo "Netlog filtering completed successfully."


#------------------------------ Step 2: Run data analysis ---------------------------
ANALYSIS_SCRIPT="../data-analysis/single-test-analysis/main.py"

if [ ! -f "$ANALYSIS_SCRIPT" ]; then
    echo "Error: Analysis script not found at $ANALYSIS_SCRIPT"
    exit 1
fi

# Process download data (if not in upload-only mode)
if [ "$FILTER_MODE" != "-upload" ]; then
    if [ -d "$DOWNLOAD_DIR" ] && [ -f "$DOWNLOAD_DIR/byte_time_list.json" ]; then
        echo -e "Processing download data"

        python3 "$ANALYSIS_SCRIPT" "$DOWNLOAD_DIR" $SAVE_FLAG $BIN_FLAG $ALL_CONFIGS_FLAG

        if [ $? -ne 0 ]; then
            echo "Warning: Download analysis failed."
        else
            echo "Download analysis completed successfully."
        fi
    else
        echo -e "Skipping download processing - no download data found"
    fi
fi

# Process upload data (if not in download-only mode)
if [ "$FILTER_MODE" != "-download" ]; then
    if [ -d "$UPLOAD_DIR" ] && [ -f "$UPLOAD_DIR/current_position_list.json" ]; then
        echo -e "Processing upload data."

        python3 "$ANALYSIS_SCRIPT" "$UPLOAD_DIR" $SAVE_FLAG $BIN_FLAG $ALL_CONFIGS_FLAG

        if [ $? -ne 0 ]; then
            echo "Warning: Upload analysis failed."
        else
            echo "Upload analysis completed successfully."
        fi
    else
        echo -e "Skipping upload processing - no upload data found."
    fi
fi

echo -e "\n=========================================="
echo "Processing complete!"
echo "=========================================="
exit 0