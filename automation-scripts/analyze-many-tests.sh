l#!/bin/bash
# Script to run a specified script on all test directories

# Parse command line arguments
SCRIPT=""
OUTPUT_CSV=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -script)
            SCRIPT="$2"
            shift 2
            ;;
        -output)
            OUTPUT_CSV="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 -script <script_path> -output <output_csv>"
            echo "Example: $0 -script ../exploratory/eda_driver.py -output ./results.csv"
            exit 1
            ;;
    esac
done

# Validate required parameters
if [ -z "$SCRIPT" ]; then
    echo "ERROR: -script parameter is required"
    echo "Usage: $0 -script <script_path> -output <output_csv>"
    echo "Example: $0 -script ../exploratory/eda_driver.py -output ./results.csv"
    exit 1
fi

if [ -z "$OUTPUT_CSV" ]; then
    echo "ERROR: -output parameter is required"
    echo "Usage: $0 -script <script_path> -output <output_csv>"
    echo "Example: $0 -script ../exploratory/eda_driver.py -output ./results.csv"
    exit 1
fi

# Configuration
TEST_RESULTS_DIR="/mnt/d/virginia-ookla-tests"

echo "Processing all test directories in: $TEST_RESULTS_DIR"
echo "Using script: $SCRIPT"
echo "Output CSV: $OUTPUT_CSV"
echo ""

# Check if the test results directory exists
if [ ! -d "$TEST_RESULTS_DIR" ]; then
    echo "ERROR: Directory $TEST_RESULTS_DIR does not exist"
    exit 1
fi

# Check if the script exists
if [ ! -f "$SCRIPT" ]; then
    echo "ERROR: Script $SCRIPT does not exist"
    exit 1
fi

# Make sure the script is executable if it's a shell script
if [[ "$SCRIPT" == *.sh ]]; then
    chmod +x "$SCRIPT"
fi

# Get all test directories from batch1 through batch10
TEST_DIRECTORIES=()
for batch in {1..10}; do
    batch_dir="$TEST_RESULTS_DIR/batch$batch"
    if [ -d "$batch_dir" ]; then
        echo "Scanning batch$batch..."
        test_count=0
        # Find all test directories in this batch (excluding the batch directory itself)
        for test_dir in "$batch_dir"/*; do
            if [ -d "$test_dir" ]; then
                TEST_DIRECTORIES+=("$test_dir")
                test_count=$((test_count + 1))
                echo "  Found: $(basename "$test_dir")"
            fi
        done
        echo "  Total tests in batch$batch: $test_count"
    else
        echo "Warning: batch$batch directory not found at $batch_dir"
    fi
done

if [ ${#TEST_DIRECTORIES[@]} -eq 0 ]; then
    echo "No test directories found in any batch folders"
    exit 1
fi

echo "Found ${#TEST_DIRECTORIES[@]} test directories to process:"
for dir in "${TEST_DIRECTORIES[@]}"; do
    echo "  - $(basename "$(dirname "$dir")")/$(basename "$dir")"
done
echo ""

# Process each directory
successful=0
failed=0

# Determine how to run the script based on file extension
if [[ "$SCRIPT" == *.py ]]; then
    RUN_CMD="python3"
elif [[ "$SCRIPT" == *.sh ]]; then
    RUN_CMD=""
else
    # Default to python3 for unknown extensions
    RUN_CMD="python3"
fi

for dir in "${TEST_DIRECTORIES[@]}"; do
    batch_name=$(basename "$(dirname "$dir")")
    test_name=$(basename "$dir")
    full_name="$batch_name/$test_name"

    echo "Processing: $full_name"
    echo "  Running script..."

    # Run the script with the test directory and output CSV as arguments
    if [ -n "$RUN_CMD" ]; then
        if $RUN_CMD "$SCRIPT" "$dir" "$OUTPUT_CSV"; then
            echo "  ✓ Script completed for: $full_name"
            successful=$((successful + 1))
        else
            echo "  ✗ Script failed for: $full_name"
            failed=$((failed + 1))
        fi
    else
        if "$SCRIPT" "$dir" "$OUTPUT_CSV"; then
            echo "  ✓ Script completed for: $full_name"
            successful=$((successful + 1))
        else
            echo "  ✗ Script failed for: $full_name"
            failed=$((failed + 1))
        fi
    fi
    echo ""
done

echo "========================================="
echo "Processing completed!"
echo ""
echo "Script Execution Results:"
echo "  Successful: $successful"
echo "  Failed: $failed"
echo "  Total: $((successful + failed))"
echo ""
echo "Output CSV file: $OUTPUT_CSV"
if [ -f "$OUTPUT_CSV" ]; then
    row_count=$(wc -l < "$OUTPUT_CSV")
    echo "Total rows in CSV: $row_count (including header)"
fi
echo "========================================="

if [ $failed -gt 0 ]; then
    echo "Some operations failed. Check the output above for details."
    exit 1
fi
