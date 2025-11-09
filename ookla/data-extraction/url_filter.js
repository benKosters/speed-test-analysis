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
const { checkFilePath, readFileSync, ensureDirectoryExists, fixAndParseJSON } = require('./file-utils');
const { url } = require('inspector');


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

    // // Save all URLs into one file
    // const urlFilePath = path.join(netlogDir, 'all_urls.json');
    // const urlFileExists = fs.existsSync(urlFilePath);

    // if (!urlFileExists) {
    //     console.log("Saving all URLs");
    //     fs.writeFileSync(urlFilePath, JSON.stringify(url_list, null, 2));
    //     console.log(`Successfully wrote download URLs to ${urlFilePath}`);
    // }
    // else {
    //     console.log("URL file has already been saved, skipping saving");
    // }


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
        console.log(`Both ${downloadUrlsPath} and ${uploadUrlsPath} already exist. Exiting.`);
        process.exit(0);
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
}

if (require.main === module) {
    main();
}

module.exports = {
    fixAndParseJSON
};