#!/bin/bash

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Create results directory in the test-execution folder - this file should always exist, but the it is required for the output files
if [ ! -d "$SCRIPT_DIR/ookla-test-results" ]; then
    mkdir "$SCRIPT_DIR/ookla-test-results"
fi

# Default parameters
SERVER="Michwave"
CONNECTION="multi"
OUTPUT_DIR=""
PCAP_FLAG=false
DEV_MODE=false # dev mode will just place output in dev_tests/, rewriting any existing files - used when developing this tool
INTERFACE="eth0"
CPU_MONITOR=false

# Function to display help
show_help() {
    echo "Usage: ./execute-ookla-test.sh [options]"
    echo ""
    echo "Options:"
    echo "  -s, --server <name>      Server name to test against (default: Michwave)"
    echo "  -c, --connection <type>  Connection type: single or multi (default: multi)"
    echo "  -o, --output <dir>       Output directory for results (default: auto-generated)"
    echo "  -p, --pcap               Enable packet capture during test"
    echo "  -d, --dev                Enable development mode"
    echo "  -i, --interface <iface>  Network interface for packet capture (default: eth0)"
    echo "  -m, --cpu-monitor        Enable CPU monitoring with someta"
    echo "  -h, --help               Show this help message"
    echo ""
    echo "Example:"
    echo "  ./execute-ookla-test.sh -s Michwave -c single -p -i wlan0"
    exit 0
}

# Parse command-line options
while [[ $# -gt 0 ]]; do
    case "$1" in
        -s|--server)
            SERVER="$2"
            shift 2
            ;;
        -c|--connection)
            CONNECTION="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -p|--pcap)
            PCAP_FLAG=true
            shift
            ;;
        -d|--dev)
            DEV_MODE=true
            shift
            ;;
        -i|--interface)
            INTERFACE="$2"
            shift 2
            ;;
        -m|--cpu-monitor)
            CPU_MONITOR=true
            shift
            ;;
        -h|--help)
            show_help
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            ;;
    esac
done


# Handle output directory
if [ -z "$OUTPUT_DIR" ]; then
    # Create output directory if not specified
    if [ "$DEV_MODE" = true ]; then
        # For dev mode, use/create the dev_tests directory
        if [ ! -d "$SCRIPT_DIR/ookla-test-results/dev_tests" ]; then
            mkdir -p "$SCRIPT_DIR/ookla-test-results/dev_tests"
        else
            echo "Clearing old files in dev_tests directory."
            rm -rf "$SCRIPT_DIR/ookla-test-results/dev_tests/*" # Remove old files
        fi
        OUTPUT_DIR="$SCRIPT_DIR/ookla-test-results/dev_tests"
    else
        TIMESTAMP=$(date +"%Y-%m-%d_%H%M")
        # Create a standard directory name using server + connection type + timestamp --> this ensures a unique identifier for each test
        SERVER_FORMATTED=$(echo "$SERVER" | tr '[:upper:]' '[:lower:]' | tr ' ' '_')
        OUTPUT_DIR="$SCRIPT_DIR/ookla-test-results/${SERVER_FORMATTED}-${CONNECTION}-${TIMESTAMP}"
        mkdir -p "$OUTPUT_DIR"
    fi
else
    # If output directory is specified, create a subdirectory with the same formatting
    TIMESTAMP=$(date +"%Y-%m-%d_%H%M")
    SERVER_FORMATTED=$(echo "$SERVER" | tr '[:upper:]' '[:lower:]' | tr ' ' '_')
    OUTPUT_DIR="$OUTPUT_DIR/${SERVER_FORMATTED}-${CONNECTION}-${TIMESTAMP}"
    mkdir -p "$OUTPUT_DIR"
fi

# Display configuration
echo "---------------------------------------------"
echo "Test configuration:"
echo "  Server:      $SERVER"
echo "  Connection:  $CONNECTION"
echo "  Output dir:  $OUTPUT_DIR"
echo "  Packet cap:  $PCAP_FLAG"
echo "  CPU monitor: $CPU_MONITOR"
echo "  Dev mode:    $DEV_MODE"
if [ "$PCAP_FLAG" = true ]; then
    echo "  Interface:   $INTERFACE"
fi
echo "---------------------------------------------"


