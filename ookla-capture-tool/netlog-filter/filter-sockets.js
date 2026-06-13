
const { checkFilePath, readFileSync, writeFileSync, deleteFile, parseJSONFromFile } = require('./file-utils');
const fs = require('fs');


const processHttpStreamJobIds = (path, filePath, urlPath, directory, testType, logEvent_ids) => {
    http_stream_job_ids = [];
    // Resolve absolute path to upload directory based on urlPath
    const absoluteUrlPath = path.resolve(urlPath);
    const uploadDir = path.dirname(absoluteUrlPath);
    let currentPosListPath;
    // Paths inside the upload directory
    if (testType == "upload") {
        currentPosListPath = path.join(uploadDir, "current_position_list.json");
    } else {
        currentPosListPath = path.join(uploadDir, "byte_time_list.json");
    }


    const uploadDirPath = path.join(uploadDir, 'httpStreamJobIds.json');

    try {
        // Validate required files
        checkFilePath(filePath);
        checkFilePath(absoluteUrlPath); // urlPath (upload_urls.json)
        checkFilePath(currentPosListPath);

        // Read and parse the main file
        const data = readFileSync(filePath);
        const parsedData = JSON.parse(data);
        const events = parsedData.events;

        // Read current position list
        const currentPosList = parseJSONFromFile(currentPosListPath);
        const list = currentPosList.map(item => item.id);
        console.log("The ids of the http streams are: ", list);
        events.forEach((eventData, index) => {
            if (
                eventData.type === logEvent_ids['HTTP_STREAM_REQUEST_BOUND_TO_JOB'] &&
                eventData.params?.source_dependency &&
                list.includes(eventData.source?.id)
            ) {
                http_stream_job_ids.push([eventData.source.id, eventData.params.source_dependency.id]);
            }
        });

    } catch (error) {
        console.error("Error:", error);
    } finally {
        if (fs.existsSync(uploadDirPath)) {
            console.log(`\nNote: httpStreamJobIds.json already exists in ${directory}`);
        }
        writeFileSync(path.join(directory, 'httpStreamJobIds.json'), JSON.stringify(http_stream_job_ids, null, 2));
    }
};

/**
For every http stream ID, there is an entry.
//An example entry is [ 5781, 5783, 5759 ] where 5781 is the http stream source ID, 5783 is the source dependency ID, and 5759 is the socket ID
*/
const processSocketIds = (path, filePath, urlPath, directory, logEvent_ids) => {
    socketIds = [];
    // Resolve absolute path to upload directory based on urlPath
    const absoluteUrlPath = path.resolve(urlPath);
    const uploadDir = path.dirname(absoluteUrlPath);

    // Paths inside the upload directory
    const httpStreamIdsPath = path.join(uploadDir, 'httpStreamJobIds.json');
    const socketIdsPath = path.join(uploadDir, 'socketIds.json');

    try {
        // Validate required files
        checkFilePath(filePath);
        checkFilePath(httpStreamIdsPath);

        // Read and parse the main file
        const data = readFileSync(filePath);
        const parsedData = JSON.parse(data);
        const events = parsedData.events;

        // Read http stream job IDs
        const httpstreamJobs = JSON.parse(readFileSync(httpStreamIdsPath));

        if (httpstreamJobs.length !== 0) {
            // Parse the HTTP stream jobs
            httpstreamList = httpstreamJobs.map(item => item[1]);
            httpsourceID = httpstreamJobs.map(item => item[0]);

            //event type SOCKET_POOL_BOUND_TO_SOCKET -- 114(michwave) -->114(spacelink) --> 112(merit)
            events.forEach((eventData, index) => {
                if (eventData.hasOwnProperty('params') &&
                    eventData.params.hasOwnProperty('source_dependency') &&
                    eventData.type === logEvent_ids['SOCKET_POOL_BOUND_TO_SOCKET']) {
                    const eventIndex = httpstreamList.indexOf(eventData.source.id);
                    if (eventIndex !== -1) {
                        socketIds.push([
                            httpsourceID[eventIndex],
                            httpstreamList[eventIndex],
                            eventData.params.source_dependency.id
                        ]);
                    }
                }
            });
        }

    } catch (error) {
        console.error("Error:", error);
    } finally {
        // Write to socketIds.json in the upload directory
        writeFileSync(path.join(directory, 'socketIds.json'), JSON.stringify(socketIds, null, 2));
    }
};

// --------------------Legacy functions for socket processing --------------------
/**
 * This function normalizes test data for upload and download tests. This is now performed in the data analysis portion of the pipeline.
 * @param {*} byteFile
 * @param {*} currentFile
 * @param {*} latencyFile
 * @returns
 */
