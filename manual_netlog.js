/**
 * This file is in the analysis_manual/ directory. It filters the relevant data from netlog files generated during running speed tests manually.
 * The relevant events are used to compute both throughput and latency (based on our calculations) which will then be used to compare against
 * running CARROTS tests to verify the accuracy of CARROTS.
 *
 * The script is run this way: node manual_netlog.js <path_to_netlog_file> <path_to_urls_file>
 * #FIXME: since the netlog data for manual tests contains BOTH upload and download tests, find a way to separate the netlog data
 *
 * This event filtering script can be used for both download and upload, and these are the files produced:
 * For download:
 *      1) byte_time_list.json - the byte counts divided by http stream/source
 *      2) latency.json - the unloaded latency for each http stream/source
 *      3) loaded_latency.json - the loaded latency for each http stream/source #FIXME - the issue with loaded latency could be here too
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
 * These output files are written to the output directory, for ease of access. They are also
 * written to the same directory as where the URLs came from in order to save the results.
 */


//Import the filesystem and path modules
const fs = require('fs');
const { url } = require('inspector');
const path = require('path');
const { ConsoleMessage } = require('puppeteer');

//merit
const EVENT_TYPES = {
    REQUEST_ALIVE: 2,
    URL_REQUEST_JOB_FILTERED_BYTES_READ: 134,
    URL_REQUEST_JOB_FILTERED_BYTES_READ_MICHWAVE: 136,

    URL_REQUEST_BYTES_READ: 122,
    URL_REQUEST_JOB_FILTERED_BYTES_READ_NEW: 136,

    UPLOAD_DATA_STREAM_READ: 502,
    UPLOAD_DATA_STREAM_READ_MICHWAVE: 509,
    UPLOAD_DATA_STREAM_READ_SPACELINK: 514,

    HTTP_TRANSACTION_READ_RESPONSE_HEADERS: 218,
    HTTP_TRANSACTION_READ_RESPONSE_HEADERS_MICHWAVE: 224,
    HTTP_TRANSACTION_READ_RESPONSE_HEADERS_SPACELINK: 229,

    HTTP_TRANSACTION_SEND_REQUEST_HEADERS: 213,
    HTTP_TRANSACTION_SEND_REQUEST_HEADERS_MICHWAVE: 219,
    HTTP_TRANSACTION_SEND_REQUEST_HEADERS_SPACELINK: 224,

    HTTP_TRANSACTION_RECEIVE_RESPONSE_HEADERS: 181,
    HTTP_TRANSACTION_RECEIVE_RESPONSE_HEADERS_MICHWAVE: 224,
    HTTP_TRANSACTION_RECEIVE_RESPONSE_HEADERS_SPACELINK: 229,

    HTTP_STREAM_REQUEST_BOUND_TO_JOB: 171,
    HTTP_STREAM_REQUEST_BOUND_TO_JOB_MICHWAVE: 173,
    HTTP_STREAM_REQUEST_BOUND_TO_JOB_SPACELINK: 174,

    SOCKET_POOL_BOUND_TO_SOCKET: 112,
    SOCKET_POOL_BOUND_TO_SOCKET_MICHWAVE: 114,
    SOCKET_POOL_BOUND_TO_SOCKET_SPACELINK: 114,

    DEBUG: 160
};


// Check if a file path was provided
const checkFilePath = (filePath) => {
    if (!fs.existsSync(filePath)) {
        console.log("The file ", filePath, " does not exist.");
        process.exit(1);
    }
};

// Function to read a file synchronously - from the output directory
const readFileSync = (filePath) => {
    fileread = fs.readFileSync(filePath, { encoding: 'utf-8' });
    console.log('File ', filePath, ' read success!');
    return fileread
};

let directory;
// Function to write a file synchronously - only to URL directory
const writeFileSync = (fileName, data) => {
    // Write to the same directory as the URL file
    const urlDir = path.dirname(urlPath);
    const urlDirPath = path.join(urlDir, fileName);

    // Check if file exists in URL directory
    if (fs.existsSync(urlDirPath)) {
        console.log(`Note: ${fileName} already exists in ${urlDir}, overwriting...`);
    }

    fs.writeFileSync(urlDirPath, data);
    console.log(`File ${fileName} write success in ${urlDir}\n`);
};

