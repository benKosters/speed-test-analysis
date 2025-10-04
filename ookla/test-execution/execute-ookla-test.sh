#!/bin/bash

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Create results directory in the test-execution folder
if [ ! -d "$SCRIPT_DIR/ookla-test-results" ]; then
    mkdir "$SCRIPT_DIR/ookla-test-results"
fi

# Default values
SERVER="Michwave"
CONNECTION="multi"
OUTPUT_DIR=""
PCAP_FLAG=false
DEV_MODE=false
INTERFACE="eth0"

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
        # For dev mode, use/create dev_tests directory
        if [ ! -d "$SCRIPT_DIR/ookla-test-results/dev_tests" ]; then
            mkdir -p "$SCRIPT_DIR/ookla-test-results/dev_tests"
        else
            echo "Clearing old files in dev_tests directory."
            rm -rf "$SCRIPT_DIR/ookla-test-results/dev_tests/*" # Remove old files
        fi
        OUTPUT_DIR="$SCRIPT_DIR/ookla-test-results/dev_tests"
    else
        # Generate timestamp for standard mode
        TIMESTAMP=$(date +"%Y-%m-%d_%H%M")
        # Create a directory with server, connection type, and timestamp
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
echo "  Dev mode:    $DEV_MODE"
if [ "$PCAP_FLAG" = true ]; then
    echo "  Interface:   $INTERFACE"
fi
echo "---------------------------------------------"


# Set up file path for pcap file if pcap flag is enabled
if [ "$PCAP_FLAG" = true ]; then
    PCAP_FILE="$OUTPUT_DIR/tcp_capture.pcap"

    # Create output directory with proper permissions
    mkdir -p "$OUTPUT_DIR"
    chmod -R 777 "$OUTPUT_DIR"

    # Pre-create and set permissions on the pcap file
    touch "$PCAP_FILE"
    chmod 666 "$PCAP_FILE"

    echo "Running pcap on $INTERFACE."

    # Use a more reliable approach for running tshark
    if [ "$(id -u)" -eq 0 ]; then
        # Already running as root
        tshark -i $INTERFACE -w "$PCAP_FILE" > "$OUTPUT_DIR/tshark_output.log" 2>&1 &
        TSHARK_PID=$!
        echo "Running tshark as root user"
    else
        # Try running with sudo
        sudo -n true 2>/dev/null
        if [ $? -eq 0 ]; then
            # We can use sudo without password
            sudo tshark -i $INTERFACE -w "$PCAP_FILE" > "$OUTPUT_DIR/tshark_output.log" 2>&1 &
            TSHARK_PID=$!
            echo "Running tshark with sudo"
        else
            # Try running directly (if we're in wireshark group)
            tshark -i $INTERFACE -w "$PCAP_FILE" > "$OUTPUT_DIR/tshark_output.log" 2>&1 &
            TSHARK_PID=$!
            echo "Running tshark directly"
        fi
    fi

    # Check if tshark started successfully
    sleep 2
    if ! ps -p $TSHARK_PID > /dev/null; then
        echo "Warning: tshark failed to start. Check $OUTPUT_DIR/tshark_output.log for details."
        # Output the error for easier debugging
        if [ -f "$OUTPUT_DIR/tshark_output.log" ]; then
            echo "tshark error: $(cat "$OUTPUT_DIR/tshark_output.log")"
        fi
        PCAP_FLAG=false
    else
        echo "tshark process started with PID $TSHARK_PID"
        # Try to observe the first few lines of output
        sleep 3
        if [ -f "$OUTPUT_DIR/tshark_output.log" ]; then
            echo "tshark output: $(head -3 "$OUTPUT_DIR/tshark_output.log")"
        fi
    fi
fi
# Build the command to run the Puppeteer test
JS_COMMAND="node $SCRIPT_DIR/ookla-test.js"
JS_COMMAND="$JS_COMMAND -s \"$SERVER\""
JS_COMMAND="$JS_COMMAND -c \"$CONNECTION\""
JS_COMMAND="$JS_COMMAND -o \"$OUTPUT_DIR\""

# Fix any permission issues in the output directory
if [ -d "$OUTPUT_DIR" ]; then
    sudo chown -R $(whoami):$(whoami) "$OUTPUT_DIR"
    chmod -R 777 "$OUTPUT_DIR"
fi

# Run the Puppeteer test
echo "Launching speed test..."
echo "Executing: $JS_COMMAND"
eval "$JS_COMMAND"
TEST_EXIT_CODE=$?

# Stop packet capture if pcap flag is enabled
if [ "$PCAP_FLAG" = true ]; then
    echo "Stopping packet capture..."
    if ps -p $TSHARK_PID > /dev/null; then
        # First try normal kill
        kill $TSHARK_PID 2>/dev/null
        sleep 1

        # If still running, try sudo kill
        if ps -p $TSHARK_PID > /dev/null; then
            sudo kill $TSHARK_PID 2>/dev/null
            sleep 1

            # If STILL running, use SIGKILL
            if ps -p $TSHARK_PID > /dev/null; then
                sudo kill -9 $TSHARK_PID 2>/dev/null
            fi
        fi

        echo "Packet capture completed."

        # Ensure the pcap file is accessible
        if [ -f "$PCAP_FILE" ]; then
            sudo chmod 666 "$PCAP_FILE"
            ls -la "$PCAP_FILE"
            echo "Packet capture saved to $PCAP_FILE ($(du -h "$PCAP_FILE" | cut -f1) bytes)"
        else
            echo "Warning: Packet capture file was not created"
            ls -la "$OUTPUT_DIR"
        fi
    else
        echo "Warning: tshark process was not running"
    fi
fi

# Create metadata.json file with test information
echo "{
  \"server\": \"$SERVER\",
  \"connection\": \"$CONNECTION\",
  \"timestamp\": \"$(date '+%Y-%m-%d %H:%M:%S')\",
  "dev_mode": $DEV_MODE,
  "pcap_enabled": $PCAP_FLAG
}" > "$OUTPUT_DIR/metadata.json"

echo "---------------------------------------------"
echo "Test completed with exit code: $TEST_EXIT_CODE"
echo "Results saved to: $OUTPUT_DIR"
echo "---------------------------------------------"
# Output the directory path in a standardized format for automated processing
echo "OUTPUT_DIR=$OUTPUT_DIR"

exit $TEST_EXIT_CODE