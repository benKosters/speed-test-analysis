#!/bin/bash

BASE_DIR="$(dirname "$0")"
COMMANDS_FILE="$BASE_DIR/test-configurations.txt"
LOG_FILE="$BASE_DIR/many-tests.log"
ENV_FILE="$BASE_DIR/.env"
RESULTS_DIR="$BASE_DIR/ookla-test-results"

# Configuration
BATCH_SIZE=20  # The number of tests before uploading to the S3 bucket
WAIT_TIME=120  # Cooldown period before continuing tests -- this should not be too long
TEST_NAME=""   # Name of the test (required)
UPLOAD_TO_S3=true  # Upload to S3 and delete local files (default: true)
FILTER_NETLOG=false  # Filter netlog data and remove netlog.json before upload (default: false)

show_help() {
    echo "Usage: ./execute-many-tests.sh -n <test_name> [options]"
    echo ""
    echo "Required:"
    echo "  -n, --name <name>        Name for this test batch (required)"
    echo ""
    echo "Options:"
    echo "  -b, --batch <number>     Number of tests before uploading to S3 (default: 20)"
    echo "  -w, --wait <seconds>     Cooldown period between batches in seconds (default: 120)"
    echo "  -f, --filter             Filter netlog data and remove netlog.json before upload"
    echo "  -l, --local              Keep tests local, do not upload to S3 or delete files"
    echo "  -h, --help               Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./execute-many-tests.sh -n michwave_test1"
    echo "  ./execute-many-tests.sh -n experiment_jan10 -b 10 -w 60"
    echo "  ./execute-many-tests.sh --name my_test --batch 5 --wait 30"
    echo "  ./execute-many-tests.sh -n local_test -l"
    echo "  ./execute-many-tests.sh -n filtered_test -f"
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -n|--name)
            TEST_NAME="$2"
            if [ -z "$TEST_NAME" ]; then
                echo "Error: Test name cannot be empty"
                exit 1
            fi
            shift 2
            ;;
        -b|--batch)
            BATCH_SIZE="$2"
            if ! [[ "$BATCH_SIZE" =~ ^[0-9]+$ ]] || [ "$BATCH_SIZE" -le 0 ]; then
                echo "Error: Batch size must be a positive integer"
                exit 1
            fi
            shift 2
            ;;
        -w|--wait)
            WAIT_TIME="$2"
            if ! [[ "$WAIT_TIME" =~ ^[0-9]+$ ]] || [ "$WAIT_TIME" -lt 0 ]; then
                echo "Error: Wait time must be a non-negative integer"
                exit 1
            fi
            shift 2
            ;;
        -f|--filter)
            FILTER_NETLOG=true
            shift
            ;;
        -l | --local)
            UPLOAD_TO_S3=false
            shift
            ;;
        -h|--help)
            show_help
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Check if test name was provided
if [ -z "$TEST_NAME" ]; then
    echo "Error: Test name is required. Use -n or --name to specify."
    echo "Use -h or --help for usage information"
    exit 1
fi

# Load env variables
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
else
    echo "Error: .env file not found at $ENV_FILE"
    exit 1
fi

# Check if AWS CLI is installed
if ! command -v aws >/dev/null 2>&1; then
    echo "Error: AWS CLI not installed. Install with: sudo apt-get install awscli"
    exit 1
fi

# Check if Node.js is installed (needed for filtering)
if [ "$FILTER_NETLOG" = true ] && ! command -v node >/dev/null 2>&1; then
    echo "Error: Node.js not installed. Install Node.js to use the --filter option."
    exit 1
fi

