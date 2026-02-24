/*
 * This script is used to collect the relevant URLs from manually collected Netlog data.
 *
 * Step 1) Extract download, upload, and load URLs from the Netlog file.
 * Step 2) Check to see if download/ or upload/ directories exist in the same directory as the Netlog file. If they do not exist, create them.
 * Step 3) Write the relevant URLs to download_urls.json and upload_urls.json files respectively within the new directories.
 *
 *
 */

const fs = require('fs');
const path = require('path');
const { checkFilePath, readFileSync, ensureDirectoryExists, fixAndParseJSON, mapEventNamesToIds, parseJSONFromFile, writeFileSync } = require('./file-utils');
const { url } = require('inspector');
const { type } = require('os');

const captureTestMetadata = (netlogPath) => {
    //append metadata to existing speedtest_result.json file
    directory = path.dirname(netlogPath);
    const data = JSON.parse(readFileSync(netlogPath));
    const netlog_constants = data.constants;

    const os_type = netlog_constants.clientInfo.os_type;
    const chrome_version = netlog_constants.clientInfo.version;
    const speedtestResultPath = path.join(directory, 'speedtest_result.json');
    if (!fs.existsSync(speedtestResultPath)) {
        console.log("speedtest_result.json not found, metadata does not need to be added.");
        return;
    }
    try {
        const existingData = parseJSONFromFile(speedtestResultPath);
        existingData.os_type = os_type;
        existingData.chrome_version = chrome_version;
        writeFileSync(speedtestResultPath, JSON.stringify(existingData, null, 2));
    } catch (error) {
        console.error("Error:", error);
    }
}

// Helper function to check if a URL has already been picked up
function isUniqueUrl(list, newUrl) {
    return !list.some(pair => pair[0] === newUrl);
}

