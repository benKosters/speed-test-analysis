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
    INTERFACE="eth0"

    echo "Running pcap on $INTERFACE."
    sudo tshark -i $INTERFACE -w $PCAP_FILE & #Run in the background
    TSHARK_PID=$! #Assigns the process of the last command (the tshark) to a variable
    sleep 2
fi

# Build the command to run the Puppeteer test
JS_COMMAND="node $SCRIPT_DIR/ookla-test.js"
JS_COMMAND="$JS_COMMAND -s \"$SERVER\""
JS_COMMAND="$JS_COMMAND -c \"$CONNECTION\""
JS_COMMAND="$JS_COMMAND -o \"$OUTPUT_DIR\""

# Run the Puppeteer test
echo "Launching speed test..."
echo "Executing: $JS_COMMAND"
eval "$JS_COMMAND"
TEST_EXIT_CODE=$?

# Stop packet capture if pcap flag is enabled
if [ "$PCAP_FLAG" = true ]; then
    echo "Stopping packet capture..."
    kill $TSHARK_PID
    echo "Packet capture saved to $PCAP_FILE"
fi

# Create metadata.json file with test information
echo "{
  \"server\": \"$SERVER\",
  \"connection\": \"$CONNECTION\",
  \"timestamp\": \"$(date '+%Y-%m-%d %H:%M:%S')\",
  \"dev_mode\": $DEV_MODE,
  \"pcap_enabled\": $PCAP_FLAG
}" > "$OUTPUT_DIR/metadata.json"

echo "---------------------------------------------"
echo "Test completed with exit code: $TEST_EXIT_CODE"
echo "Results saved to: $OUTPUT_DIR"
echo "---------------------------------------------"
# Output the directory path in a standardized format for automated processing
echo "OUTPUT_DIR=$OUTPUT_DIR"

exit $TEST_EXIT_CODE