const normalizeTestData = (byteFile, currentFile, latencyFile) => {
    // Load byte list first to determine test type
    let byteList = loadJson(byteFile);
    console.log("The length of byteList is:", byteList.length); // Verify byteList is loaded correctly

    let testType = null;

    if (byteList.length === 0) { // For upload test
        testType = "upload";
        const currentList = loadJson(currentFile);
        console.log("Length of current position list:", currentList.length);

        // Transform cumulative data into incremental byte data
        byteList = currentList.map(item => {
            let newProgress = [];
            let prevPosition = 0; // Initialize the previous position

            item.progress.forEach(progress => {
                const currentPosition = progress.current_position;
                const time = progress.time;

                // Difference between positions is the number of bytes transferred
                const bytesTransferred = currentPosition - prevPosition;
                prevPosition = currentPosition; // Update previous position

                // Add the incremental data to the new progress list
                newProgress.push({ bytecount: bytesTransferred, time: time });
            });

            // Return the transformed item
            return {
                id: item.id,
                type: item.type,
                progress: newProgress
            };
        });
    } else { // For download test
        testType = "download";

        // Load the latency file only if it exists (unloaded latency is optional)
        if (fs.existsSync(latencyFile)) {
            const latencyData = loadJson(latencyFile);
            console.log("Latency loaded");
            console.log("Size of latency list:", latencyData.length, "\n");

            // Create a dictionary to map IDs to the first receive time from the latency file
            const latencyTimeMap = {};
            latencyData.forEach(entry => {
                if (entry.recv_time && entry.recv_time.length > 0) {
                    latencyTimeMap[entry.sourceID] = parseInt(entry.recv_time[0]);
                }
            });
            console.log("Unique source IDs:", Object.keys(latencyTimeMap).length);

            // For every unique source ID, prepend a zero-byte entry with the first receive time
            byteList.forEach(entry => {
                const id = entry.id;
                const progress = entry.progress;

                // If the ID exists in the latency map, prepend the 0th time entry
                if (latencyTimeMap[id]) {
                    const zeroTimeEntry = {
                        bytecount: 0, // Bytecount at recv_time is 0, because no bytes have been received yet
                        time: latencyTimeMap[id]
                    };
                    progress.unshift(zeroTimeEntry); // Prepend to the progress list
                }
            });
        } else {
            console.log("No unloaded latency file found - throughput calculation will not include unloaded latency timing");
            console.log("Only loaded latency (if available) will be used for plotting");
        }
    }

    console.log("Length of byteList after normalization:", byteList.length);
    return { byteList, testType };
};

const processByteCounts = (testType) => {
    /**
     * Collect byte counts at the socket level (layer 4 in TCP/IP model)
     * This was investigated in Spring 2025, but we have since moved away from this investigation.
     */
    const absoluteUrlPath = path.resolve(urlPath);
    const uploadDir = path.dirname(absoluteUrlPath);

    // Paths inside the upload directory
    const socketIdsPath = path.join(uploadDir, "socketIds.json");
    const byteTimeListPath = path.join(uploadDir, "socket_byte_counts.json");

    let byte_time_list = [];

    try {
        // Validate required files
        checkFilePath(filePath);
        checkFilePath(socketIdsPath);

        // Read and parse the main file
        const data = readFileSync(filePath);
        const parsedData = JSON.parse(data);
        const events = parsedData.events;

        // Read socket IDs
        const socketdata = readFileSync(socketIdsPath);

        if (socketdata.length !== 0) {
            // Parse the socket data
            urlSourceID = socketdata.map(item => parseInt(item.split(',')[0]));
            httpID = socketdata.map(item => parseInt(item.split(',')[1]));
            socketID = socketdata.map(item => parseInt(item.split(',')[2]));

            events.forEach((eventData, index) => {
                if (eventData.hasOwnProperty('params') &&
                    eventData.params.hasOwnProperty('byte_count')) {
                    const eventIndex = socketID.indexOf(eventData.source.id);
                    if (eventIndex !== -1) {
                        // Add new entry if socket ID not found
                        if (!byte_time_list.some(item => item.id === socketID[eventIndex])) {
                            byte_time_list.push({
                                id: socketID[eventIndex],
                                type: testType,
                                progress: []
                            });
                        }
                        // Add progress data
                        byte_time_list.find(item =>
                            item.id === socketID[eventIndex]
                        ).progress.push({
                            bytecount: eventData.params.byte_count,
                            time: eventData.time
                        });
                    }
                }
            });
        }
    } catch (error) {
        console.error("Error:", error);
    } finally {
        // process bytes counts at the socket level
        writeFileSync('socket_byte_time_list.json', JSON.stringify(byte_time_list, null, 2));
    }
};

module.exports = {
    processHttpStreamJobIds,
    processSocketIds
};