function collectUrlsFromNetlog(filePath) {
    try {
        const data = readFileSync(filePath);
        const result = fixAndParseJSON(data, filePath);
        console.log("JSON parsed successfully.");

        const events = result.events;
        const event_ids = {};

        console.log(typeof (result.constants.logEventTypes));
        mapEventNamesToIds(result.constants.logEventTypes, event_ids);
        console.log(event_ids["REQUEST_ALIVE"]);


        url_list = {
            "download": [],
            "upload": [],
            "hello": [],
            "ws": []
        }

        let ws_sessions = {};
        let ws_source_ids = [];

        // Process each event to collect URLs
        events.forEach((eventData, index) => {
            try {
                const DOWNLOAD_PATTERN = '8080/download?nocache=';
                const UPLOAD_PATTERN = '8080/upload?nocache=';
                const HELLO_PATTERN = '8080/hello?nocache=';
                const WS_PATTERN = '/ws?';

                // Declare these variables at the beginning of the loop
                const sourceId = eventData.source.id;
                const eventType = eventData.type;

                //Look for WS events:
                if (eventData.hasOwnProperty('params') &&
                    typeof (eventData.params) === 'object' &&
                    eventData.params.hasOwnProperty('url') &&
                    eventData.params.url.includes(WS_PATTERN) &&
                    eventData.type === event_ids['URL_REQUEST']) {

                    ws_sessions[sourceId] = {
                        url: eventData.params.url,
                        sourceId: sourceId,
                        initialRequestTime: eventData.time,
                        startTime: null,
                        endTime: null,
                        duration: null
                    };
                    ws_source_ids.push(sourceId);
                    console.log("Found WebSocket URL:", eventData.params.url, "Source ID:", sourceId);
                }

                // Check for WebSocket start event (HTTP 101 Switching Protocols)
                if (ws_source_ids.includes(sourceId) &&
                    eventType === event_ids["HTTP_TRANSACTION_READ_RESPONSE_HEADERS"] &&
                    eventData.hasOwnProperty('params') &&
                    eventData.params.hasOwnProperty('headers')) {

                    // Check if headers indicate WebSocket upgrade
                    const headers = Array.isArray(eventData.params.headers) ?
                        eventData.params.headers.join(' ') :
                        JSON.stringify(eventData.params.headers);

                    if (headers.includes("101 Switching Protocols") &&
                        headers.includes("websocket")) {

                        if (ws_sessions[sourceId]) {
                            ws_sessions[sourceId].startTime = eventData.time;
                            console.log("WebSocket start event found for source ID:", sourceId, "at time:", eventData.time);
                        }
                    }
                }

                // Check for WebSocket end event (WEBSOCKET_RECV_FRAME_HEADER with specific opcode)
                if (ws_source_ids.includes(sourceId) &&
                    eventType === event_ids["WEBSOCKET_RECV_FRAME_HEADER"] &&
                    eventData.hasOwnProperty('params') &&
                    eventData.params.hasOwnProperty('opcode')) {

                    // Look for close frame (opcode 8) or other specific opcodes that indicate end
                    if (eventData.params.opcode === 8) { // Close frame
                        if (ws_sessions[sourceId]) {
                            ws_sessions[sourceId].endTime = eventData.time;

                            // Calculate duration if we have both start and end times
                            if (ws_sessions[sourceId].startTime) {
                                ws_sessions[sourceId].duration =
                                    parseInt(ws_sessions[sourceId].endTime) -
                                    parseInt(ws_sessions[sourceId].startTime);
                            }
                            console.log("WebSocket end event found for source ID:", sourceId, "at time:", eventData.time);
                        }
                    }
                }

                if (eventData.hasOwnProperty('params') &&
                    typeof (eventData.params) === 'object' &&
                    eventData.params.hasOwnProperty('url')) {


                    //check for download URLs
                    if (eventData.params.url.includes(DOWNLOAD_PATTERN)) {
                        if (isUniqueUrl(url_list.download, eventData.params.url)) {
                            url_list.download.push([eventData.params.url, sourceId]);
                        }
                    }
                    //check for more download URLs
                    if (eventData.params.hasOwnProperty('created') &&
                        eventData.params.hasOwnProperty('key') &&
                        eventData.params.key.includes(DOWNLOAD_PATTERN)) {
                        const urlParts = eventData.params.key.split(' ');
                        if (urlParts.length >= 3) {
                            const extractedUrl = urlParts[2];
                            if (isUniqueUrl(url_list.download, extractedUrl)) {
                                url_list.download.push([extractedUrl, eventData.source.id]);
                            }
                        }
                    }
                    //check for upload URLs
                    if (eventData.params.url.includes(UPLOAD_PATTERN)) {
                        if (isUniqueUrl(url_list.upload, eventData.params.url)) {
                            url_list.upload.push([eventData.params.url, sourceId]);
                        }
                    }
                    //check for hello URLs
                    if (eventData.params.url.includes(HELLO_PATTERN)) {
                        if (isUniqueUrl(url_list.hello, eventData.params.url)) {
                            url_list.hello.push([eventData.params.url, sourceId]);
                        }
                    }

                }

            } catch (error) {
                console.error('Error processing event at index:', index);
                console.error('Event data:', eventData);
            }
        });

        // Convert WebSocket sessions to array format and add to url_list
        url_list.ws = Object.values(ws_sessions);

        // Log summary of WebSocket sessions found
        console.log("WebSocket sessions found:", url_list.ws.length);
        url_list.ws.forEach((session, index) => {
            console.log(`WS ${index + 1}: URL: ${session.url}`);
            console.log(`  Source ID: ${session.sourceId}`);
            console.log(`  Start Time: ${session.startTime || 'Not found'}`);
            console.log(`  End Time: ${session.endTime || 'Not found'}`);
            console.log(`  Duration: ${session.duration || 'Cannot calculate'} ms`);
        });

    } catch (error) {
        console.error('Error reading or processing file:', error.message);
        console.error('Stack trace:', error.stack);
        process.exit(1);
    }
    return url_list;
}

function separateHelloUrlsByTiming(url_list) {
    /**
     * time ---------------------------------------------------------------------------------------->
     *        first_download_id --- last_download_id     first_upload_id --- last_upload_id
     *        |                        |                    |                    |
     * hello  |  hello    hello       |       hello        |       hello       |      hello
     *   |    |    |        |         |         |          |         |         |         |
     *   |    |    |        |         |         |          |         |         |         |
     *   A    B    C        D         E         F          G         H         I         J
     *
     * A: unloaded_download (id < first_download_id)
     * B,C,D: loaded_download (first_download_id < id < last_download_id)
     * E,F,G: unloaded_upload (last_download_id < id < first_upload_id)
     * H,I,J: loaded_upload (id > first_upload_id)
     */

    let first_download_id, last_download_id, first_upload_id;
    let unloaded_download_urls = [],
        loaded_download_urls = [],
        unloaded_upload_urls = [],
        loaded_upload_urls = [];

    // Get boundary IDs
    if (url_list.download.length !== 0) {
        first_download_id = url_list.download[0][1];
        last_download_id = url_list.download[url_list.download.length - 1][1];
    }
    if (url_list.upload.length !== 0) {
        first_upload_id = url_list.upload[0][1];
    }

    // Process each hello URL
    for (let i = 0; i < url_list.hello.length; i++) {
        const [url, hello_id] = url_list.hello[i];

        if (first_download_id && hello_id < first_download_id) {
            // Before first download = unloaded download
            unloaded_download_urls.push(url);
        } else if (first_download_id && last_download_id &&
            hello_id > first_download_id && hello_id < last_download_id) {
            // Between first and last download = loaded download
            loaded_download_urls.push(url);
        } else if (last_download_id && first_upload_id &&
            hello_id > last_download_id && hello_id < first_upload_id) {
            // Between last download and first upload = unloaded upload
            unloaded_upload_urls.push(url);
        } else if (first_upload_id && hello_id > first_upload_id) {
            // After first upload = loaded upload
            loaded_upload_urls.push(url);
        }
    }

    return {
        "download": {
            "unload": unloaded_download_urls,
            "load": loaded_download_urls
        },
        "upload": {
            "unload": unloaded_upload_urls,
            "load": loaded_upload_urls
        }
    };
}