filter_batch() {
    echo "[$(date)] Filtering netlog data for all tests in batch..." | tee -a "$LOG_FILE"

    local filter_script="$BASE_DIR/../netlog-filter/main.js"

    if [ ! -f "$filter_script" ]; then
        echo "[$(date)] Error: Filter script not found at $filter_script" | tee -a "$LOG_FILE"
        return 1
    fi

    local test_count=0
    local success_count=0
    local netlog_removed_count=0

    # Process each test directory in the results folder
    for test_dir in "$RESULTS_DIR"/*/; do
        if [ -d "$test_dir" ]; then
            test_count=$((test_count + 1))
            local test_name=$(basename "$test_dir")

            echo "[$(date)] Filtering test: $test_name" | tee -a "$LOG_FILE"

            # Run the filtering script
            if node "$filter_script" "$test_dir" >> "$LOG_FILE" 2>&1; then
                success_count=$((success_count + 1))

                # Remove netlog.json after successful filtering
                local netlog_file="${test_dir}netlog.json"
                if [ -f "$netlog_file" ]; then
                    local netlog_size=$(stat -c%s "$netlog_file" 2>/dev/null || echo "0")
                    rm -f "$netlog_file"
                    netlog_removed_count=$((netlog_removed_count + 1))
                    echo "[$(date)] Removed netlog.json ($(numfmt --to=iec $netlog_size)) from $test_name" | tee -a "$LOG_FILE"
                fi
            else
                echo "[$(date)] Warning: Filtering failed for $test_name" | tee -a "$LOG_FILE"
            fi
        fi
    done

    echo "[$(date)] Filtering complete: $success_count/$test_count tests processed, $netlog_removed_count netlog files removed" | tee -a "$LOG_FILE"
    return 0
}

upload_batch() {
    local batch_num=$1
    echo "[$(date)] Starting upload process for batch $batch_num" | tee -a "$LOG_FILE"

    # Filter netlog data if requested
    if [ "$FILTER_NETLOG" = true ]; then
        if ! filter_batch; then
            echo "[$(date)] Warning: Filtering failed, continuing with upload" | tee -a "$LOG_FILE"
        fi
    fi

    local timestamp=$(date +"%Y-%m-%d_%H%M")
    local s3_prefix="${TEST_NAME}_ookla_tests_batch${batch_num}_${timestamp}"

    echo "[$(date)] Compressing PCAP files for optimal upload (using gzip -9)..." | tee -a "$LOG_FILE"

    # Find and compress all .pcap files in the results directory
    local pcap_count=0
    local compressed_size=0
    local original_size=0

    while IFS= read -r -d '' pcap_file; do
        if [ -f "$pcap_file" ]; then
            local original_file_size=$(stat -c%s "$pcap_file")
            original_size=$((original_size + original_file_size))

            echo "[$(date)] Compressing $(basename "$pcap_file") with gzip -9" | tee -a "$LOG_FILE"

            # Compress the pcap file with gzip -9 (maximum compression)
            if gzip -9 "$pcap_file" 2>> "$LOG_FILE"; then
                local compressed_file_size=$(stat -c%s "${pcap_file}.gz")
                compressed_size=$((compressed_size + compressed_file_size))
                pcap_count=$((pcap_count + 1))

                local compression_ratio=$(echo "scale=1; $compressed_file_size * 100 / $original_file_size" | bc 2>/dev/null || echo "N/A")
                echo "[$(date)] Compressed $(basename "$pcap_file"): $(numfmt --to=iec $original_file_size) → $(numfmt --to=iec $compressed_file_size) (${compression_ratio}%)" | tee -a "$LOG_FILE"
            else
                echo "[$(date)] Warning: Failed to compress $(basename "$pcap_file")" | tee -a "$LOG_FILE"
            fi
        fi
    done < <(find "$RESULTS_DIR" -name "*.pcap" -print0)

    if [ $pcap_count -gt 0 ]; then
        local total_savings=$(echo "scale=1; ($original_size - $compressed_size) * 100 / $original_size" | bc 2>/dev/null || echo "N/A")
        echo "[$(date)] PCAP compression complete: $pcap_count files, ${total_savings}% size reduction" | tee -a "$LOG_FILE"
        echo "[$(date)] Original size: $(numfmt --to=iec $original_size)" | tee -a "$LOG_FILE"
        echo "[$(date)] Compressed size: $(numfmt --to=iec $compressed_size)" | tee -a "$LOG_FILE"
        echo "[$(date)] Space saved: $(numfmt --to=iec $((original_size - compressed_size)))" | tee -a "$LOG_FILE"
    else
        echo "[$(date)] No PCAP files found to compress" | tee -a "$LOG_FILE"
    fi

    echo "[$(date)] Uploading test results to S3 (PCAP files compressed with gzip -6, others raw)..." | tee -a "$LOG_FILE"

    # Upload the entire ookla-test-results directory to S3 with batch prefix
    if aws s3 sync "$RESULTS_DIR/" "s3://$S3_BUCKET_NAME/$s3_prefix/" --delete 2>> "$LOG_FILE"; then
        echo "[$(date)] Upload successful to s3://$S3_BUCKET_NAME/$s3_prefix/" | tee -a "$LOG_FILE"

        # Verify upload by listing the S3 directory
        local file_count=$(aws s3 ls "s3://$S3_BUCKET_NAME/$s3_prefix/" --recursive | wc -l)
        if [ "$file_count" -gt 0 ]; then
            echo "[$(date)] Upload verified in S3 ($file_count files uploaded)" | tee -a "$LOG_FILE"

            # Clean up local files
            echo "[$(date)] Removing local test files" | tee -a "$LOG_FILE"
            rm -rf "$RESULTS_DIR"/*
            echo "[$(date)] Local cleanup complete" | tee -a "$LOG_FILE"

            echo "[$(date)] Waiting $WAIT_TIME seconds before continuing." | tee -a "$LOG_FILE"
            sleep $WAIT_TIME

            return 0
        else
            echo "[$(date)] Error: Could not verify upload in S3" | tee -a "$LOG_FILE"
            return 1
        fi
    else
        echo "[$(date)] Error: Upload to S3 failed" | tee -a "$LOG_FILE"
        return 1
    fi
}


# Function to count existing test directories to track batch size
count_tests() {
    if [ -d "$RESULTS_DIR" ]; then
        find "$RESULTS_DIR" -maxdepth 1 -type d ! -path "$RESULTS_DIR" | wc -l
    else
        echo 0
    fi
}

echo "[$(date)] Starting driver to run many Ookla tests" | tee -a "$LOG_FILE"
echo "[$(date)] Test name: $TEST_NAME" | tee -a "$LOG_FILE"
echo "[$(date)] Batch size: $BATCH_SIZE tests" | tee -a "$LOG_FILE"
if [ "$UPLOAD_TO_S3" = true ]; then
    echo "[$(date)] S3 bucket: $S3_BUCKET_NAME" | tee -a "$LOG_FILE"
    echo "[$(date)] Upload mode: Tests will be uploaded and deleted after each batch" | tee -a "$LOG_FILE"
else
    echo "[$(date)] Local mode: Tests will be kept locally (no upload or deletion)" | tee -a "$LOG_FILE"
fi
if [ "$FILTER_NETLOG" = true ]; then
    echo "[$(date)] Filtering: Netlog data will be filtered and netlog.json removed before upload" | tee -a "$LOG_FILE"
fi

test_count=0
batch_num=1

# Loop through each command in the commands file
while IFS= read -r CMD; do
    if [ -n "$CMD" ] && [[ ! "$CMD" =~ ^[[:space:]]*# ]]; then
        echo "[$(date)] Running test $((test_count + 1)): $CMD" | tee -a "$LOG_FILE"

        eval "$CMD" >> "$LOG_FILE" 2>&1
        EXIT_CODE=$?

        if [ $EXIT_CODE -eq 0 ]; then
            test_count=$((test_count + 1))
            echo "[$(date)] Test $test_count completed successfully" | tee -a "$LOG_FILE"
        else
            echo "[$(date)] Test failed with exit code $EXIT_CODE" | tee -a "$LOG_FILE"
        fi

        if [ $((test_count % BATCH_SIZE)) -eq 0 ] && [ $test_count -gt 0 ]; then
            if [ "$UPLOAD_TO_S3" = true ]; then
                echo "[$(date)] Reached batch limit ($BATCH_SIZE tests). Starting upload process." | tee -a "$LOG_FILE"

                if upload_batch $batch_num; then
                    echo "[$(date)] Batch $batch_num upload completed successfully" | tee -a "$LOG_FILE"
                    batch_num=$((batch_num + 1))
                else
                    echo "[$(date)] Error: Batch $batch_num upload failed. Stopping execution." | tee -a "$LOG_FILE"
                    exit 1
                fi
            else
                echo "[$(date)] Reached batch limit ($BATCH_SIZE tests). Keeping tests locally." | tee -a "$LOG_FILE"
                batch_num=$((batch_num + 1))
            fi
        fi
    fi
done < "$COMMANDS_FILE"

# Upload any remaining tests if the batch limit is not reached but all configurations are done
remaining_tests=$(count_tests)
if [ $remaining_tests -gt 0 ]; then
    if [ "$UPLOAD_TO_S3" = true ]; then
        echo "[$(date)] Uploading remaining $remaining_tests tests." | tee -a "$LOG_FILE"
        if upload_batch "final"; then
            echo "[$(date)] Final batch upload completed successfully" | tee -a "$LOG_FILE"
        else
            echo "[$(date)] Warning: Final batch upload failed" | tee -a "$LOG_FILE"
        fi
    else
        echo "[$(date)] All tests completed. $remaining_tests tests kept locally." | tee -a "$LOG_FILE"
    fi
fi

echo "[$(date)] All commands finished." | tee -a "$LOG_FILE"