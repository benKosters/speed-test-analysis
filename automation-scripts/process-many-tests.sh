#!/bin/bash
# Script to run process-netlog-data.sh on multiple test directories

show_help() {
    echo "Usage: ./process-many-tests.sh <search_directory> [options]"
    echo ""
    echo "Required:"
    echo "  <search_directory>   Root directory to search for tests"
    echo "                       (e.g., usa-server-tests/ or usa-server-tests/batch1/)"
    echo ""
    echo "Test Filtering:"
    echo "  -multi               Process only multi-flow tests (e.g., *-multi-*)"
    echo "  -single              Process only single-flow tests (e.g., *-single-*)"
    echo "                       (If neither specified, processes all tests)"
    echo ""
    echo "Passthrough Flags (forwarded to process-netlog-data.sh and main.py):"
    echo "  -upload              Process only upload data"
    echo "  -download            Process only download data"
    echo "  --save               Save plots"
    echo "  --bin <n>            Bin size for aggregating data"
    echo "  --all-configs        Run all 16 configurations"
    echo ""
    echo "Other Options:"
    echo "  -h, --help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  # Process all tests in all batches"
    echo "  ./process-many-tests.sh /mnt/d/usa-server-tests/"
    echo ""
    echo "  # Process only multi-flow tests in a specific batch"
    echo "  ./process-many-tests.sh /mnt/d/usa-server-tests/batch1/ -multi"
    echo ""
    echo "  # Process single-flow tests, download only, with plots saved"
    echo "  ./process-many-tests.sh /mnt/d/usa-server-tests/ -single -download --save"
    echo ""
    echo "  # Process with custom bin size and all configs"
    echo "  ./process-many-tests.sh /mnt/d/usa-server-tests/ --bin 10 --all-configs"
    exit 0
}

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROCESS_SCRIPT="$SCRIPT_DIR/process-netlog-data.sh"

# Parse command-line arguments
SEARCH_DIR=""
TEST_FILTER=""  # "multi", "single", or empty for all
PASSTHROUGH_FLAGS=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        -multi)
            if [ "$TEST_FILTER" = "single" ]; then
                echo "Error: Cannot specify both -multi and -single"
                exit 1
            fi
            TEST_FILTER="multi"
            shift
            ;;
        -single)
            if [ "$TEST_FILTER" = "multi" ]; then
                echo "Error: Cannot specify both -multi and -single"
                exit 1
            fi
            TEST_FILTER="single"
            shift
            ;;
        -upload|-download)
            PASSTHROUGH_FLAGS="$PASSTHROUGH_FLAGS $1"
            shift
            ;;
        --save|--all-configs)
            PASSTHROUGH_FLAGS="$PASSTHROUGH_FLAGS $1"
            shift
            ;;
        --bin)
            if [ -z "$2" ] || ! [[ "$2" =~ ^[0-9]+$ ]]; then
                echo "Error: --bin requires a positive integer"
                exit 1
            fi
            PASSTHROUGH_FLAGS="$PASSTHROUGH_FLAGS $1 $2"
            shift 2
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
            if [ -z "$SEARCH_DIR" ]; then
                SEARCH_DIR="$1"
            else
                echo "Error: Multiple directories specified"
                exit 1
            fi
            shift
            ;;
    esac
done

# Validate search directory
if [ -z "$SEARCH_DIR" ]; then
    echo "Error: Please provide a search directory"
    echo "Use -h or --help for usage information"
    exit 1
fi

if [ ! -d "$SEARCH_DIR" ]; then
    echo "Error: Directory '$SEARCH_DIR' does not exist"
    exit 1
fi

# Check if the processing script exists
if [ ! -f "$PROCESS_SCRIPT" ]; then
    echo "Error: Process script not found at $PROCESS_SCRIPT"
    exit 1
fi

# Make sure the processing script is executable
chmod +x "$PROCESS_SCRIPT"

# Function to check if directory is a test directory
# A test directory should have download/ or upload/ subdirectories
is_test_directory() {
    local dir="$1"
    [ -d "$dir/download" ] || [ -d "$dir/upload" ]
}

