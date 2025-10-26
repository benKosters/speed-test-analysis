/*
 * This script is used to collect the relevant URLs from manually collected Netlog data.
 *
 * Step 1)Extract download, upload, and load URLs from the Netlog file.
 * Step 2) Check to see if download/ or upload/ directories exist in the same directory as the Netlog file.
 * Step 3) If they do not exist, create them.
 * Step 4) Write the relevant URLs to download_urls.json and upload_urls.json files respectively within the new directories.
 *
 * Collecting the proper URLs is the first step in extracting meaningful data from the Netlog file.
 *
 * This program can by run using the following command: node url_filter.js </path/to/netlog/file>
 * Note: the path must be to the SPECIFIC netlog file, not the parent directory that contains the netlog file.
 *
 */

const fs = require('fs');
const path = require('path');
const { checkFilePath, readFileSync, ensureDirectoryExists } = require('./file-utils');
const { url } = require('inspector');

function fixAndParseJSON(jsonString, originalFilePath) {
    // Handles two cases for Puppeteer-collected netlog.json:
    // 1. Missing closing `]}` at the end
    // 2. Has trailing comma, and is missing closing `]}`

    jsonString = jsonString.trim();

    try {
        return JSON.parse(jsonString);
    } catch (e) {
        console.log('Error with Netlog JSON data:', e.message);

        let fixedString;

        // Check if the string ends with a comma (case 2)
        if (jsonString.endsWith(',')) {
            // Remove trailing comma then add closing brackets
            fixedString = jsonString.slice(0, -1) + ']}';
            console.log('Detected trailing comma, removing it and adding closing brackets');
        } else {
            // Just add closing brackets (case 1)
            fixedString = jsonString + ']}';
            console.log('Adding missing closing brackets');
        }

        try {
            const parsedJson = JSON.parse(fixedString);

            if (parsedJson) {
                console.log('Writing fixed JSON back to file:', originalFilePath);
                fs.writeFileSync(originalFilePath, fixedString);
                console.log('JSON file has been fixed and saved.');
            }

            return parsedJson;
        } catch (e2) {
            console.error('Failed to parse JSON with first fix attempt:', e2.message);

            // If the first attempt failed, try the other approach as a fallback
            try {
                if (jsonString.endsWith(',')) {
                    // We already tried removing the comma, now just try adding brackets
                    fixedString = jsonString + ']}';
                } else {
                    // We already tried adding brackets, now try removing potential hidden comma and adding brackets
                    // This handles cases where there might be a non-visible comma or other character
                    const lastBraceIndex = jsonString.lastIndexOf('}');
                    if (lastBraceIndex !== -1) {
                        fixedString = jsonString.substring(0, lastBraceIndex + 1) + ']}';
                    } else {
                        console.error('Could not find a closing brace to fix the JSON');
                        return null;
                    }
                }

                const parsedJson = JSON.parse(fixedString);

                if (parsedJson) {
                    console.log('Writing fixed JSON back to file with second attempt:', originalFilePath);
                    fs.writeFileSync(originalFilePath, fixedString);
                    console.log('JSON file has been fixed and saved with second approach.');
                }

                return parsedJson;
            } catch (e3) {
                console.error('Failed to parse JSON even after multiple fixing attempts:', e3.message);
                return null;
            }
        }
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

        // Extract only the events array
        const events = result.events;

        url_list = {
            "download": [],
            "upload": [],
            "hello": []
        }

        // Process each event to collect URLs
        events.forEach((eventData, index) => {
            try {
                const DOWNLOAD_PATTERN = '8080/download?nocache=';
                const UPLOAD_PATTERN = '8080/upload?nocache=';
                const HELLO_PATTERN = '8080/hello?nocache=';

                if (eventData.hasOwnProperty('params') &&
                    typeof (eventData.params) === 'object' &&
                    eventData.params.hasOwnProperty('url')) {

                    const sourceId = eventData.source.id;

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
                return url_list;

            } catch (error) {
                console.error('Error processing event at index:', index);
                console.error('Event data:', eventData);
            }
        });

    } catch (error) {
        console.error('Error reading or processing file:', error.message); // Log the error message
        console.error('Stack trace:', error.stack); // Log the stack trace for debugging
        process.exit(1);
    }
    return url_list;
}

function separateHelloUrlsByTiming(url_list) {
    /**
     *   time ---------------------------------------------------------------------------------------->
     *   hello ------- download ------- hello ------- upload ------- hello
     *    |                               |                            |
     *    unload_urls                download_load_urls         upload_load_urls
     *
     * Hello urls will appear in three phases:
     * 1) Before the first download URL - these are "unload" URLs
     * 2) Between the first download and first upload URL - these are "download_load" URLs
     * 3) After the first upload URL - these are "upload_load" URLs
     */


    let first_download_id, first_upload_id;
    let unload_urls = [], download_load_urls = [], upload_load_urls = [];
    if (url_list.download.length !== 0) {
        first_download_id = url_list.download[0][1];
    }
    if (url_list.upload.length !== 0) {
        first_upload_id = url_list.upload[0][1];
    }

    for (let i = 0; i < url_list.hello.length; i++) { //for each hello URL
        let hello_id = url_list.hello[i][1];
        let url
        if (first_download_id && hello_id < first_download_id) { //if the ID comes before the first download ID, it is an unload URL
            unload_urls.push(url_list.hello[i][0]);
        } else if (first_download_id && first_upload_id && hello_id > first_download_id && hello_id < first_upload_id) { //if the ID comes after the first download ID but before the first upload ID, it is a download load URL
            download_load_urls.push(url_list.hello[i][0]);
        } else if (first_upload_id && hello_id > first_upload_id) {//if the ID comes after the first upload ID, it is an upload load URL
            upload_load_urls.push(url_list.hello[i][0]);
        }
    }

    latency_urls = {
        "unload": unload_urls,
        "download_load": download_load_urls,
        "upload_load": upload_load_urls
    }

    return latency_urls;
}

function main() {
    if (process.argv.length < 3) {
        console.error('Please provide a netlog or json file path');
        process.exit(1);
    }

    const filePath = process.argv[2];
    checkFilePath(filePath);

    const netlogDir = path.dirname(filePath);

    let url_list = collectUrlsFromNetlog(filePath);

    let latency_urls = separateHelloUrlsByTiming(url_list);


    // Define paths for download and upload directories
    const downloadDir = path.join(netlogDir, 'download');
    const uploadDir = path.join(netlogDir, 'upload');
    // Define paths for the output files
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
    console.log("Number of unload URLs found:", latency_urls.unload.length);
    console.log("Number of download load URLs found:", latency_urls.download_load.length);
    console.log("Number of upload load URLs found:", latency_urls.upload_load.length);
    console.log();

    // Exit if both files already exist
    if (downloadUrlsExists && uploadUrlsExists) {
        console.log(`Both ${downloadUrlsPath} and ${uploadUrlsPath} already exist. Exiting.`);
        process.exit(0);
    }

    let download_url_list = {
        download: url_list.download.map(pair => pair[0]),
        upload: [],
        load: latency_urls.download_load,
        unload: latency_urls.unload
    }

    let upload_url_list = {
        download: [],
        upload: url_list.upload.map(pair => pair[0]),
        load: latency_urls.upload_load,
        unload: latency_urls.unload
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
}

if (require.main === module) {
    main();
}

module.exports = {
    fixAndParseJSON
};