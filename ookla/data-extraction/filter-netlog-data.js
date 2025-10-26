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
const { checkFilePath, readFileSync, writeFileSync, deleteFile, parseJSONFromFile } = require('./file-utils');
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

// Check if the files exist
checkFilePath(filePath);
checkFilePath(urlPath);

// Get the directory that the url file is in (this is where we want to place the output)
directory = path.dirname(urlPath);
console.log("Output files will be written to:", directory);

const getUrlTypeAndForm = (urlJSON) => {
    let urltype = "", urltype2 = "", form = [], form2 = [];
    // Check for latency URLs - prioritize idle_latency over older unload field
    if (urlJSON.idle_latency && urlJSON.idle_latency.length > 0) {
        urltype2 = "unload";  // Keep internal naming as "unload" for consistency
        form2 = urlJSON.idle_latency;
    } else if (urlJSON.load.length > 0) {
        urltype2 = "load";
        form2 = urlJSON.load;
    } else if (urlJSON.unload.length > 0) {
        urltype2 = "unload";
        form2 = urlJSON.unload;
    }

    if (urlJSON.download.length > 0) {
        urltype = "download";
        form = urlJSON.download;
    } else if (urlJSON.upload.length > 0) {
        urltype = "upload";
        form = urlJSON.upload;
    }

    //You can either have only one url type or two (download/upload and load/unload)
    if (urltype) {
        if (urltype2) {
            return { count: 2, urltype: urltype, form: form, urltype2: urltype2, form2: form2 }
        }
        else {
            return { count: 1, urltype: urltype, form: form }
        }
    }
    else {
        return { count: 1, urltype: urltype2, form: form2 };
    }
};