const deleteFile = (fileName) => {
    const urlDir = path.dirname(urlPath);
    const urlDirPath = path.join(urlDir, fileName);

    // Check if file exists before attempting to delete
    if (fs.existsSync(urlDirPath)) {
        try {
            fs.unlinkSync(urlDirPath);
            console.log(`File ${fileName} deleted successfully from ${urlDir}`);
        } catch (err) {
            console.error(`Error deleting file ${fileName} from ${urlDir}:`, err);
        }
    } else {
        console.log(`File ${fileName} does not exist in ${urlDir}`);
    }
};

//Function that returns the url's type and form
const getUrlTypeAndForm = (urlJSON) => {
    //print lines for testing purposes...
    //console.log("URL JSON: ", urlJSON);
    //console.log("urlJSON.download.length: ", urlJSON.download.length);
    let urltype = "", urltype2 = "", form = [], form2 = [];
    if (urlJSON.load.length > 0) {
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

// Function to parse JSON from a file
const parseJSONFromFile = (filePath) => {
    const fileContent = fs.readFileSync(filePath);
    console.log('File ', filePath, ' JSON parse success!');
    return JSON.parse(fileContent);
};

// Read the command line arguments to get netlog file and url file
const filePath = process.argv[2];
const urlPath = process.argv[3];

// Check if file paths were provided
if (process.argv.length != 4) {
    console.log("Usage: node netlog.js <path_to_netlog_file> <path_to_urls_file>");
    process.exit(1);
}

// Check if the files exist
checkFilePath(filePath);
checkFilePath(urlPath);


//get the directory that the netlog file is in
directory = filePath.substring(0, filePath.lastIndexOf('/'));

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
        const events = parsedData.events;

        const byte_time_list = []; //used for desired download data
        const current_position_list = []; //used for desired upload data
        const results = [];
        const latency_results = [];//for UNLOADED latency
        const loaded_latency_results = [];//For loaded latency


        // 1) Download URLS
        //only store the relative attributes of the urls, removing the domain - saves the cache, guid, and size attributes
        //we need this to check for the proper HTTP_TRANSACTION_SEND_REQUEST_HEADERS event
        //Form contains download/upload urls, form2 contains the load urls
        if (urltype === "load" || urltype === "unload" || urltype2 === "load" || urltype2 === "unload") {
            var split_urls = [];
            for (var i = 0; i < form.length; i++) {
                //console.log(typeof urls[i], urls[i]);
                var parts = form[i].split("/");
                var split_url = parts.slice(3).join("/");
                split_urls.push(split_url);
            }
            //TESTING: check the split URLs being saved
            //writeFileSync("split_urls.json", JSON.stringify(split_urls, null, 2));
        }

        // 2) Load URLS
        // Store the relative attributes of the loaded urls, which we will need for finding the HTTP_TRANSACTION_SEND_REQUEST_HEADERS event
        // of the URL_REQUEST events that measure loaded latency.
        // We Can use this to calculate loaded latency
        if (urltype === "load" || urltype === "unload" || urltype2 === "load" || urltype2 === "unload") {
            var split_loaded_urls = [];
            for (var i = 0; i < form2.length; i++) {
                //console.log(typeof urls[i], urls[i]);
                var parts = form2[i].split("/");
                var split_loaded_url = parts.slice(3).join("/");
                split_loaded_urls.push(split_loaded_url);
            }
        }

        console.log("Url types: ", urltype, " ", urltype2);
        //Begin parsing each event in the Netlog data.
        events.forEach((eventData, index) => {
            try {
                //const eventData = JSON.parse(eachEvent);
                /**
                Check #0
                I had initially placed the check for loaded latency here, but I later moved it to after the unloaded latency check.
                I am leaving this comment here as a placeholder for future reference.
               */

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
                        eventData.type === EVENT_TYPES.URL_REQUEST_JOB_FILTERED_BYTES_READ
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
                /**check #2:
                Now that we have recorded the source ID of the first event in an event stream that came from the server, we can check subsequent events
                to see if they have an ID that matches. If the ID is in the results, we can look to see if it is the right event type.
                If the source is not recognized, it does not come from the speed test server and is irelevant.
                */
                if (
                    results.some(result => result.sourceID && result.sourceID.id === eventData.source.id)
                ) {
                    //check #3a --> Download events
                    // check if  1) this event type is 123(URL_REQUEST_JOB_FILTERED_BYTES_READ) or 122(URL_REQUEST_BYTES_READ)
                    // 2) event has params property
                    // 3) url type is download
                    // 4) must have byte_count property

                    //if ((eventData.type === 123 || eventData.type === 122) && eventData.hasOwnProperty('params') && (urltype == "download") && eventData.params.hasOwnProperty('byte_count')) {
                    // 123/122 --> 136(both michwave and spacelink)
                    if ((eventData.type === EVENT_TYPES.URL_REQUEST_JOB_FILTERED_BYTES_READ) && eventData.hasOwnProperty('params') && (urltype == "download") && eventData.params.hasOwnProperty('byte_count')) {
                        let existingIdIndex = byte_time_list.findIndex(item => item.id === eventData.source.id);
                        if (existingIdIndex === -1) {
                            // If id does not exist, add it to byte_time_list (progress will store an object containing the byte_count and timestamp)
                            byte_time_list.push({ id: eventData.source.id, type: urltype, progress: [] });
                            existingIdIndex = byte_time_list.length - 1; //
                        }
                        // Push new progress values
                        byte_time_list[existingIdIndex].progress.push({ bytecount: eventData.params.byte_count, time: eventData.time }); //For larger test sizes, there will be multiple events associated with that ID
                        //type 160 --> used for debugging, this if statement can be ignored
                        if (eventData.params.hasOwnProperty('source_dependency') && eventData.type === 160) {
                            // console.log(eventData.params.source_dependency.id);
                        }
                        //check #3b --> upload events
                        //similar to download, but event type is 450(UPLOAD_DATA_STREAM_READ) and the event must have a current_position attribute
                        // 450 --> 509(michwave) --> 514 (spacelink) --> 502(merit) //also edited to check both urltype 1 and urltype 2
                    } else if (eventData.type === EVENT_TYPES.UPLOAD_DATA_STREAM_READ && eventData.hasOwnProperty('params') && ((urltype == "upload" || urltype2 == "upload") && eventData.params.hasOwnProperty('current_position'))) {
                        let existingIdIndex = current_position_list.findIndex(item => item.id === eventData.source.id);
                        if (existingIdIndex === -1) {
                            // If id does not exist, add it to current_position_list
                            current_position_list.push({ id: eventData.source.id, type: urltype, progress: [] });
                            existingIdIndex = current_position_list.length - 1;
                        }
                        // Push new progress values (larger uploads may have multiple events recording current position, similar to how large downloads may have multiple events for byte_count)
                        current_position_list[existingIdIndex].progress.push({ current_position: eventData.params.current_position, time: eventData.time });
                    }


                    /**check #4 --> latency
                    To calculate latency, we need to find the events that are of type 176 (HTTP_TRANSACTION_SEND_REQUEST_HEADERS).
                    This signifies the beginning of the transaction, and the time stamp for this event will be recorded as "send_time"

                    We also need to find the events that are of type 181 (HTTP_TRANSACTION_RECEIVE_RESPONSE_HEADERS).
                    This event is the end of the transaction, and the timestamp will be recorded as "recv_time"

                    Latency = "recv_time" - "send_time"

                    The contents for one source ID are as follows:
                    {
                    "sourceID": 6141,
                    "send_time": [a_number],
                    "recv_time": [a_number]
                    }

                    events that have params.line are of event type 176 (HTTP_TRANSACTION_SEND_REQUEST_HEADERS)
                    params.line should contain the parameters from the url (which were gathered earlier in the script)
                    */
                    //Start by checking for event 176 (HTTP_TRANSACTION_SEND_REQUEST_HEADERS) - the attributes of the url are in params.line
                    if (
                        eventData.hasOwnProperty('params') &&
                        typeof (eventData.params) === 'object' &&
                        eventData.params.hasOwnProperty('line')
                        && ((urltype == "load") || (urltype == "unload") || (urltype2 == "load") || (urltype2 == "unload"))
                        && split_urls.some(url => eventData.params.line.includes(url))
                    ) {
                        //176 -> 219(michwave) --> 224(spacelink) --> 213 (merit)
                        if (eventData.type === EVENT_TYPES.HTTP_TRANSACTION_SEND_REQUEST_HEADERS) { //event 219 is for manually collected tests
                            const id = eventData.source;
                            const existingIdIndex = latency_results.findIndex(item => item.sourceID === eventData.source.id); //look for the source ID
                            if (existingIdIndex !== -1) {
                                // If id already exists, add to the same dictionary item
                                if (!latency_results[existingIdIndex].send_time) {
                                    latency_results[existingIdIndex].send_time = []; //Why make it a list? There is only one "send_time" value
                                }
                                latency_results[existingIdIndex].send_time.push(eventData.time);
                            } else {
                                //add to the list if the id is not already in the list
                                latency_results.push({ sourceID: eventData.source.id, send_time: [eventData.time] });
                            }
                        }
                    }
                    //If the event is http recieve response headers, then add timestamp as "recv_time"
                    //181 -> 224(michwave) -> 229(spacelink) --> 218(merit)
                    if (eventData.type === EVENT_TYPES.HTTP_TRANSACTION_READ_RESPONSE_HEADERS && latency_results.some(item => item.sourceID === eventData.source.id)) { //event 224 for manual tests
                        const existingIdIndex = latency_results.findIndex(item => item.sourceID === eventData.source.id);
                        if (existingIdIndex !== -1) {
                            if (!latency_results[existingIdIndex].recv_time) {
                                latency_results[existingIdIndex].recv_time = [];
                            }
                            // If id already exists, add to the same dictionary item
                            latency_results[existingIdIndex].recv_time.push(eventData.time);
                        } else {
                            latency_results.push({ sourceID: eventData.source.id, recv_time: [eventData.time] });
                        }
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
                    eventData.params.hasOwnProperty('line')
                    && ((urltype == "load") || (urltype == "unload") || (urltype2 == "load") || (urltype2 == "unload"))
                    && split_loaded_urls.some(url => String(eventData.params.line).includes(url))
                ) { //176 -> 219(michwave) --> 224(spacelink) --> 231(merit)
                    if (eventData.type === EVENT_TYPES.HTTP_TRANSACTION_SEND_REQUEST_HEADERS) {
                        const id = eventData.source;
                        const existingIdIndex = loaded_latency_results.findIndex(item => item.sourceID === eventData.source.id); //look for the source ID
                        if (existingIdIndex !== -1) {
                            // If id already exists, add to the same dictionary item
                            if (!loaded_latency_results[existingIdIndex].send_time) {
                                loaded_latency_results[existingIdIndex].send_time = []; //Why make it a list? There is only one "send_time" value
                            }
                            loaded_latency_results[existingIdIndex].send_time.push(eventData.time);
                        } else {
                            //add to the list if the id is not already in the list
                            loaded_latency_results.push({ sourceID: eventData.source.id, send_time: [eventData.time] });
                        }
                    }
                } //181 -> 224 (michwave) -> 229 (spacelink)
                if (eventData.type === EVENT_TYPES.HTTP_TRANSACTION_READ_RESPONSE_HEADERS && loaded_latency_results.some(item => item.sourceID === eventData.source.id)) {
                    const id = eventData.source;
                    const existingIdIndex = loaded_latency_results.findIndex(item => item.sourceID === eventData.source.id);
                    if (existingIdIndex !== -1) {
                        if (!loaded_latency_results[existingIdIndex].recv_time) {
                            loaded_latency_results[existingIdIndex].recv_time = [];
                        }
                        // If id already exists, add to the same dictionary item
                        loaded_latency_results[existingIdIndex].recv_time.push(eventData.time);
                    } else {
                        loaded_latency_results.push({ sourceID: eventData.source.id, recv_time: [eventData.time] });
                    }
                }

            } catch (error) {
                console.error("Error parsing line", index, ":", error);
            }
        });

        // Write byte_time_list (id, type, and progress [{bytecount, timestamp}]
        writeFileSync('byte_time_list.json', JSON.stringify(byte_time_list, null, 2));
        console.log("byte list before functions: ", byte_time_list.length);

        //write loaded latency send an receive time to loaded_latency.json
        writeFileSync('loaded_latency.json', JSON.stringify(loaded_latency_results, null, 2));

        //if type is upload, write the current_position_list to a file
        console.log("length of current_position list: ", current_position_list.length);
        if (urltype == "upload") {
            writeFileSync('current_position_list.json', JSON.stringify(current_position_list, null, 2));
        }

        //write latency_results list to the latency file --(source ID, send and receive time)
        console.log("number of unloaded latency events: ", latency_results.length);
        writeFileSync('latency.json', JSON.stringify(latency_results, null, 2));


    } catch (error) {
        console.error("Error reading the file:", error);
    }
})();