# Function to check if test matches the filter
matches_filter() {
    local test_name="$1"
    case "$TEST_FILTER" in
        multi)
            [[ "$test_name" == *-multi-* ]]
            ;;
        single)
            [[ "$test_name" == *-single-* ]]
            ;;
        *)
            return 0  # No filter, match everything
            ;;
    esac
}

# Recursively find all test directories
echo "Searching for test directories in: $SEARCH_DIR"
if [ -n "$TEST_FILTER" ]; then
    echo "Filter: Only processing $TEST_FILTER-flow tests"
fi
if [ -n "$PASSTHROUGH_FLAGS" ]; then
    echo "Options:$PASSTHROUGH_FLAGS"
fi
echo ""

TEST_DIRECTORIES=()

# Use find to locate all potential test directories
# Look for directories that contain download/ or upload/ subdirectories
while IFS= read -r -d '' dir; do
    parent_dir=$(dirname "$dir")
    # Check if parent is a test directory and hasn't been added yet
    if is_test_directory "$parent_dir"; then
        test_name=$(basename "$parent_dir")
        # Check if it matches the filter
        if matches_filter "$test_name"; then
            # Check if not already in array
            if [[ ! " ${TEST_DIRECTORIES[@]} " =~ " ${parent_dir} " ]]; then
                TEST_DIRECTORIES+=("$parent_dir")
            fi
        fi
    fi
done < <(find "$SEARCH_DIR" -type d \( -name "download" -o -name "upload" \) -print0)

# Sort the test directories for consistent processing order
IFS=$'\n' TEST_DIRECTORIES=($(sort <<<"${TEST_DIRECTORIES[*]}"))
unset IFS

if [ ${#TEST_DIRECTORIES[@]} -eq 0 ]; then
    echo "No test directories found"
    if [ -n "$TEST_FILTER" ]; then
        echo "Try running without the -$TEST_FILTER filter"
    fi
    exit 1
fi

echo "Found ${#TEST_DIRECTORIES[@]} test director$([ ${#TEST_DIRECTORIES[@]} -eq 1 ] && echo "y" || echo "ies") to process:"
for dir in "${TEST_DIRECTORIES[@]}"; do
    # Get relative path from search directory
    rel_path="${dir#$SEARCH_DIR}"
    rel_path="${rel_path#/}"
    echo "  - $rel_path"
done
echo ""

# Confirmation prompt for large batches
if [ ${#TEST_DIRECTORIES[@]} -gt 10 ]; then
    echo "Warning: About to process ${#TEST_DIRECTORIES[@]} tests"
    read -p "Continue? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted"
        exit 0
    fi
    echo ""
fi

# Process each directory
successful=0
failed=0
start_time=$(date +%s)

for dir in "${TEST_DIRECTORIES[@]}"; do
    rel_path="${dir#$SEARCH_DIR}"
    rel_path="${rel_path#/}"
    test_name=$(basename "$dir")

    echo "========================================="
    echo "Processing [$((successful + failed + 1))/${#TEST_DIRECTORIES[@]}]: $rel_path"
    echo "========================================="

    # Run the netlog processing script with passthrough flags
    if $PROCESS_SCRIPT "$dir" $PASSTHROUGH_FLAGS; then
        echo "✓ Successfully processed: $rel_path"
        successful=$((successful + 1))
    else
        echo "✗ Failed to process: $rel_path"
        failed=$((failed + 1))
    fi
    echo ""
done

end_time=$(date +%s)
elapsed=$((end_time - start_time))

echo "========================================="
echo "Processing completed!"
echo "========================================="
echo "Results:"
echo "  Successful: $successful"
echo "  Failed:     $failed"
echo "  Total:      ${#TEST_DIRECTORIES[@]}"
echo ""
printf "  Time elapsed: %02d:%02d:%02d\n" $((elapsed/3600)) $((elapsed%3600/60)) $((elapsed%60))
echo "========================================="

if [ $failed -gt 0 ]; then
    echo "Warning: $failed test(s) failed. Check the output above for details."
    exit 1
fi

exit 0