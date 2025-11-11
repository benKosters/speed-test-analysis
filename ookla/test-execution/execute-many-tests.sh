#!/bin/bash

BASE_DIR="$(dirname "$0")"
COMMANDS_FILE="$BASE_DIR/test-configurations.txt"
LOG_FILE="$BASE_DIR/many-tests.log"
ENV_FILE="$BASE_DIR/.env"
RESULTS_DIR="$BASE_DIR/ookla-test-results"

# Configuration
BATCH_SIZE=20  # The number of tests before uploading to the S3 bucket
WAIT_TIME=120  # Cooldown period before continuing tests -- this should not be too long

show_help() {
    echo "Usage: ./execute-many-tests.sh [options]"
    echo ""
    echo "Options:"
    echo "  -b, --batch <number>     Number of tests before uploading to S3 (default: 20)"
    echo "  -w, --wait <seconds>     Cooldown period between batches in seconds (default: 120)"
    echo "  -h, --help               Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./execute-many-tests.sh                    # Use default settings"
    echo "  ./execute-many-tests.sh -b 10 -w 60       # Upload every 10 tests, wait 60 seconds"
    echo "  ./execute-many-tests.sh --batch 5 --wait 30"
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
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

# Function to compress and upload batch
upload_batch() {
    local batch_num=$1
    echo "[$(date)] Starting upload process for batch $batch_num" | tee -a "$LOG_FILE"

    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local archive_name="ookla_tests_batch${batch_num}_${timestamp}.tar.gz"
    local archive_path="$BASE_DIR/$archive_name"

    echo "[$(date)] Compressing test results." | tee -a "$LOG_FILE"
    if tar -czf "$archive_path" -C "$BASE_DIR" ookla-test-results/ 2>> "$LOG_FILE"; then
        echo "[$(date)] Compression successful: $(du -h "$archive_path" | cut -f1)" | tee -a "$LOG_FILE"
    else
        echo "[$(date)] Error: Compression failed" | tee -a "$LOG_FILE"
        return 1
    fi

    # Upload to S3
    echo "[$(date)] Uploading to S3 bucket: $S3_BUCKET_NAME" | tee -a "$LOG_FILE"
    if aws s3 cp "$archive_path" "s3://$S3_BUCKET_NAME/" 2>> "$LOG_FILE"; then
        echo "[$(date)] Upload successful" | tee -a "$LOG_FILE"

        # Verify upload
        if aws s3 ls "s3://$S3_BUCKET_NAME/$archive_name" >/dev/null 2>&1; then
            echo "[$(date)] Upload verified in S3" | tee -a "$LOG_FILE"

            # Clean up local files
            echo "[$(date)] Removing local test files" | tee -a "$LOG_FILE"
            rm -rf "$RESULTS_DIR"/*
            rm -f "$archive_path"
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
echo "[$(date)] Batch size: $BATCH_SIZE tests" | tee -a "$LOG_FILE"
echo "[$(date)] S3 bucket: $S3_BUCKET_NAME" | tee -a "$LOG_FILE"

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
            echo "[$(date)] Reached batch limit ($BATCH_SIZE tests). Starting upload process." | tee -a "$LOG_FILE"

            if upload_batch $batch_num; then
                echo "[$(date)] Batch $batch_num upload completed successfully" | tee -a "$LOG_FILE"
                batch_num=$((batch_num + 1))
            else
                echo "[$(date)] Error: Batch $batch_num upload failed. Stopping execution." | tee -a "$LOG_FILE"
                exit 1
            fi
        fi
    fi
done < "$COMMANDS_FILE"

# Upload any remaining tests if the batch limit is not reached but all configurations are done
remaining_tests=$(count_tests)
if [ $remaining_tests -gt 0 ]; then
    echo "[$(date)] Uploading remaining $remaining_tests tests." | tee -a "$LOG_FILE"
    if upload_batch "final"; then
        echo "[$(date)] Final batch upload completed successfully" | tee -a "$LOG_FILE"
    else
        echo "[$(date)] Warning: Final batch upload failed" | tee -a "$LOG_FILE"
    fi
fi

echo "[$(date)] All commands finished." | tee -a "$LOG_FILE"