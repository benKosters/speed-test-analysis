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
 */

//Import the filesystem and path modules
const fs = require('fs');
const path = require('path');
const { checkFilePath, readFileSync, writeFileSync, deleteFile, parseJSONFromFile, mapEventNamesToIds } = require('./file-utils');
const { captureBytecountData } = require('./filter-bytecounts');
const { splitTestTypeUrls } = require('./url-processing')
const { captureLatencyData, calculateLatencyStatistics, updateAllLatencyStatistics } = require('./filter-latency-data')
const { processHttpStreamJobIds, processSocketIds } = require('./filter-sockets')

const captureTestMetadata = (netlog_constants) => {
    os_type = netlog_constants.clientInfo.os_type;
    chrome_version = netlog_constants.clientInfo.version;
}

// Immediately invoked anonomous function to read the contents of the Netlog file
function processNetlogFile(filePath, urlPath) {
    try {
        directory = path.dirname(urlPath);
        const urlJSON = parseJSONFromFile(urlPath);


        const data = readFileSync(filePath);
        const parsedData = JSON.parse(data);
        const netlog_constants = parsedData.constants;
        const events = parsedData.events;
        captureTestMetadata(netlog_constants);

        const logEvent_ids = {}; //maps Netlog event names to a number (their IDs) - these IDs change for each test, but the names remain the same
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
        const { split_urls, split_unloaded_urls, split_loaded_urls, testType: testType } = splitTestTypeUrls(urlJSON);

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
                    captureBytecountData(eventData, results, byte_time_list, current_position_list, testType, logEvent_ids);
                }

                // check #3 --> UNLOADED latency (hello URLs)
                if (eventData.hasOwnProperty('params') &&
                    typeof (eventData.params) === 'object' &&
                    split_unloaded_urls.length > 0) {

                    // Handle send events (type 176) with URL matching
                    if (eventData.type === logEvent_ids['HTTP_TRANSACTION_SEND_REQUEST_HEADERS'] &&
                        eventData.params.hasOwnProperty('line') &&
                        split_unloaded_urls.some(url => String(eventData.params.line).includes(url))) {
                        captureLatencyData(eventData, latency_data.unloaded_latency.streams, split_unloaded_urls, 'unloaded', logEvent_ids);
                    }

                    // Handle receive events (type 181) - only if source already exists from send event
                    if (eventData.type === logEvent_ids['HTTP_TRANSACTION_READ_RESPONSE_HEADERS'] &&
                        latency_data.unloaded_latency.streams.some(stream => stream.id === eventData.source.id)) {
                        captureLatencyData(eventData, latency_data.unloaded_latency.streams, split_unloaded_urls, 'unloaded', logEvent_ids);
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
                        captureLatencyData(eventData, latency_data.loaded_latency.streams, split_loaded_urls, 'loaded', logEvent_ids);
                    }

                    // Handle receive events (type 181) - only if source already exists from send event
                    if (eventData.type === logEvent_ids['HTTP_TRANSACTION_READ_RESPONSE_HEADERS'] &&
                        latency_data.loaded_latency.streams.some(stream => stream.id === eventData.source.id)) {
                        captureLatencyData(eventData, latency_data.loaded_latency.streams, split_loaded_urls, 'loaded', logEvent_ids);
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
                        captureLatencyData(eventData, latency_data.test_latency.streams, split_urls, 'test', logEvent_ids);
                    }

                    // Handle receive events (type 181) - only if source already exists from send event
                    if (eventData.type === logEvent_ids['HTTP_TRANSACTION_READ_RESPONSE_HEADERS'] &&
                        latency_data.test_latency.streams.some(stream => stream.id === eventData.source.id)) {
                        captureLatencyData(eventData, latency_data.test_latency.streams, split_urls, 'test', logEvent_ids);
                    }
                }

            } catch (error) {
                console.error("Error parsing line", index, ":", error);
            }
        });
        console.log("latency captured");
        updateAllLatencyStatistics(latency_data);

        // Write byte_time_list (id, type, and progress [{bytecount, timestamp}]
        writeFileSync(path.join(directory, 'byte_time_list.json'), JSON.stringify(byte_time_list, null, 2));

        //write loaded latency send an receive time to loaded_latency.json
        writeFileSync(path.join(directory, 'latency_data.json'), JSON.stringify(latency_data, null, 2));

        //if type is upload, write the current_position_list to a file
        if (testType == "upload") {
            writeFileSync(path.join(directory, 'current_position_list.json'), JSON.stringify(current_position_list, null, 2));
        }

        console.log("Testing url type:", testType);
        processHttpStreamJobIds(path, filePath, urlPath, directory, testType, logEvent_ids);
        processSocketIds(path, filePath, urlPath, directory, logEvent_ids);

    } catch (error) {
        console.error("Error processing netlog file:", error);
    }


};

module.exports = {
    processNetlogFile
}




