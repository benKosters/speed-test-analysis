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

if (process.argv.length < 3) {
    console.error('Please provide a netlog or json file path');
    process.exit(1);
}

const filePath = process.argv[2];
checkFilePath(filePath);

function fixAndParseJSON(jsonString, originalFilePath) {
    // Handles two cases for Puppeteer-collected netlog.json:
    // 1. Missing closing `]}` at the end
    // 2. Has trailing comma, and is missing closing `]}`

    jsonString = jsonString.trim();

    // First try parsing as-is in case the JSON is already valid
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

try {
    const data = readFileSync(filePath);
    const result = fixAndParseJSON(data, filePath);
    console.log("JSON parsed successfully.");

    // Extract only the events array
    const events = result.events;

    // Define separate URL list objects
    let download_url_list = {
        "download": [],
        "upload": [],
        "load": [],      // Keep for backward compatibility (will be populated with loaded latency)
        "unload": [],    // Will be populated with idle latency
        "idle_latency": [], // New: explicitly identify idle latency URLs
        "loaded_latency": [] // New: explicitly identify loaded latency URLs
    };

    let upload_url_list = {
        "download": [],
        "upload": [],
        "load": [],      // Keep for backward compatibility (will be populated with loaded latency)
        "unload": [],    // Will be populated with idle latency
        "idle_latency": [], // New: explicitly identify idle latency URLs
        "loaded_latency": [] // New: explicitly identify loaded latency URLs
    };

    // Collect all hello URLs for timing analysis
    let allHelloUrls = [];

    // Process each event to collect URLs
    events.forEach((eventData, index) => {
        try {
            const DOWNLOAD_PATTERN = '8080/download?nocache=';
            const UPLOAD_PATTERN = '8080/upload?nocache=';
            const LOAD_PATTERN = '8080/hello?nocache=';



            if (eventData.hasOwnProperty('params') &&
                typeof (eventData.params) === 'object' &&
                eventData.params.hasOwnProperty('url')) {
                //check for download URLs
                if (eventData.params.url.includes(DOWNLOAD_PATTERN)) {
                    if (!download_url_list.download.includes(eventData.params.url)) {
                        download_url_list.download.push(eventData.params.url);
                    }
                }
                //check for more download URLs
                if (eventData.params.hasOwnProperty('created') &&
                    eventData.params.hasOwnProperty('key') &&
                    eventData.params.key.includes(DOWNLOAD_PATTERN)) {
                    const urlParts = eventData.params.key.split(' ');
                    if (urlParts.length >= 3) {
                        const extractedUrl = urlParts[2];
                        if (!download_url_list.download.includes(extractedUrl)) {
                            download_url_list.download.push(extractedUrl);
                        }
                    }
                }
                //check for upload URLs
                if (eventData.params.url.includes(UPLOAD_PATTERN)) {
                    if (!upload_url_list.upload.includes(eventData.params.url)) {
                        upload_url_list.upload.push(eventData.params.url);
                    }
                }
                //check for hello URLs - collect them for timing analysis
                if (eventData.params.url.includes(LOAD_PATTERN)) {
                    if (!allHelloUrls.includes(eventData.params.url)) {
                        allHelloUrls.push(eventData.params.url);
                    }
                }
            }

        } catch (error) {
            console.error('Error processing event at index:', index);
            console.error('Event data:', eventData);
        }
    });


    // Time-based URL separation for hello endpoints
    function separateHelloUrlsByTiming(netlogData, helloUrls) {
        const events = netlogData.events;

        // Find timing boundaries
        const downloadTimes = [];
        const helloTimes = [];

        events.forEach(event => {
            if (event.params && event.params.url) {
                if (event.params.url.includes('/download') || event.params.url.includes('/upload')) {
                    downloadTimes.push(parseInt(event.time));
                } else if (event.params.url.includes('/hello')) {
                    helloTimes.push({ time: parseInt(event.time), url: event.params.url });
                }
            }
        });

        if (downloadTimes.length === 0) {
            // No download/upload, all hello URLs are idle latency
            return {
                idleLatencyUrls: helloUrls,
                loadedLatencyUrls: []
            };
        }

        const firstDownloadTime = Math.min(...downloadTimes);
        const lastDownloadTime = Math.max(...downloadTimes);

        console.log(`DEBUG: First download time: ${firstDownloadTime}`);
        console.log(`DEBUG: Total hello URLs to classify: ${helloUrls.length}`);
        console.log(`DEBUG: Total hello events found: ${helloTimes.length}`);

        // Separate hello URLs by timing
        const idleLatencyUrls = [];
        const loadedLatencyUrls = [];

        // Group hello events by URL to find their timing
        const urlTimings = {};
        helloTimes.forEach(entry => {
            if (!urlTimings[entry.url]) {
                urlTimings[entry.url] = [];
            }
            urlTimings[entry.url].push(parseInt(entry.time));
        });

        // Classify each hello URL based on its timing
        helloUrls.forEach(url => {
            const times = urlTimings[url] || [];
            if (times.length === 0) {
                // Fallback: if we can't find timing, assume it's loaded latency
                loadedLatencyUrls.push(url);
                return;
            }

            const avgTime = times.reduce((a, b) => a + b, 0) / times.length;

            // If average time is before first download, it's idle latency
            // If it's during/after downloads, it's loaded latency
            if (avgTime < firstDownloadTime) {
                idleLatencyUrls.push(url);
            } else {
                loadedLatencyUrls.push(url);
            }
        });

        return {
            idleLatencyUrls,
            loadedLatencyUrls
        };
    }

    //FIXME - Uncomment this section once verified
    //------------------------------------------------------------------------------------------------------------
    // // Now separate hello URLs by timing to distinguish idle vs loaded latency
    // console.log("Separating hello URLs by timing...");
    // console.log("Total hello URLs collected:", allHelloUrls.length);

    // if (allHelloUrls.length > 0) {
    //     const separation = separateHelloUrlsByTiming(jsonData, allHelloUrls);

    //     // Populate the URL lists with separated data
    //     download_url_list.unload = separation.idleLatencyUrls;
    //     download_url_list.idle_latency = separation.idleLatencyUrls;
    //     download_url_list.load = separation.loadedLatencyUrls;
    //     download_url_list.loaded_latency = separation.loadedLatencyUrls;

    //     upload_url_list.unload = separation.idleLatencyUrls;
    //     upload_url_list.idle_latency = separation.idleLatencyUrls;
    //     upload_url_list.load = separation.loadedLatencyUrls;
    //     upload_url_list.loaded_latency = separation.loadedLatencyUrls;

    //     console.log("Idle latency URLs found:", separation.idleLatencyUrls.length);
    //     console.log("Loaded latency URLs found:", separation.loadedLatencyUrls.length);
    // } else {
    //     console.log("No hello URLs found for latency measurement");
    // }

    //------------------------------------------------------------------------------------------------------------
    const netlogDir = path.dirname(filePath);

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
    console.log("Number of download URLs found:", download_url_list.download.length);
    console.log("Number of load URLs found:", download_url_list.load.length);
    console.log("Number of idle latency URLs found:", download_url_list.idle_latency.length);
    console.log("Number of upload URLs found:", upload_url_list.upload.length);

    // Exit if both files already exist
    if (downloadUrlsExists && uploadUrlsExists) {
        console.log(`Both ${downloadUrlsPath} and ${uploadUrlsPath} already exist. Exiting.`);
        process.exit(0);
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

} catch (error) {
    console.error('Error reading or processing file:', error.message); // Log the error message
    console.error('Stack trace:', error.stack); // Log the stack trace for debugging
    process.exit(1);
}