/**
 * Main driver for netlog filtering
 *
 * Usage:
 *   node main.js <path_to_test_directory>
 *   node main.js <path_to_netlog_file>
 *
 * Steps:
 * 1. Filter URLs from netlog.json
 * 2. Filter bytecount/latency data for download
 * 3. Filter bytecount/latency data for upload
 * 4. TODO: Filter CPU data here?
 */

const path = require('path');
const fs = require('fs');
const { filterUrls } = require('./filter-urls');
const { filterCpuData } = require('./filter-cpu-data')
const { processNetlogFile } = require('./netlog-processing')

function parseCLIArgs() {
    if (process.argv.length < 3) {
        console.error('Error: Please provide a path to test directory or netlog file');
        console.error('Usage: node main.js <path_to_test_directory_or_netlog_file> [-upload | -download]');
        console.error('Example: node main.js /path/michwave-multi-2026-01-27_1722/');
        console.error('Example: node main.js /path/to/test/michwave-multi-2026-01-27_1722/netlog.json');
        console.error('Example: node main.js /path/to/test/directory/ -download');
        console.error('Example: node main.js /path/to/test/directory/ -upload');
        process.exit(1);
    }

    const args = process.argv.slice(2);
    let netlogPath = null;
    let filterMode = null;

    for (const arg of args) {
        if (arg === '-upload' || arg === '-download') {
            if (filterMode !== null) {
                throw new Error('Cannot specify both -upload and -download flags');
            }
            filterMode = arg.substring(1); // Remove the '-' prefix
        } else if (!arg.startsWith('-')) {
            netlogPath = arg;
        } else {
            throw new Error(`Unknown flag: ${arg}`);
        }
    }

    if (!netlogPath) {
        throw new Error('No path provided');
    }

    return { netlogPath, filterMode };
}

function resolveNetlogPath(inputPath) {
    if (!fs.existsSync(inputPath)) {
        throw new Error(`Path does not exist: ${inputPath}`);
    }

    const stats = fs.statSync(inputPath);

    if (stats.isDirectory()) {
        // If directory, look for netlog.json inside
        const netlogPath = path.join(inputPath, 'netlog.json');
        if (!fs.existsSync(netlogPath)) {
            throw new Error(`netlog.json not found in directory: ${inputPath}`);
        }
        return netlogPath;
    } else if (stats.isFile()) {
        // If file, verify it's a .json file
        if (!inputPath.endsWith('.json')) {
            throw new Error(`Expected a .json file, got: ${inputPath}`);
        }
        return inputPath;
    }

    throw new Error(`Invalid path: ${inputPath}`);
}

/**
 * Main execution function
 */
function main() {

    try {
        const { netlogPath, filterMode } = parseCLIArgs();
        const netlogFilePath = resolveNetlogPath(netlogPath);
        // Step 1: Filter URLs
        console.log('\nStep 1: Filtering URLs from netlog.');
        console.log('='.repeat(60));
        const urlResults = filterUrls(netlogFilePath);

        downloadUrlsPath = urlResults.downloadUrlsPath;
        uploadUrlsPath = urlResults.uploadUrlsPath;

        // TODO: Step 2 - Filter download data
        console.log('\nStep 2: Filtering download data.');
        console.log('='.repeat(60));
        processNetlogFile(netlogFilePath, urlResults.downloadUrlsPath, "download");

        // TODO: Step 3 - Filter upload data
        console.log('\nStep 3: Filtering upload data.');
        console.log('='.repeat(60));
        processNetlogFile(netlogFilePath, urlResults.uploadUrlsPath, "upload");

        // // TODO: Step 4 - Filter CPU data. Does this need to be done here or should it be done as part of processing?
        // console.log('\nSTEP 4: Filtering CPU data...');
        // filterCpuData(path.dirname(netlogFilePath));

        console.log('\n' + '='.repeat(60));
        console.log('All filtering steps completed.');

    }
    catch (error) {
        console.error('\nError:', error.message);
        process.exit(1);
    }
}

if (require.main === module) {
    main();
}

module.exports = { main };