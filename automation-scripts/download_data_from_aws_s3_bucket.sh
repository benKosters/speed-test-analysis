#!/bin/bash

BUCKET_NAME="rabbits-expr"
DOWNLOAD_DIR=""
TEST_PREFIX=""
BATCH="all"
EXCLUDE_EXTENSIONS="*.pcap,*.PCAP,*.pcap.gz"

usage() {
    echo "Usage: $0 -l <location> -t <test_prefix> [-b <batch>] [-e <exclude_extensions>] [--bucket <bucket_name>]"
    echo ""
    echo "Required arguments:"
    echo "  -l, --download-location <path>           Path where downloaded files should go"
    echo "  -n, --name <prefix>             Test name prefix (e.g., 'usa_ookla_tests', 'michwave-single')"
    echo ""
    echo "Optional arguments:"
    echo "  -b, --batch <number|all>        Batch number to download, or 'all' (default: all)"
    echo "  -e, --exclude <extensions>      Comma-separated file extensions to exclude"
    echo "                                  (default: '*.pcap,*.PCAP,*.pcap.gz')"
    echo "      --bucket <name>             S3 bucket name (default: 'rabbits-expr')"
    echo "  -h, --help                      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -l /mnt/d/usa-server-tests/ -t usa_ookla_tests -b 5"
    echo "  $0 -l /mnt/d/usa-server-tests/ -t usa_ookla_tests -b all"
    echo "  $0 -l /mnt/d/test-results/ -t michwave-single --exclude '*.pcap,*.log'"
    exit 1
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -l|--location)
            DOWNLOAD_DIR="$2"
            shift 2
            ;;
        -t|--test)
            TEST_PREFIX="$2"
            shift 2
            ;;
        -b|--batch)
            BATCH="$2"
            shift 2
            ;;
        -e|--exclude)
            EXCLUDE_EXTENSIONS="$2"
            shift 2
            ;;
        --bucket)
            BUCKET_NAME="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Error: Unknown option $1"
            usage
            ;;
    esac
done

# Validate required arguments
if [[ -z "$DOWNLOAD_DIR" ]]; then
    echo "Error: Location (-l) is required"
    usage
fi

if [[ -z "$TEST_PREFIX" ]]; then
    echo "Error: Test prefix (-t) is required"
    usage
fi

# Create download directory if it doesn't exist
if [[ ! -d "$DOWNLOAD_DIR" ]]; then
    echo "Creating directory: $DOWNLOAD_DIR"
    mkdir -p "$DOWNLOAD_DIR"
fi

# Convert exclude extensions to aws s3 sync exclude arguments
EXCLUDE_ARGS=""
IFS=',' read -ra EXTENSIONS <<< "$EXCLUDE_EXTENSIONS"
for ext in "${EXTENSIONS[@]}"; do
    EXCLUDE_ARGS="$EXCLUDE_ARGS --exclude \"$ext\""
done

echo "======================================"
echo "AWS S3 Download Configuration"
echo "======================================"
echo "Bucket: $BUCKET_NAME"
echo "Test Prefix: $TEST_PREFIX"
echo "Batch: $BATCH"
echo "Destination: $DOWNLOAD_DIR"
echo "Excluding: $EXCLUDE_EXTENSIONS"
echo ""

# List all prefixes in the bucket that match the test prefix
echo "Finding matching test directories in S3..."
if [[ "$BATCH" == "all" ]]; then
    # Download all batches matching the test prefix
    # List all directories that start with the test prefix
    PREFIXES=$(aws s3 ls "s3://$BUCKET_NAME/" | grep "PRE" | awk '{print $2}' | grep "^${TEST_PREFIX}")

    if [[ -z "$PREFIXES" ]]; then
        echo "Error: No directories found matching prefix '$TEST_PREFIX' in bucket '$BUCKET_NAME'"
        exit 1
    fi

    echo "Found matching directories:"
    echo "$PREFIXES"
    echo ""

    # Download each matching prefix
    for PREFIX in $PREFIXES; do
        # Remove trailing slash
        PREFIX_CLEAN="${PREFIX%/}"
        echo "----------------------------------------"
        echo "Downloading: $PREFIX_CLEAN"
        echo "----------------------------------------"

        # Download to maintain directory structure
        eval aws s3 sync "s3://$BUCKET_NAME/$PREFIX_CLEAN/" "$DOWNLOAD_DIR/$PREFIX_CLEAN/" $EXCLUDE_ARGS

        echo ""
    done
else
    # Download specific batch
    # Find directories that match the test prefix and batch number
    PREFIXES=$(aws s3 ls "s3://$BUCKET_NAME/" | grep "PRE" | awk '{print $2}' | grep "^${TEST_PREFIX}" | grep "_batch${BATCH}_")

    if [[ -z "$PREFIXES" ]]; then
        echo "Error: No directories found matching prefix '$TEST_PREFIX' with batch $BATCH in bucket '$BUCKET_NAME'"
        exit 1
    fi

    echo "Found matching directories for batch $BATCH:"
    echo "$PREFIXES"
    echo ""

    # Download each matching prefix
    for PREFIX in $PREFIXES; do
        # Remove trailing slash
        PREFIX_CLEAN="${PREFIX%/}"
        echo "----------------------------------------"
        echo "Downloading: $PREFIX_CLEAN"
        echo "----------------------------------------"

        # Download to maintain directory structure
        eval aws s3 sync "s3://$BUCKET_NAME/$PREFIX_CLEAN/" "$DOWNLOAD_DIR/$PREFIX_CLEAN/" $EXCLUDE_ARGS

        echo ""
    done
fi

echo "======================================"
echo "Download completed!"
echo "Files saved to: $DOWNLOAD_DIR"
echo "======================================"