# If PCAP is enabled, create the pcap file and begin the dumpcap process
if [ "$PCAP_FLAG" = true ]; then
    PCAP_FILE="$OUTPUT_DIR/tcp_capture_${TIMESTAMP}.pcap"

    mkdir -p "$OUTPUT_DIR"
    chmod -R 777 "$OUTPUT_DIR"

    touch "$PCAP_FILE"
    chmod 666 "$PCAP_FILE"

    echo "Running pcap on $INTERFACE."

    if [ "$(id -u)" -eq 0 ]; then
        # Assume that the user is running as root
        dumpcap -i $INTERFACE -w "$PCAP_FILE" > "$OUTPUT_DIR/capture_output.log" 2>&1 &
        TSHARK_PID=$!
        echo "Running dumpcap as root"
    else
        # Try running with sudo
        sudo -n true 2>/dev/null
        if [ $? -eq 0 ]; then
            # Use dumpcap via the wireshart group permissions
            dumpcap -i $INTERFACE -w "$PCAP_FILE" > "$OUTPUT_DIR/capture_output.log" 2>&1 &
            TSHARK_PID=$!
            echo "Running dumpcap via wireshark group permissions"
        else
            echo "Cannot start dumpcap: requires elevated permissions"
        fi
    fi

    # Check if dumpcap started successfully
    sleep 2
    if ! ps -p $TSHARK_PID > /dev/null; then
        echo "Warning: dumpcap failed to start."
        if [ -f "$OUTPUT_DIR/capture_output.log" ]; then
            echo "dumpcap error: $(cat "$OUTPUT_DIR/capture_output.log")"
        fi
        PCAP_FLAG=false
    else
        echo "dumpcap process started with PID $TSHARK_PID"
        sleep 3
        if [ -f "$OUTPUT_DIR/capture_output.log" ]; then
            echo "dumpcap output: $(head -3 "$OUTPUT_DIR/capture_output.log")"
        fi
    fi
fi
# After pcap setup, begin the Ookla test
# Set up command to run the ookla-test.js - need to pass command line arguments into the node script
JS_COMMAND="node $SCRIPT_DIR/ookla-test.js"
JS_COMMAND="$JS_COMMAND -s \"$SERVER\""
JS_COMMAND="$JS_COMMAND -c \"$CONNECTION\""
JS_COMMAND="$JS_COMMAND -o \"$OUTPUT_DIR\""

# Use someta for CPU monitoring, if enabled
if [ "$CPU_MONITOR" = true ]; then
    SOMETA_BASENAME="$OUTPUT_DIR/cpu_metrics"
    echo "Beginning CPU monitoring."
    someta -M cpu -f "$SOMETA_BASENAME" -c "$JS_COMMAND"
    TEST_EXIT_CODE=$?

    # Rename the timestamped file to cpu_metrics.json
    # someta creates files like cpu_metrics_2026-02-05T20:38:58-05:00.json
    TIMESTAMPED_FILE=$(ls -t "$OUTPUT_DIR"/cpu_metrics_*.json 2>/dev/null | head -n 1)
    if [ -n "$TIMESTAMPED_FILE" ]; then
        mv "$TIMESTAMPED_FILE" "$OUTPUT_DIR/cpu_metrics.json"
        echo "Renamed CPU metrics file to cpu_metrics.json"
    fi
else
    # Run the Ookla test normally
    eval "$JS_COMMAND"
    TEST_EXIT_CODE=$?
fi

# Stop packet capture if pcap flag is enabled
if [ "$PCAP_FLAG" = true ]; then
    echo "Stopping packet capture..."
    if ps -p $TSHARK_PID > /dev/null; then
        kill $TSHARK_PID 2>/dev/null
        sleep 1
        echo "Packet capture completed."

        # Ensure the pcap file is accessible
        if [ -f "$PCAP_FILE" ]; then
            # sudo chmod 666 "$PCAP_FILE"
            # ls -la "$PCAP_FILE"
            echo "Packet capture saved to $PCAP_FILE ($(du -h "$PCAP_FILE" | cut -f1) bytes)"
        else
            echo "Warning: Packet capture file was not created"
            ls -la "$OUTPUT_DIR"
        fi
    else
        echo "Warning: tshark process was not running"
    fi
fi

echo "---------------------------------------------"
echo "Test completed with exit code: $TEST_EXIT_CODE"
echo "Results saved to: $OUTPUT_DIR"
echo "---------------------------------------------"
echo "OUTPUT_DIR=$OUTPUT_DIR"

exit $TEST_EXIT_CODE