const urlJSON = parseJSONFromFile(urlPath);
const urlTypeAndForm = getUrlTypeAndForm(urlJSON);
let urltype, form, urltype2, form2
if (urlTypeAndForm.count === 1) {
    urltype = urlTypeAndForm.urltype;
    form = urlTypeAndForm.form
} else {
    urltype = urlTypeAndForm.urltype;
    form = urlTypeAndForm.form;
    urltype2 = urlTypeAndForm.urltype2;
    form2 = urlTypeAndForm.form2;
}

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
        const unloaded_latency = [];//for UNLOADED latency
        const loaded_latency = [];//For loaded latency

        const latency_data = {
            "unloaded_latency": {
                "streams": [],
                "latency_ms": []
            }
            , "loaded_latency": {
                "streams": [],
                "latency_ms": []
            }
        };

        if (!events || !netlog_constants) {
            console.error("The Netlog data or constants are missing");
            process.exit(1);
        }


        const mapEventNamesToIds = (logEventTypes, targetMap) => {
            //Store event names and IDs, as the IDs change for every test
            Object.entries(logEventTypes).forEach(([name, id]) => {
                targetMap[name] = id;
            });
            console.log("Number of event types:", Object.keys(targetMap).length);
        };

        mapEventNamesToIds(netlog_constants.logEventTypes, logEvent_ids);

        // 1) Download/Upload URLS (for throughput calculation)
        //only store the relative attributes of the urls, removing the domain - saves the cache, guid, and size attributes
        //we need this to check for the proper HTTP_TRANSACTION_SEND_REQUEST_HEADERS event for throughput
        //Form contains download/upload urls, form2 contains the load urls
        var split_urls = [];
        if (urltype === "download" || urltype === "upload") {
            for (var i = 0; i < form.length; i++) {
                var parts = form[i].split("/");
                var split_url = parts.slice(3).join("/");
                split_urls.push(split_url);
            }
        }
        console.log("Example split url: ", split_urls[0]);

        // 2) Unload URLS (for unloaded latency calculation)
        var split_unload_urls = [];
        if (urltype === "unload" || urltype2 === "unload") {
            const unload_form = (urltype === "unload") ? form : form2;
            for (var i = 0; i < unload_form.length; i++) {
                var parts = unload_form[i].split("/");
                var split_url = parts.slice(3).join("/");
                split_unload_urls.push(split_url);
            }
        }
        console.log("Example unload url: ", split_unload_urls[0]);

        // 3) Loaded URLS
        // Store the relative attributes of the loaded urls, which we will need for finding the HTTP_TRANSACTION_SEND_REQUEST_HEADERS event
        // of the URL_REQUEST events that measure loaded latency.
        var split_loaded_urls = [];

        // Check for loaded latency URLs - prioritizing loaded_latency over older load field
        if (urlJSON.loaded_latency && urlJSON.loaded_latency.length > 0) {
            for (var i = 0; i < urlJSON.loaded_latency.length; i++) {
                var parts = urlJSON.loaded_latency[i].split("/");
                var split_loaded_url = parts.slice(3).join("/");
                split_loaded_urls.push(split_loaded_url);
            }
        } else if (urltype === "load" || urltype2 === "load") {
            const load_form = (urltype === "load") ? form : form2;
            for (var i = 0; i < load_form.length; i++) {
                var parts = load_form[i].split("/");
                var split_loaded_url = parts.slice(3).join("/");
                split_loaded_urls.push(split_loaded_url);
            }
        }

        console.log(urltype, "URLs found: ", split_urls.length);
        console.log("Unload URLs found: ", split_unload_urls.length);
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
                    form.some(url => eventData.params.url.includes(url) &&
                        eventData.type === logEvent_ids['REQUEST_ALIVE']
                    )
                ) {
                    //if the conditions are met, add entire source(src.id, start_time, type), along with the index and the rest of the event data
                    //We can the use the source ID to find other events with the same id, becuase they also come from the test server.
                    if (eventData.source.hasOwnProperty('id')) {
                        const id = eventData.source;
                        results.push({ sourceID: id, index: index, dict: eventData }); //by including the entire event data, the source info is present twice. Interesting...
                        //console.log({ sourceID: id, index: index, dict: eventData });
                    }

                }

                /**check #4 --> UNLOADED latency (INDEPENDENT OF RESULTS ARRAY)
                To calculate UNLOADED latency, we need to find events that use UNLOAD URLs only
                These are separate small requests made BEFORE the main test to measure baseline idle latency from Ookla.

                This check is independent of the main upload/download events and doesn't require
                the event to be in the results array.
                */
                //Start by checking for unload latency events - only if we have unload URLs
                if (
                    eventData.hasOwnProperty('params') &&
                    typeof (eventData.params) === 'object' &&
                    split_unload_urls.length > 0  // Only process if we have unload URLs
                    && (
                        (eventData.params.hasOwnProperty('line') && split_unload_urls.some(url => String(eventData.params.line).includes(url))) ||
                        (eventData.params.hasOwnProperty('url') && split_unload_urls.some(url => String(eventData.params.url).includes(url)))
                    )
                ) {
                    if (eventData.type === logEvent_ids['HTTP_TRANSACTION_SEND_REQUEST_HEADERS']) {
                        const existingIdIndex = unloaded_latency.findIndex(item => item.sourceID === eventData.source.id);
                        if (existingIdIndex !== -1) {
                            // If id already exists, add to the same dictionary item
                            if (!unloaded_latency[existingIdIndex].send_time) {
                                unloaded_latency[existingIdIndex].send_time = [];
                            }
                            unloaded_latency[existingIdIndex].send_time.push(eventData.time);
                        } else {
                            //add to the list if the id is not already in the list
                            unloaded_latency.push({ sourceID: eventData.source.id, send_time: [eventData.time] });
                        }
                    }
                }
                //If the event is http receive response headers for unload URLs, then add timestamp as "recv_time"
                if (eventData.type === logEvent_ids['HTTP_TRANSACTION_READ_RESPONSE_HEADERS'] &&
                    unloaded_latency.some(item => item.sourceID === eventData.source.id)) {
                    const existingIdIndex = unloaded_latency.findIndex(item => item.sourceID === eventData.source.id);
                    if (existingIdIndex !== -1) {
                        if (!unloaded_latency[existingIdIndex].recv_time) {
                            unloaded_latency[existingIdIndex].recv_time = [];
                        }
                        // If id already exists, add to the same dictionary item
                        unloaded_latency[existingIdIndex].recv_time.push(eventData.time);
                    } else {
                        unloaded_latency.push({ sourceID: eventData.source.id, recv_time: [eventData.time] });
                    }
                }

                /**check #2:
                Now that we have recorded the source ID of the first event in an event stream that came from the server, we can check subsequent events
                to see if they have an ID that matches. If the ID is in the results, we can look to see if it is the right event type.
                If the source is not recognized, it does not come from the speed test server and is irelevant.
                */
                if (
                    results.some(result => result.sourceID && result.sourceID.id === eventData.source.id)
                ) {
                    //check #3a --> Download events
                    if (((eventData.type === logEvent_ids['URL_REQUEST_JOB_FILTERED_BYTES_READ']) || (eventData.type === logEvent_ids['URL_REQUEST_BYTES_READ'])) && eventData.hasOwnProperty('params') && (urltype == "download") && eventData.params.hasOwnProperty('byte_count')) {
                        let existingIdIndex = byte_time_list.findIndex(item => item.id === eventData.source.id);
                        if (existingIdIndex === -1) {
                            // If id does not exist, add it to byte_time_list (progress will store an object containing the byte_count and timestamp)
                            byte_time_list.push({ id: eventData.source.id, type: urltype, progress: [] });
                            existingIdIndex = byte_time_list.length - 1; //
                        }
                        // Push new progress values
                        byte_time_list[existingIdIndex].progress.push({ bytecount: eventData.params.byte_count, time: eventData.time });
                        //type 160 --> used for debugging, this if statement can be ignored
                        if (eventData.params.hasOwnProperty('source_dependency') && eventData.type === 160) {
                            // console.log(eventData.params.source_dependency.id);
                        }
                        //check #3b --> upload events
                    } else if (eventData.type === logEvent_ids['UPLOAD_DATA_STREAM_READ'] && eventData.hasOwnProperty('params') && ((urltype == "upload" || urltype2 == "upload") && eventData.params.hasOwnProperty('current_position'))) {
                        let existingIdIndex = current_position_list.findIndex(item => item.id === eventData.source.id);
                        if (existingIdIndex === -1) {
                            // If id does not exist, add it to current_position_list
                            current_position_list.push({ id: eventData.source.id, type: urltype, progress: [] });
                            existingIdIndex = current_position_list.length - 1;
                        }
                        // Push new progress values (larger uploads may have multiple events recording current position, similar to how large downloads may have multiple events for byte_count)
                        current_position_list[existingIdIndex].progress.push({ current_position: eventData.params.current_position, time: eventData.time });
                    }
                }
                /**
                Check #5
                We also need to look for the loaded latency events. These are URL_REQUEST event streams that use the "hello?=" urls, and these occur after the download URL_REQUEST events.
                The loaded latency is calculated the same way as the unloaded latency, but the only difference is that we need to find use events 176 and 181 that are associated with the
                loaded urls, which are in in the split_loaded_urls list.
                 */
                if (
                    eventData.hasOwnProperty('params') &&
                    typeof (eventData.params) === 'object' &&
                    (
                        // Check for traditional load/unload url types
                        ((urltype == "load") || (urltype == "unload") || (urltype2 == "load") || (urltype2 == "unload")) ||
                        // Check for new loaded_latency field
                        (urlJSON.loaded_latency && urlJSON.loaded_latency.length > 0)
                    )
                    && (
                        (eventData.params.hasOwnProperty('line') && split_loaded_urls.some(url => String(eventData.params.line).includes(url))) ||
                        (eventData.params.hasOwnProperty('url') && split_loaded_urls.some(url => String(eventData.params.url).includes(url)))
                    )
                ) {
                    if (eventData.type === logEvent_ids['HTTP_TRANSACTION_SEND_REQUEST_HEADERS']) {
                        const id = eventData.source;
                        const existingIdIndex = loaded_latency.findIndex(item => item.sourceID === eventData.source.id); //look for the source ID
                        if (existingIdIndex !== -1) {
                            // If id already exists, add to the same dictionary item
                            if (!loaded_latency[existingIdIndex].send_time) {
                                loaded_latency[existingIdIndex].send_time = []; //Why make it a list? There is only one "send_time" value
                            }
                            loaded_latency[existingIdIndex].send_time.push(eventData.time);
                        } else {
                            //add to the list if the id is not already in the list
                            loaded_latency.push({ sourceID: eventData.source.id, send_time: [eventData.time] });
                        }
                    }
                }
                if (eventData.type === logEvent_ids['HTTP_TRANSACTION_READ_RESPONSE_HEADERS'] && loaded_latency.some(item => item.sourceID === eventData.source.id)) {
                    const id = eventData.source;
                    const existingIdIndex = loaded_latency.findIndex(item => item.sourceID === eventData.source.id);
                    if (existingIdIndex !== -1) {
                        if (!loaded_latency[existingIdIndex].recv_time) {
                            loaded_latency[existingIdIndex].recv_time = [];
                        }
                        // If id already exists, add to the same dictionary item
                        loaded_latency[existingIdIndex].recv_time.push(eventData.time);
                    } else {
                        loaded_latency.push({ sourceID: eventData.source.id, recv_time: [eventData.time] });
                    }
                }

            } catch (error) {
                console.error("Error parsing line", index, ":", error);
            }
        });

        // Write byte_time_list (id, type, and progress [{bytecount, timestamp}]
        writeFileSync(path.join(directory, 'byte_time_list.json'), JSON.stringify(byte_time_list, null, 2));

        //write loaded latency send an receive time to loaded_latency.json
        writeFileSync(path.join(directory, 'loaded_latency.json'), JSON.stringify(loaded_latency, null, 2));

        //if type is upload, write the current_position_list to a file
        if (urltype == "upload") {
            writeFileSync(path.join(directory, 'current_position_list.json'), JSON.stringify(current_position_list, null, 2));
        }

        //write unloaded_latency list to the latency file --(source ID, send and receive time)
        //Only write unloaded latency file if we have unload URLs
        if (split_unload_urls.length > 0) {
            console.log("number of unloaded latency events: ", unloaded_latency.length);
            writeFileSync(path.join(directory, 'latency.json'), JSON.stringify(unloaded_latency, null, 2));
        } else {
            console.log("No unload URLs found - skipping unloaded latency calculation");
        }


    } catch (error) {
        console.error("Error reading the file:", error);
    }
})();

/**
 For every event stream, the source dependancy ID must be collected.

 Uses the source IDs from the current_position_list to collect
 the source dependancy IDs from an event stream.

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
    if (urltype == "upload") {
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
     * Using the socket ID, sum the bytecounts at the socket level.
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
                                type: urltype,
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

console.log("Testing url types: ", urltype, "and", urltype2);
processHttpStreamJobIds();
processSocketIds();
//At this point in time, we are only looking at the byte counts at the socket level for upload tests only.
// if (urltype == "upload") {
//     processByteCounts();
// }

// Since httpStreamJobIds is an intermediary file, we can delete it (socketIds.txt contains the same information)
//  #FIXME: why even write it to a file in the first place, just save it as a variable....
// deleteFile("httpStreamJobIds.txt")

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
