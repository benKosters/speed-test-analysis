/**
 * Standalone script to process byte counts at socket level for existing test data
 * Takes the parent directory containing both upload and download subdirectories
 *
 * Usage: node collect-socket-level-bytecounts.js <parent_test_directory>
 *
 * The parent_test_directory should contain:
 * - netlog.json (shared netlog file)
 * - upload/ subdirectory with socketIds.json
 * - download/ subdirectory with socketIds.json
 */

const fs = require('fs');
const path = require('path');
const { checkFilePath, readFileSync, writeFileSync, mapEventNamesToIds } = require('./file-utils');

// Check if correct arguments were provided
if (process.argv.length !== 3) {
    console.log("Usage: node collect-socket-level-bytecounts.js <parent_test_directory>");
    process.exit(1);
}

const parentTestDirectory = process.argv[2];

// Validate parent test directory exists
if (!fs.existsSync(parentTestDirectory)) {
    console.error(`Error: Parent test directory '${parentTestDirectory}' does not exist`);
    process.exit(1);
}

console.log(`Processing socket-level byte counts for test: ${path.basename(parentTestDirectory)}`);
console.log(`Parent directory: ${parentTestDirectory}`);

const processByteCounts = (netlogPath, socketIdsPath, outputDir, testType) => {
    /**
     * Collect byte counts at the socket level (layer 4 in TCP/IP model)
     */
    let byte_time_list = [];

    try {
        // Validate required files
        checkFilePath(netlogPath);
        checkFilePath(socketIdsPath);

        console.log("Reading netlog file:", netlogPath);
        console.log("Reading socket IDs from:", socketIdsPath);

        // Read and parse the main netlog file
        const data = readFileSync(netlogPath);
        const parsedData = JSON.parse(data);
        const events = parsedData.events;

        logEventIds = {};
        mapEventNamesToIds(parsedData.constants.logEventTypes, logEventIds);

        // Read socket IDs
        const socketdata = JSON.parse(readFileSync(socketIdsPath));

        let urlSourceID, httpID, socketID;

        if (socketdata.length !== 0) {
            // Parse the socket data - handle both array of strings and array of objects
            if (typeof socketdata[0] === 'string') {
                // Format: ["urlSourceID,httpID,socketID", ...]
                urlSourceID = socketdata.map(item => parseInt(item.split(',')[0]));
                httpID = socketdata.map(item => parseInt(item.split(',')[1]));
                socketID = socketdata.map(item => parseInt(item.split(',')[2]));
            } else {
                // Handle object format if different
                urlSourceID = socketdata.map(item => parseInt(item.urlSourceID || item[0]));
                httpID = socketdata.map(item => parseInt(item.httpID || item[1]));
                socketID = socketdata.map(item => parseInt(item.socketID || item[2]));
            }

            console.log(`Processing ${events.length} events...`);
            console.log(`Found ${socketID.length} socket mappings`);

            // Determine which event type to look for based on test type
            const targetEventType = testType === 'upload' ? logEventIds["SOCKET_BYTES_SENT"] : logEventIds["SOCKET_BYTES_RECEIVED"];

            let processedEvents = 0;

            events.forEach((eventData, index) => {
                if (eventData.hasOwnProperty('params') &&
                    eventData.params.hasOwnProperty('byte_count') &&
                    eventData.type === targetEventType) {

                    const eventIndex = socketID.indexOf(eventData.source.id);
                    if (eventIndex !== -1) {
                        processedEvents++;

                        // Add new entry if socket ID not found
                        if (!byte_time_list.some(item => item.id === socketID[eventIndex])) {
                            byte_time_list.push({
                                id: socketID[eventIndex],
                                type: testType,
                                progress: []
                            });
                        }

                        // Add progress data
                        const socketEntry = byte_time_list.find(item => item.id === socketID[eventIndex]);
                        socketEntry.progress.push({
                            bytecount: eventData.params.byte_count,
                            time: eventData.time
                        });
                    }
                }
            });

            console.log(`Processed ${processedEvents} byte count events`);
            console.log(`Generated data for ${byte_time_list.length} unique sockets`);

        } else {
            console.warn("Warning: socketIds.json is empty");
        }

    } catch (error) {
        console.error("Error processing byte counts:", error);
        throw error;
    }

    // Write output file
    const outputPath = path.join(outputDir, 'socket_byte_time_list.json');
    writeFileSync(outputPath, JSON.stringify(byte_time_list, null, 2));
    console.log(`Socket byte counts written to: ${outputPath}`);

    return byte_time_list;
};

