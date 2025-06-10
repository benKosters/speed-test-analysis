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
        "load": [],
        "unload": []
    };

    let upload_url_list = {
        "download": [],
        "upload": [],
        "load": [],
        "unload": []
    };

    // Process each event
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
                if (eventData.params.url.includes(DOWNLOAD_PATTERN3)) {
                    if (!download_url_list.download.includes(eventData.params.url)) {
                        download_url_list.download.push(eventData.params.url);
                    }
                }
                //check for more download URLs
                if (eventData.params.hasOwnProperty('created') &&
                    eventData.params.hasOwnProperty('key') &&
                    eventData.params.key.includes(DOWNLOAD_PATTERN3)) {
                    const urlParts = eventData.params.key.split(' ');
                    if (urlParts.length >= 3) {
                        const extractedUrl = urlParts[2];
                        if (!download_url_list.download.includes(extractedUrl)) {
                            download_url_list.download.push(extractedUrl);
                        }
                    }
                }
                //check for upload URLs
                if (eventData.params.url.includes(UPLOAD_PATTERN3)) {
                    if (!upload_url_list.upload.includes(eventData.params.url)) {
                        upload_url_list.upload.push(eventData.params.url);
                    }
                }
                //check for load URLs (add to both lists)
                if (eventData.params.url.includes(LOAD_PATTERN3)) {
                    if (!download_url_list.load.includes(eventData.params.url)) {
                        download_url_list.load.push(eventData.params.url);
                    }
                    if (!upload_url_list.load.includes(eventData.params.url)) {
                        upload_url_list.load.push(eventData.params.url);
                    }
                }
            }

        } catch (error) {
            console.error('Error processing event at index:', index);
            console.error('Event data:', eventData);
        }
    });

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