/**
 * Main function to filter URLs from a netlog file
 * @param {string} netlogFilePath - Path to the netlog.json file
 * @returns {object} Object containing paths to created URL files
 */
function filterUrls(netlogFilePath) {
    checkFilePath(netlogFilePath);
    const netlogDir = path.dirname(netlogFilePath);
    captureTestMetadata(netlogFilePath);

    let url_list = collectUrlsFromNetlog(netlogFilePath);
    let latency_urls = separateHelloUrlsByTiming(url_list);

    // Define paths for download and upload directories
    const downloadDir = path.join(netlogDir, 'download');
    const uploadDir = path.join(netlogDir, 'upload');
    //Define paths for the output files
    const downloadUrlsPath = path.join(downloadDir, 'download_urls.json');
    const uploadUrlsPath = path.join(uploadDir, 'upload_urls.json');

    // Check if the output directories exist or create them
    const downloadDirExists = ensureDirectoryExists(downloadDir);
    const uploadDirExists = ensureDirectoryExists(uploadDir);
    // Check if output files already exist
    const downloadUrlsExists = fs.existsSync(downloadUrlsPath);
    const uploadUrlsExists = fs.existsSync(uploadUrlsPath);


    // Print summary of found URLs
    console.log("Number of download URLs found:", url_list.download.length);
    console.log("Number of upload URLs found:", url_list.upload.length);
    console.log("Number of hello URLs found:", url_list.hello.length);
    console.log();
    console.log("Download test latency URLs:");
    console.log("  Unloaded:", latency_urls.download.unload.length);
    console.log("  Loaded:", latency_urls.download.load.length);
    console.log("Upload test latency URLs:");
    console.log("  Unloaded:", latency_urls.upload.unload.length);
    console.log("  Loaded:", latency_urls.upload.load.length);

    // Exit if both files already exist
    if (downloadUrlsExists && uploadUrlsExists) {
        // console.log(`Both ${downloadUrlsPath} and ${uploadUrlsPath} already exist.`);
        console.log('URL files already exist. Skipping creation.');
        return {
            downloadDir: downloadDir,
            uploadDir: uploadDir,
            downloadUrlsPath: downloadUrlsPath,
            uploadUrlsPath: uploadUrlsPath
        }
    }

    let download_url_list = {
        download: url_list.download.map(pair => pair[0]),
        upload: [],
        load: latency_urls.download.load,
        unload: latency_urls.download.unload
    }

    let upload_url_list = {
        download: [],
        upload: url_list.upload.map(pair => pair[0]),
        load: latency_urls.upload.load,
        unload: latency_urls.upload.unload
    }

    // Write download_urls.json if it doesn't exist
    if (!downloadUrlsExists) {
        console.log(`Writing to ${downloadUrlsPath}`);
        fs.writeFileSync(downloadUrlsPath, JSON.stringify(download_url_list, null, 2));
        console.log(`Successfully wrote download URLs to ${downloadUrlsPath}`);
    } else {
        console.log(`File ${downloadUrlsPath} already exists. Skipping.`);
    }

    // Write upload_urls.json if it doesn't exist
    if (!uploadUrlsExists) {
        console.log(`Writing to ${uploadUrlsPath}`);
        fs.writeFileSync(uploadUrlsPath, JSON.stringify(upload_url_list, null, 2));
        console.log(`Successfully wrote upload URLs to ${uploadUrlsPath}`);
    } else {
        console.log(`File ${uploadUrlsPath} already exists. Skipping.`);
    }

    console.log('URL extraction completed successfully.');

    return {
        downloadDir: downloadDir,
        uploadDir: uploadDir,
        downloadUrlsPath: downloadUrlsPath,
        uploadUrlsPath: uploadUrlsPath
    };
}

module.exports = {
    filterUrls,
    collectUrlsFromNetlog,
    separateHelloUrlsByTiming
};