/**
 * This program is used to extract relevant data from netlog files generated during a conventional Ookla speed test.
 *
 *
 * The script is run this way: node filter-netlog-data.js <path_to_netlog_file> <path_to_urls_file>
 *
 * This event filtering script can be used for both download and upload, and these are the files produced:
 * For download:
 *      1) byte_time_list.json - the byte counts divided by http stream/source
 *      2) unloaded_latency.json - the unloaded latency for each http stream/source
 *      3) loaded_latency.json - the loaded latency for each http stream/source
 *      4) socket_byte_time_list.sjon (the byte counts divided by socket instead of by http stream)
 *      6) socketIds.txt - the socket IDs associated with each http stream ID
 *
 * For upload:
 *      1) current_position_list.json
 *      2) latency.json
 *      3) loaded_latency.json
 *      4) socket_byte_time_list.json
 *      5) socketIds.txt
 *
 */

//Import the filesystem and path modules
const fs = require('fs');
const path = require('path');
const { checkFilePath, readFileSync, writeFileSync, deleteFile, parseJSONFromFile, mapEventNamesToIds } = require('./file-utils');
const logEvent_ids = {}; //maps Netlog event names to a number (their IDs) - these IDs change for each test, but the names remain the same

// Check if file paths were provided
if (process.argv.length != 4) {
    console.log("Usage: node filter-netlog-data.js <path_to_netlog_file> <path_to_urls_file>");
    process.exit(1);
}

// Get file path from command line argument
const filePath = process.argv[2];
const urlPath = process.argv[3];
let directory;
let testType = "";

// Check if the files exist
checkFilePath(filePath);
checkFilePath(urlPath);

// Get the directory that the url file is in (this is where we want to place the output)
directory = path.dirname(urlPath);
console.log("Output files will be written to:", directory);
const urlJSON = parseJSONFromFile(urlPath);

//Function that returns the test type, as well as the split urls
const splitTestTypeUrls = (urlJSON) => {
    let split_urls = [], split_unloaded_urls = [], split_loaded_urls = [];
    let testUrls = [];
    if (urlJSON.download.length > 0) {
        testType = 'download';
        testUrls = urlJSON.download;
    } else if (urlJSON.upload.length > 0) {
        testType = 'upload';
        testUrls = urlJSON.upload;
    }

    for (var i = 0; i < testUrls.length; i++) {
        var parts = testUrls[i].split("/");
        var split_url = parts.slice(3).join("/");
        split_urls.push(split_url);
    }

    if (urlJSON.unload.length > 0) {
        for (var i = 0; i < urlJSON.unload.length; i++) {
            var parts = urlJSON.unload[i].split("/");
            var split_url = parts.slice(3).join("/");
            split_unloaded_urls.push(split_url);
        }
    }
    if (urlJSON.load.length > 0) {
        for (var i = 0; i < urlJSON.load.length; i++) {
            var parts = urlJSON.load[i].split("/");
            var split_url = parts.slice(3).join("/");
            split_loaded_urls.push(split_url);
        }
    }
    console.log("Example", testType, "split URL:", split_urls[0]);
    console.log("Example loaded split URL:", split_loaded_urls[0]);
    console.log("Example unloaded split URL:", split_unloaded_urls[0])
    return { split_urls: split_urls, split_unloaded_urls: split_unloaded_urls, split_loaded_urls: split_loaded_urls };
};

