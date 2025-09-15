/*
 * This script is used to collect the relevant URLs from manually collected Netlog data.
 * Step 1)Extract download, upload, and load URLs from the Netlog file.
 * Step 2) Check to see if download/ or upload/ directories exist in the same directory as the Netlog file.
 * Step 3) If they do not exist, create them.
 * Step 4) Write the relevant URLs to download_urls.json and upload_urls.json files respectively within the new directories.
 *
 * Collecting the proper URLs is the first step in extracting meaningful data from the Netlog file.
 *
 * This program can by run using the following command: python3 url_filter.js </path/to/netlog/file>
 * Note: the path must be to the SPECIFIC netlog file, not the parent directory that contains the netlog file.
 *
 * #FIXME: The process of collecting the load URLs for the manually run tests is incorrect and must be fixed.
 */

const fs = require('fs');
const path = require('path');

// Check if a file path was provided
if (process.argv.length < 3) {
    console.error('Please provide a netlog or json file path');
    process.exit(1);
}

// Function to check if file exists
const checkFilePath = (filePath) => {
    if (!fs.existsSync(filePath)) {
        console.log(`The file does not exist: ${filePath}`);
        process.exit(1);
    }
};

// Function to read a file synchronously
const readFileSync = (filePath) => {
    const fileread = fs.readFileSync(filePath, { encoding: 'utf-8' });
    console.log(`File ${filePath} read successfully!`);
    return fileread;
};

// Function to create directory if it doesn't exist
const ensureDirectoryExists = (dirPath) => {
    if (!fs.existsSync(dirPath)) {
        console.log(`Creating directory: ${dirPath}`);
        fs.mkdirSync(dirPath, { recursive: true });
        return false; // Directory didn't exist before
    }
    return true; // Directory already existed
};

// Get file path from command line argument
const filePath = process.argv[2];
checkFilePath(filePath);

try {
    const data = readFileSync(filePath);
    // Parse the entire JSON file
    const jsonData = JSON.parse(data);

    // Extract only the events array
    const events = jsonData.events;

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
            const DOWNLOAD_PATTERN = 'speed.michwave.com.prod.hosts.ooklaserver.net:8080/download?nocache=';
            const UPLOAD_PATTERN = 'speed.michwave.com.prod.hosts.ooklaserver.net:8080/upload?nocache=';
            const LOAD_PATTERN = 'speed.michwave.com.prod.hosts.ooklaserver.net:8080/hello?nocache=';

            //Spacelink patterns:
            const DOWNLOAD_PATTERN2 = 'speedtest.spacelink.com.prod.hosts.ooklaserver.net:8080/download?nocache='
            const UPLOAD_PATTERN2 = 'speedtest.spacelink.com.prod.hosts.ooklaserver.net:8080/upload?nocache=';
            const LOAD_PATTERN2 = 'speedtest.spacelink.com.prod.hosts.ooklaserver.net:8080/hello?nocache=';


            //Merit patterns:
            const DOWNLOAD_PATTERN3 = 'speedtest-gdrp.merit.edu.prod.hosts.ooklaserver.net:8080/download?nocache=';
            const UPLOAD_PATTERN3 = 'speedtest-gdrp.merit.edu.prod.hosts.ooklaserver.net:8080/upload?nocache=';
            const LOAD_PATTERN3 = 'speedtest-gdrp.merit.edu.prod.hosts.ooklaserver.net:8080/hello?nocache=';
        

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
                    helloTimes.push({time: parseInt(event.time), url: event.params.url});
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
            
            //console.log(`DEBUG: URL ${url.substring(url.indexOf('nocache=')+8, url.indexOf('nocache=')+20)} - avg time: ${avgTime}, first download: ${firstDownloadTime}, is idle: ${avgTime < firstDownloadTime}`);
            
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

    // Now separate hello URLs by timing to distinguish idle vs loaded latency
    console.log("Separating hello URLs by timing...");
    console.log("Total hello URLs collected:", allHelloUrls.length);
    
    if (allHelloUrls.length > 0) {
        const separation = separateHelloUrlsByTiming(jsonData, allHelloUrls);
        
        // Populate the URL lists with separated data
        download_url_list.unload = separation.idleLatencyUrls;
        download_url_list.idle_latency = separation.idleLatencyUrls;
        download_url_list.load = separation.loadedLatencyUrls;
        download_url_list.loaded_latency = separation.loadedLatencyUrls;
        
        upload_url_list.unload = separation.idleLatencyUrls;
        upload_url_list.idle_latency = separation.idleLatencyUrls;
        upload_url_list.load = separation.loadedLatencyUrls;
        upload_url_list.loaded_latency = separation.loadedLatencyUrls;
        
        console.log("Idle latency URLs found:", separation.idleLatencyUrls.length);
        console.log("Loaded latency URLs found:", separation.loadedLatencyUrls.length);
    } else {
        console.log("No hello URLs found for latency measurement");
    }

    // Get the directory of the netlog file
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
    console.error('Error reading or processing file:', error);
    process.exit(1);
}