// Validate directory structure
const netlogPath = path.join(parentTestDirectory, 'netlog.json');
const uploadDir = path.join(parentTestDirectory, 'upload');
const downloadDir = path.join(parentTestDirectory, 'download');

// Check required files and directories exist
if (!fs.existsSync(netlogPath)) {
    console.error(`Error: netlog.json not found in ${parentTestDirectory}`);
    process.exit(1);
}

if (!fs.existsSync(uploadDir)) {
    console.error(`Error: upload/ directory not found in ${parentTestDirectory}`);
    process.exit(1);
}

if (!fs.existsSync(downloadDir)) {
    console.error(`Error: download/ directory not found in ${parentTestDirectory}`);
    process.exit(1);
}

const processSpecificTestType = (testDir, testType) => {
    console.log(`\n=== Processing ${testType.toUpperCase()} Test ===`);

    const socketIdsPath = path.join(testDir, 'socketIds.json');

    if (!fs.existsSync(socketIdsPath)) {
        console.error(`Error: socketIds.json not found in ${testDir}`);
        return null;
    }

    console.log(`Test directory: ${testDir}`);
    console.log(`Socket IDs file: ${socketIdsPath}`);
    console.log(`Shared netlog file: ${netlogPath}`);

    try {
        const result = processByteCounts(netlogPath, socketIdsPath, testDir, testType);
        console.log(`Successfully processed ${testType} test - generated data for ${result.length} sockets`);
        return result;
    } catch (error) {
        console.error(`Error processing ${testType} test:`, error.message);
        return null;
    }
};

// Main execution - no longer need processTestDirectory function
const processParentDirectory = () => {
    const uploadDir = path.join(baseDir, 'upload');
    const downloadDir = path.join(baseDir, 'download');

    // Check if we're processing a specific upload/download directory
    if (testDirectory.endsWith('/upload') || testDirectory.endsWith('\\upload')) {
        return processSpecificDirectory(testDirectory, 'upload');
    } else if (testDirectory.endsWith('/download') || testDirectory.endsWith('\\download')) {
        return processSpecificDirectory(testDirectory, 'download');
    }

    // Otherwise process both if they exist
    let results = [];

    if (fs.existsSync(uploadDir)) {
        console.log("\n=== Processing Upload Directory ===");
        results.push(processSpecificDirectory(uploadDir, 'upload'));
    }

    if (fs.existsSync(downloadDir)) {
        console.log("\n=== Processing Download Directory ===");
        results.push(processSpecificDirectory(downloadDir, 'download'));
    }

    if (results.length === 0) {
        console.error("No upload or download directories found in:", baseDir);
        process.exit(1);
    }

    return results;
};



// Main execution
try {
    console.log(`\nFound shared netlog file: ${netlogPath}`);
    console.log(`Processing both upload and download tests...\n`);

    const results = [];

    // Process upload test
    const uploadResult = processSpecificTestType(uploadDir, 'upload');
    if (uploadResult) {
        results.push({ type: 'upload', sockets: uploadResult.length });
    }

    // Process download test
    const downloadResult = processSpecificTestType(downloadDir, 'download');
    if (downloadResult) {
        results.push({ type: 'download', sockets: downloadResult.length });
    }

    // Final summary
    console.log("\n" + "=".repeat(50));
    console.log("PROCESSING COMPLETE");
    console.log("=".repeat(50));

    if (results.length === 0) {
        console.log("❌ No tests were processed successfully");
        process.exit(1);
    } else {
        console.log(`✅ Successfully processed ${results.length} test(s):`);
        results.forEach(result => {
            console.log(`   - ${result.type}: ${result.sockets} sockets`);
        });

        console.log(`\nOutput files created:`);
        results.forEach(result => {
            const outputFile = path.join(parentTestDirectory, result.type, 'socket_byte_time_list.json');
            console.log(`   - ${outputFile}`);
        });
    }

} catch (error) {
    console.error("Processing failed:", error.message);
    process.exit(1);
}