const captureThroughputData = (eventData, results, byte_time_list, current_position_list, testType, logEvent_ids) => {
    // Check if this event belongs to a recognized source from the speed test server
    if (!results.some(result => result.sourceID && result.sourceID.id === eventData.source.id)) {
        return;
    }

    // Download events
    if (((eventData.type === logEvent_ids['URL_REQUEST_JOB_FILTERED_BYTES_READ']) ||
        (eventData.type === logEvent_ids['URL_REQUEST_BYTES_READ'])) &&
        eventData.hasOwnProperty('params') &&
        (testType == "download") &&
        eventData.params.hasOwnProperty('byte_count')) {

        let existingIdIndex = byte_time_list.findIndex(item => item.id === eventData.source.id);
        if (existingIdIndex === -1) {
            // If id does not exist, add it to byte_time_list (progress will store an object containing the byte_count and timestamp)
            byte_time_list.push({ id: eventData.source.id, type: testType, progress: [] });
            existingIdIndex = byte_time_list.length - 1;
        }
        // Push new progress values
        byte_time_list[existingIdIndex].progress.push({ bytecount: eventData.params.byte_count, time: eventData.time });

        // Debug logging (can be removed in production)
        if (eventData.params.hasOwnProperty('source_dependency') && eventData.type === 160) {
            // console.log(eventData.params.source_dependency.id);
        }
    }
    // Upload events
    else if (eventData.type === logEvent_ids['UPLOAD_DATA_STREAM_READ'] &&
        eventData.hasOwnProperty('params') &&
        (testType == "upload") &&
        eventData.params.hasOwnProperty('current_position')) {

        let existingIdIndex = current_position_list.findIndex(item => item.id === eventData.source.id);
        if (existingIdIndex === -1) {
            // If id does not exist, add it to current_position_list
            current_position_list.push({ id: eventData.source.id, type: testType, progress: [] });
            existingIdIndex = current_position_list.length - 1;
        }
        // Push new progress values (larger uploads may have multiple events recording current position, similar to how large downloads may have multiple events for byte_count)
        current_position_list[existingIdIndex].progress.push({ current_position: eventData.params.current_position, time: eventData.time });
    }
};

const captureLatencyData = (eventData, latencyStreams, urlList, eventType) => {
    const sourceId = eventData.source.id;
    const time = Number(eventData.time);

    // Find existing stream or create new one
    let existingStream = latencyStreams.find(item => item.id === sourceId);

    if (!existingStream) {
        existingStream = {
            id: sourceId,
            send_time: null,
            recv_time: null,
            rtt: null
        };
        latencyStreams.push(existingStream);
    }

    // Handle send time - event 176 (HTTP_TRANSACTION_SEND_REQUEST_HEADERS)
    if (eventData.type === logEvent_ids['HTTP_TRANSACTION_SEND_REQUEST_HEADERS'] &&
        eventData.params?.line) {
        existingStream.send_time = time;
    }

    // Handle receive time - event 181 (HTTP_TRANSACTION_READ_RESPONSE_HEADERS)
    if (eventData.type === logEvent_ids['HTTP_TRANSACTION_READ_RESPONSE_HEADERS']) {
        existingStream.recv_time = time;
        // Calculate RTT if we have both times
        if (existingStream.send_time !== null && existingStream.recv_time !== null) {
            existingStream.rtt = existingStream.recv_time - existingStream.send_time;
        }
    }
};

const calculateLatencyStatistics = (latencyStreams) => {
    // Make sure both send and receive times are present
    const validRtts = latencyStreams
        .filter(stream => stream.rtt !== null && stream.rtt >= 0)
        .map(stream => stream.rtt);

    if (validRtts.length === 0) {
        return {
            count_rtt: 0,
            mean_rtt: 0,
            median_rtt: 0
        };
    }

    const count_rtt = validRtts.length;

    const sum = validRtts.reduce((acc, rtt) => acc + rtt, 0);
    const mean_rtt = sum / count_rtt;

    const sortedRtts = [...validRtts].sort((a, b) => a - b);
    let median_rtt;

    if (sortedRtts.length % 2 === 0) {
        // Even number of values - average of middle two
        const mid1 = sortedRtts[sortedRtts.length / 2 - 1];
        const mid2 = sortedRtts[sortedRtts.length / 2];
        median_rtt = (mid1 + mid2) / 2;
    } else {
        median_rtt = sortedRtts[Math.floor(sortedRtts.length / 2)];
    }

    return {
        count_rtt: count_rtt,
        mean_rtt: Math.round(mean_rtt * 100) / 100,
        median_rtt: Math.round(median_rtt * 100) / 100
    };
};

