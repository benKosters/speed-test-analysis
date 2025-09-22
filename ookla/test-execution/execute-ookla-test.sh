#!/bin/bash

# First confirm there is an output directory in C:\
if [ ! -d "/mnt/c/ookla_conventional_tests" ]; then
    mkdir /mnt/c/ookla_conventional_tests
fi

PCAP_FLAG=false
DEV_MODE=false

for arg in "$@"; do
    if [[ "$arg" == "pcap" ]]; then
        PCAP_FLAG=true
    fi
    if [[ "$arg" == "dev" ]]; then
        DEV_MODE=true
    fi
done


# Check if in dev mode - If yes, confirm dev_tests/ exists and set the output directory
if [ "$DEV_MODE" = true ]; then
    if [ ! -d "/mnt/c/ookla_conventional_tests/dev_tests" ]; then
        mkdir /mnt/c/ookla_conventional_tests/dev_tests
    else
        echo "Clearing old files in dev_tests directory."
        rm -rf /mnt/c/ookla_conventional_tests/dev_tests/* # Remove old files
    fi
    OUTPUT_DIR="/mnt/c/ookla_conventional_tests/dev_tests"
else
    TIMESTAMP=$(date +"%m-%d-%Y_%H-%M")
    OUTPUT_DIR="/mnt/c/ookla_conventional_tests/$TIMESTAMP"
    mkdir $OUTPUT_DIR
fi


# Set up file path for pcap file if pcap flag is enabled
if [ "$PCAP_FLAG" = true ]; then
    PCAP_FILE="$OUTPUT_DIR/tcp_capture.pcap"
    INTERFACE="eth0"

    echo "Running pcap on $INTERFACE."
    sudo tshark -i $INTERFACE -w $PCAP_FILE & #Run in the background
    TSHARK_PID=$! #Assigns the process of the last command (the tshark) to a variable
    sleep 2
fi

# Run the Puppeteer test
echo "Launching speed test."
node ookla-test.js -s michwave -c single -o $OUTPUT_DIR

# Stop packet capture if pcap flag is enabled
if [ "$PCAP_FLAG" = true ]; then
    kill $TSHARK_PID
    echo "Packet capture saved to $PCAP_FILE"
fi