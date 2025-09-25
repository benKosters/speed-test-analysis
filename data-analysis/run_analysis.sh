#!/bin/bash
# Script to first run filter-rabbits-netlog-data.js and then calculate_plot_throughput.py on all test directories

# Path to the test directories
TEST_DIR="/mnt/c/rabbits_tests"

# Path to the scripts
FILTER_SCRIPT_PATH="/home/benk/cs390/speed-test-analysis/rabbits/filter-rabbits-netlog-data.js"
ANALYSIS_SCRIPT_PATH="/home/benk/cs390/speed-test-analysis/data-analysis/calculate_plot_throughput.py"

# Create a directory for all plots
PLOTS_DIR="/mnt/c/rabbits_tests/all_plots"
mkdir -p "$PLOTS_DIR"

# Process all test directories
echo "===================================================="
echo "Step 1: Running filter-rabbits-netlog-data.js on all tests..."
echo "===================================================="

# Define test patterns to search for
declare -a PATTERNS=(
  "frontier-25000000-6flow-download"
  "frontier-25000000-6flow-upload"
  "hawaiian_telecom-25000000-6flow-download"
  "hawaiian_telecom-25000000-6flow-upload"
  "highline-25000000-6flow-download"
  "highline-25000000-6flow-upload"
  "michwave-25000000-6flow-download"
  "michwave-25000000-6flow-upload"
  "spacelink-25000000-6flow-download"
  "spacelink-25000000-6flow-upload"
)

# Process all matching directories
for PATTERN in "${PATTERNS[@]}"; do
  # Find directories matching the pattern
  for TEST_PATH in $(find "$TEST_DIR" -maxdepth 1 -type d -name "*$PATTERN*"); do
    TEST_NAME=$(basename "$TEST_PATH")

    echo "----------------------------------------------"
    echo "Processing test: $TEST_NAME"

    # Check if the test has the necessary files
    NETLOG_FILE="$TEST_PATH/ookla.netlog"
    URLS_JSON_FILE="$TEST_PATH/ookla_urls.json"
    URLS_TXT_FILE="$TEST_PATH/ookla_urls.txt"

    # Choose the appropriate URL file (either .json or .txt)
    URL_FILE_TO_USE=""
    if [ -f "$URLS_JSON_FILE" ]; then
      URL_FILE_TO_USE="$URLS_JSON_FILE"
    elif [ -f "$URLS_TXT_FILE" ]; then
      URL_FILE_TO_USE="$URLS_TXT_FILE"
    fi

    if [ -f "$NETLOG_FILE" ] && [ -n "$URL_FILE_TO_USE" ]; then
      echo "Running filter-rabbits-netlog-data.js on $TEST_NAME"
      echo "Command: node $FILTER_SCRIPT_PATH $NETLOG_FILE $URL_FILE_TO_USE"
      node "$FILTER_SCRIPT_PATH" "$NETLOG_FILE" "$URL_FILE_TO_USE"

      # Check if filter script was successful
      if [ $? -eq 0 ]; then
        echo "Filter script completed successfully"
      else
        echo "WARNING: Filter script may have encountered errors"
      fi
    else
      echo "WARNING: Missing netlog or urls file for $TEST_NAME, skipping filter step"
      if [ ! -f "$NETLOG_FILE" ]; then
        echo "  - Missing netlog file: $NETLOG_FILE"
      fi
      if [ -z "$URL_FILE_TO_USE" ]; then
        echo "  - Missing URLs file (checked both .json and .txt)"
      fi
    fi

    # Create a directory for this test's plots
    TEST_PLOT_DIR="$PLOTS_DIR/$TEST_NAME"
    mkdir -p "$TEST_PLOT_DIR"

    # Run the analysis script with --save option to save plots
    echo "Running: python3 $ANALYSIS_SCRIPT_PATH $TEST_PATH --save"
    python3 "$ANALYSIS_SCRIPT_PATH" "$TEST_PATH" --save

    # Copy generated plots to the consolidated directory
    if [ -d "$TEST_PATH/plot_images" ]; then
      echo "Copying plots to $TEST_PLOT_DIR"
      cp "$TEST_PATH/plot_images"/* "$TEST_PLOT_DIR/"
    fi

    echo "Completed processing: $TEST_NAME"
    echo "----------------------------------------------"
  done
done

# Create a summary file
SUMMARY_FILE="$PLOTS_DIR/test_summary.txt"
echo "Test Processing Summary" > "$SUMMARY_FILE"
echo "======================" >> "$SUMMARY_FILE"
echo "Date: $(date)" >> "$SUMMARY_FILE"
echo "" >> "$SUMMARY_FILE"
echo "Processed Tests:" >> "$SUMMARY_FILE"

for PATTERN in "${PATTERNS[@]}"; do
  find "$TEST_DIR" -maxdepth 1 -type d -name "*$PATTERN*" | while read TEST_PATH; do
    TEST_NAME=$(basename "$TEST_PATH")

    # Check if key files were generated
    BYTE_TIME_FILE="$TEST_PATH/byte_time_list.json"
    CURRENT_POS_FILE="$TEST_PATH/current_position_list.json"

    if [ -f "$BYTE_TIME_FILE" ] || [ -f "$CURRENT_POS_FILE" ]; then
      PROCESSING_STATUS="SUCCESS"
    else
      PROCESSING_STATUS="INCOMPLETE - Missing data files"
    fi

    echo "- $TEST_NAME: $PROCESSING_STATUS" >> "$SUMMARY_FILE"
  done
done

echo "" >> "$SUMMARY_FILE"
echo "All plots are collected in: $PLOTS_DIR" >> "$SUMMARY_FILE"

echo "===================================================="
echo "All tests processed!"
echo "Plots are saved in original test directories and collected in: $PLOTS_DIR"
echo "A summary has been saved to: $SUMMARY_FILE"
echo "===================================================="