const updateAllLatencyStatistics = (latency_data) => {
    latency_data.test_latency.latency_ms = calculateLatencyStatistics(latency_data.test_latency.streams);
    latency_data.unloaded_latency.latency_ms = calculateLatencyStatistics(latency_data.unloaded_latency.streams);
    latency_data.loaded_latency.latency_ms = calculateLatencyStatistics(latency_data.loaded_latency.streams);

    console.log("\nLatency metrics using GET and POST URLs:")
    console.log("Test latency statistics:", latency_data.test_latency.latency_ms);
    console.log("Unloaded latency statistics:", latency_data.unloaded_latency.latency_ms);
    console.log("Loaded latency statistics:", latency_data.loaded_latency.latency_ms);
};

// Immediately invoked anonomous function to read the contents of the Netlog file
(() => {
    try {
        const data = readFileSync(filePath);
        const parsedData = JSON.parse(data);
        const netlog_constants = parsedData.constants;
        const events = parsedData.events;

        const byte_time_list = []; //For download data
        const current_position_list = []; //For upload data
        const results = [];

        const latency_data = {
            "test_latency": {
                "streams": [],
                "latency_ms": {
                    "count_rtt": 0,
                    "mean_rtt": 0,
                    "median_rtt": 0
                }
            },
            "unloaded_latency": {
                "streams": [],
                "latency_ms": {
                    "count_rtt": 0,
                    "mean_rtt": 0,
                    "median_rtt": 0
                }
            },
            "loaded_latency": {
                "streams": [],
                "latency_ms": {
                    "count_rtt": 0,
                    "mean_rtt": 0,
                    "median_rtt": 0
                }
            }
        };

        if (!events || !netlog_constants) {
            console.error("The Netlog data or constants are missing");
            process.exit(1);
        }

        mapEventNamesToIds(netlog_constants.logEventTypes, logEvent_ids);
        const { split_urls, split_unloaded_urls, split_loaded_urls } = splitTestTypeUrls(urlJSON);

        console.log(testType, "URLs found: ", split_urls.length);
        console.log("Unload URLs found: ", split_unloaded_urls.length);
        console.log("Load URLs found: ", split_loaded_urls.length);

        //Begin parsing each event in the Netlog data.
        events.forEach((eventData, index) => {
            try {

                /*Check #1
                The proper event we are looking for must have:
                    1) a 'params' field that is also an object, and it must contain a url field
                    2) one of the form URLs from netlog_urls matches and the event type must be type 2(REQUEST_ALIVE)

                    If these conditions are met, this means this event is one of the first events in an event stream where the speed test server is the source.
                    We will then need to look for other events from this source in order to glean data for calculating throughput and latency.
                */
                if (
                    eventData.hasOwnProperty('params') &&
                    typeof (eventData.params) === 'object' &&
                    eventData.params.hasOwnProperty('url') &&
                    split_urls.some(url => eventData.params.url.includes(url) &&
                        eventData.type === logEvent_ids['REQUEST_ALIVE']
                    )
                ) {
                    if (eventData.source.hasOwnProperty('id')) {
                        const id = eventData.source;
                        results.push({ sourceID: id, index: index, dict: eventData }); //by including the entire event data, the source info is present twice. Interesting...
                        //console.log({ sourceID: id, index: index, dict: eventData });
                    }

                }

                /**check #2:
                Collect byte counts for computing throughput
                */
                if (
                    results.some(result => result.sourceID && result.sourceID.id === eventData.source.id)
                ) {
                    captureThroughputData(eventData, results, byte_time_list, current_position_list, testType, logEvent_ids);
                }

                // check #3 --> UNLOADED latency (hello URLs)
                if (eventData.hasOwnProperty('params') &&
                    typeof (eventData.params) === 'object' &&
                    split_unloaded_urls.length > 0) {

                    // Handle send events (type 176) with URL matching
                    if (eventData.type === logEvent_ids['HTTP_TRANSACTION_SEND_REQUEST_HEADERS'] &&
                        eventData.params.hasOwnProperty('line') &&
                        split_unloaded_urls.some(url => String(eventData.params.line).includes(url))) {
                        captureLatencyData(eventData, latency_data.unloaded_latency.streams, split_unloaded_urls, 'unloaded');
                    }

                    // Handle receive events (type 181) - only if source already exists from send event
                    if (eventData.type === logEvent_ids['HTTP_TRANSACTION_READ_RESPONSE_HEADERS'] &&
                        latency_data.unloaded_latency.streams.some(stream => stream.id === eventData.source.id)) {
                        captureLatencyData(eventData, latency_data.unloaded_latency.streams, split_unloaded_urls, 'unloaded');
                    }
                }

                // check #4 --> LOADED latency
                if (eventData.hasOwnProperty('params') &&
                    typeof (eventData.params) === 'object' &&
                    split_loaded_urls.length > 0) {

                    // Handle send events (type 176) with URL matching
                    if (eventData.type === logEvent_ids['HTTP_TRANSACTION_SEND_REQUEST_HEADERS'] &&
                        eventData.params.hasOwnProperty('line') &&
                        split_loaded_urls.some(url => String(eventData.params.line).includes(url))) {
                        captureLatencyData(eventData, latency_data.loaded_latency.streams, split_loaded_urls, 'loaded');
                    }

                    // Handle receive events (type 181) - only if source already exists from send event
                    if (eventData.type === logEvent_ids['HTTP_TRANSACTION_READ_RESPONSE_HEADERS'] &&
                        latency_data.loaded_latency.streams.some(stream => stream.id === eventData.source.id)) {
                        captureLatencyData(eventData, latency_data.loaded_latency.streams, split_loaded_urls, 'loaded');
                    }
                }

                // check #5 --> TEST latency (download/upload URLs)
                if (eventData.hasOwnProperty('params') &&
                    typeof (eventData.params) === 'object' &&
                    split_urls.length > 0) {

                    // Handle send events (type 176) with URL matching
                    if (eventData.type === logEvent_ids['HTTP_TRANSACTION_SEND_REQUEST_HEADERS'] &&
                        eventData.params.hasOwnProperty('line') &&
                        split_urls.some(url => String(eventData.params.line).includes(url))) {
                        captureLatencyData(eventData, latency_data.test_latency.streams, split_urls, 'test');
                    }

                    // Handle receive events (type 181) - only if source already exists from send event
                    if (eventData.type === logEvent_ids['HTTP_TRANSACTION_READ_RESPONSE_HEADERS'] &&
                        latency_data.test_latency.streams.some(stream => stream.id === eventData.source.id)) {
                        captureLatencyData(eventData, latency_data.test_latency.streams, split_urls, 'test');
                    }
                }

            } catch (error) {
                console.error("Error parsing line", index, ":", error);
            }
        });
        updateAllLatencyStatistics(latency_data);

        // Write byte_time_list (id, type, and progress [{bytecount, timestamp}]
        writeFileSync(path.join(directory, 'byte_time_list.json'), JSON.stringify(byte_time_list, null, 2));

        //write loaded latency send an receive time to loaded_latency.json
        writeFileSync(path.join(directory, 'latency_data.json'), JSON.stringify(latency_data, null, 2));

        //if type is upload, write the current_position_list to a file
        if (testType == "upload") {
            writeFileSync(path.join(directory, 'current_position_list.json'), JSON.stringify(current_position_list, null, 2));
        }

    } catch (error) {
        console.error("Error reading the file:", error);
    }
})();

/**
 Writes these source dependancy IDs to httpStreamJobIds.txt.
Example HTTP stream job entry: [ 5781, 5783 ] where 5781 is the http stream ID and 5783 is the source dependency ID
 */
const processHttpStreamJobIds = () => {
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
const processSocketIds = () => {
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

const processByteCounts = () => {
    /**
     * Collect byte counts at the socket level (layer 4 in TCP/IP model)
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

console.log("Testing url type:", testType);
processHttpStreamJobIds();
processSocketIds();
//At this point in time, we are only looking at the byte counts at the socket level for upload tests only.
// if (testType == "upload") {
//     processByteCounts();
// }

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