// You can continue with your fs.readFile logic here
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


    const uploadDirPath = path.join(uploadDir, 'httpStreamJobIds.txt');

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
        //event type HTTP_STREAM_REQUEST_BOUND_TO_JOB  - 173(michwave) --> 174(spacelink) --> 171(merit)
        events.forEach((eventData, index) => {
            if (
                eventData.type === EVENT_TYPES.HTTP_STREAM_REQUEST_BOUND_TO_JOB &&
                eventData.params?.source_dependency &&
                list.includes(eventData.source?.id)
            ) {
                http_stream_job_ids.push([eventData.source.id, eventData.params.source_dependency.id]);
            }
        });

    } catch (error) {
        console.error("Error:", error);
    } finally {
        //console.log("http stream job ids: ", http_stream_job_ids);
        if (fs.existsSync(uploadDirPath)) {
            console.log(`\nNote: httpStreamJobIds.txt already exists in ${uploadDir}`);
        }

        writeFileSync('httpStreamJobIds.txt', http_stream_job_ids.join('\n'));
    }
};



/**
Socket - endpoint for communication, allows for data exchange using network protocols
For every http stream ID, there is an entry.
//An example entry is [ 5781, 5783, 5759 ] where 5781 is the http stream source ID, 5783 is the source dependency ID, and 5759 is the socket ID
//the socket id identifies the connection endpoint (IP addr + port + protocol)

*/
const processSocketIds = () => {
    socketIds = [];
    // Resolve absolute path to upload directory based on urlPath
    const absoluteUrlPath = path.resolve(urlPath);
    const uploadDir = path.dirname(absoluteUrlPath);

    // Paths inside the upload directory
    const httpStreamIdsPath = path.join(uploadDir, 'httpStreamJobIds.txt');
    const socketIdsPath = path.join(uploadDir, 'socketIds.txt');

    try {
        // Validate required files
        checkFilePath(filePath);
        checkFilePath(httpStreamIdsPath);

        // Read and parse the main file
        const data = readFileSync(filePath);
        const parsedData = JSON.parse(data);
        const events = parsedData.events;

        // Read http stream job IDs
        const httpstreamJobs = readFileSync(httpStreamIdsPath);

        if (httpstreamJobs.length !== 0) {
            // Parse the HTTP stream jobs
            httpstreamList = httpstreamJobs.split('\n').map(item => parseInt(item.split(',')[1]));
            httpsourceID = httpstreamJobs.split('\n').map(item => parseInt(item.split(',')[0]));

            //event type SOCKET_POOL_BOUND_TO_SOCKET -- 114(michwave) -->114(spacelink) --> 112(merit)
            events.forEach((eventData, index) => {
                if (eventData.hasOwnProperty('params') &&
                    eventData.params.hasOwnProperty('source_dependency') &&
                    eventData.type === 114) {
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
        // Write to socketIds.txt in the upload directory
        writeFileSync('socketIds.txt', socketIds.join('\n'));
    }
};

/**
looks for events that have the params.byte_count property
 */
const processByteCounts = () => {
    // Resolve absolute path to upload directory based on urlPath
    const absoluteUrlPath = path.resolve(urlPath);
    const uploadDir = path.dirname(absoluteUrlPath);

    // Paths inside the upload directory
    const socketIdsPath = path.join(uploadDir, "socketIds.txt");
    const byteTimeListPath = path.join(uploadDir, "socket_byte_time_list.json");

    let events_with_byte_counts = [];
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
            urlSourceID = socketdata.split('\n').map(item => parseInt(item.split(',')[0]));
            httpID = socketdata.split('\n').map(item => parseInt(item.split(',')[1]));
            socketID = socketdata.split('\n').map(item => parseInt(item.split(',')[2]));

            events.forEach((eventData, index) => {
                if (eventData.hasOwnProperty('params') &&
                    eventData.params.hasOwnProperty('byte_count') &&
                    (
                    eventData.type === EVENT_TYPES.URL_REQUEST_JOB_FILTERED_BYTES_READ ||
                    eventData.type === EVENT_TYPES.URL_REQUEST_BYTES_READ ||
                    eventData.type === EVENT_TYPES.URL_REQUEST_JOB_FILTERED_BYTES_READ_NEW
                )) {
                    //debug pring
                    console.log("Matched event:", eventData.type, eventData.source.id, eventData.params.byte_count);
                    //const eventIndex = socketID.indexOf(eventData.source.id);
                     let socketRowIndex = -1;
                    for (let i = 0; i < urlSourceID.length; i++) {
                        if (urlSourceID[i] === eventData.source.id || httpID[i] === eventData.source.id) {
                            socketRowIndex = i;
                            break;
                        }
                    }
                    if (socketRowIndex !== -1) {
                        const sid = socketID[socketRowIndex];
                        // Add new entry if socket ID not found
                        if (!byte_time_list.some(item => item.id === sid)) {
                            byte_time_list.push({
                                id: sid,
                                type: urltype,
                                progress: []
                            });
                        }
                        // Add progress data
                        byte_time_list.find(item =>
                            item.id === sid
                        ).progress.push({
                            bytecount: eventData.params.byte_count,
                            time: eventData.time
                        });
                    }
                }
                //debug
                console.log("Processing event", eventData.type, eventData.source.id, "socket match:", eventIndex !== -1);
            });
        }
    } catch (error) {
        console.error("Error:", error);
    } finally {
        // process bytes counts at the socket level
        //writeFileSync('socket_byte_time_list.json', JSON.stringify(byte_time_list, null, 2));
        writeFileSync('socketIds.txt', socketIds.map(row => row.join(',')).join('\n'));
    }
};

console.log("Testing url types: ", urltype, "and", urltype2);
processHttpStreamJobIds();
processSocketIds();
//At this point in time, we are only looking at the byte counts at the socket level for upload tests only.
if (urltype == "upload") {
    processByteCounts();
}

// Since httpStreamJobIds is an intermediary file, we can delete it (socketIds.txt contains the same information)
//  #FIXME: why even write it to a file in the first place, just save it as a variable....
deleteFile("httpStreamJobIds.txt")


// --------------------------------------------End of Program--------------------------------------------
// This is the OLD way of doing things, but it is helpful to know socket information for both upload AND download
// if (urltype == "upload") {
//     processHttpStreamJobIds();
//     processSocketIds();
//     processByteCounts();

//     //These are intermediary files that can be deleted at the end
//     //deleteFile("current_position_list.json")
//     //deleteFile("httpStreamJobIds.txt")
//     //deleteFile("socketIds.txt")
// }


