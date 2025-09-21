//Import the filesystem and path modules
const fs = require('fs');
const { url } = require('inspector');
const path = require('path');

const map_event_name_to_id = {}; //maps Netlog event names to a number (their IDs) - these IDs change for each test, but the names remain the same


// Check if a file path was provided
const checkFilePath = (filePath) => {
    const outputPath = path.posix.join(folderPath, filePath);

    if (!fs.existsSync(outputPath)) {
        console.log("The file does not exist: " + filePath);
        process.exit(1);
    }
};

// Function to read a file synchronously - from the output directory
const readFileSync = (fileName) => {
    const outputPath = path.posix.join(fileName);
    fileread = fs.readFileSync(outputPath, { encoding: 'utf-8' });
    console.log('File ', outputPath, ' read success!');
    return fileread
};

// Function to write a file synchronously - in the output directory
const writeFileSync = (fileName, data) => {
    const outputPath = path.posix.join(folderPath, fileName); // Construct the output file path
    console.log('File ', outputPath, ' write!');

    fs.writeFileSync(outputPath, data);
    console.log('File ', outputPath, ' write success!');
};

//Function to delete a file from the system - from the output directory
const deleteFile = (fileName) => {
    const filePath = path.posix.join(folderPath, fileName); // Construct the full path to the file
    return fs.unlink(filePath, (err) => {
        if (err) {
            console.error('Error deleting file:', err);
            return;
        }
        console.log('File deleted successfully');
    });
}

//Function that returns the urls type and form
const getUrlTypeAndForm = (urlJSON) => {
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
    return JSON.parse(fileContent);
};

// Read the command line arguments
// const filePath = 'generate_netlog/' + process.argv[2] +'/output/' + process.argv[2] + '.netlog';
// const urlPath = 'generate_netlog/' + process.argv[2] +'/output/' + process.argv[2] + '_urls.txt';

const folderPath = process.argv[2]
const serverName = process.argv[3]
const filePath = folderPath + '/' + serverName + '.netlog'
const urlPath = folderPath + '/' + serverName + '_urls.txt'
console.log(filePath)
console.log(urlPath)
// Check if file paths were provided
if (process.argv.length < 3) {
    console.log("Usage: node netlog.js <server_to_test>");
    process.exit(1);
}

// // Check if the files exist
// checkFilePath(filePath);
// checkFilePath(urlPath);

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

// Read the content of the Netlog file
(() => {
    try {
        console.log("reading")
        const data = readFileSync(filePath);
        const events = data.split('\n').slice(2);

        const byte_time_list = [];
        const current_position_list = [];
        const latency_results = [];
        const results = [];

        if (urltype === "load" || urltype === "unload" || urltype2 === "load" || urltype2 === "unload") {
            var split_urls = [];
            for (var i = 0; i < form.length; i++) {
                // console.log(typeof urls[i], urls[i]);
                var parts = form[i].split("/");
                var split_url = parts.slice(3).join("/");
                split_urls.push(split_url);
            }
        }

        events.forEach((element, index) => {
            if (element.trim() === "") {
                return;
            }
            if (element.slice(-2) === ']}') {
                eachEvent = element.slice(0, -2);
            } else {
                eachEvent = element.slice(0, -1);
            }
            try {
                const eventData = JSON.parse(eachEvent);

                // Check if the eventData meets certain conditions
                if (
                    eventData.hasOwnProperty('params') &&
                    typeof (eventData.params) === 'object' &&
                    eventData.params.hasOwnProperty('url') &&
                    form.some(url => eventData.params.url.includes(url) &&
                        eventData.type === 2
                    )
                ) {
                    if (eventData.source.hasOwnProperty('id')) {
                        const id = eventData.source;
                        results.push({ sourceID: id, index: index, dict: eventData });
                    }
                }

                if (
                    results.some(result => result.sourceID && result.sourceID.id === eventData.source.id)
                ) {
                    if ((eventData.type === 123 || eventData.type === 122) && eventData.hasOwnProperty('params') && (urltype == "download") && eventData.params.hasOwnProperty('byte_count')) {
                        let existingIdIndex = byte_time_list.findIndex(item => item.id === eventData.source.id);
                        if (existingIdIndex === -1) {
                            // If id does not exist, add it to byte_time_list
                            byte_time_list.push({ id: eventData.source.id, type: urltype, progress: [] });
                            existingIdIndex = byte_time_list.length - 1;
                        }
                        // Push new progress values
                        byte_time_list[existingIdIndex].progress.push({ bytecount: eventData.params.byte_count, time: eventData.time });
                        //type 160
                        if (eventData.params.hasOwnProperty('source_dependency') && eventData.type === 160) {
                            // console.log(eventData.params.source_dependency.id);
                        }
                    } else if (eventData.type === 450 && eventData.hasOwnProperty('params') && (urltype == "upload" && eventData.params.hasOwnProperty('current_position'))) {
                        let existingIdIndex = current_position_list.findIndex(item => item.id === eventData.source.id);
                        if (existingIdIndex === -1) {
                            // If id does not exist, add it to current_position_list
                            current_position_list.push({ id: eventData.source.id, type: urltype, progress: [] });
                            existingIdIndex = current_position_list.length - 1;
                        }
                        // Push new progress values
                        current_position_list[existingIdIndex].progress.push({ current_position: eventData.params.current_position, time: eventData.time });
                    }

                    //latency
                    if (
                        eventData.hasOwnProperty('params') &&
                        typeof (eventData.params) === 'object' &&
                        eventData.params.hasOwnProperty('line')
                        && ((urltype == "load") || (urltype == "unload") || (urltype2 == "load") || (urltype2 == "unload"))
                        && split_urls.some(url => eventData.params.line.includes(url))
                    ) {
                        // console.log(eventData)
                        if (eventData.type === 176) {
                            const id = eventData.source;
                            const existingIdIndex = latency_results.findIndex(item => item.sourceID === eventData.source.id);
                            if (existingIdIndex !== -1) {
                                // If id already exists, add to the same dictionary item
                                if (!latency_results[existingIdIndex].send_time) {
                                    latency_results[existingIdIndex].send_time = [];
                                }
                                latency_results[existingIdIndex].send_time.push(eventData.time);
                            } else {
                                latency_results.push({ sourceID: eventData.source.id, send_time: [eventData.time] });
                            }
                        }
                    }

                    if (eventData.type === 181 && latency_results.some(item => item.sourceID === eventData.source.id)) {
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
            } catch (error) {
                console.error("Error parsing line", index, ":", error);
            }
        });
        // Write byte_time_list to file
        // writeFileSync('analysis/output/' + process.argv[2] + '/byte_time_list.json', JSON.stringify(byte_time_list, null, 2));
        writeFileSync('byte_time_list.json', JSON.stringify(byte_time_list, null, 2));
        if (urltype == "upload") {
            // writeFileSync('analysis/output/' + process.argv[2] + '/current_position_list.json', JSON.stringify(current_position_list, null, 2));
            writeFileSync('current_position_list.json', JSON.stringify(current_position_list, null, 2));

        }
        // writeFileSync('analysis/output/' + process.argv[2] + '/latency.json', JSON.stringify(latency_results,null,2))
        writeFileSync('latency.json', JSON.stringify(latency_results, null, 2))

        console.log("Completion Successful")
    } catch (error) {
        console.error("Error reading the file:", error);
    }
})();

// You can continue with your fs.readFile logic here
const processHttpStreamJobIds = () => {
    http_stream_job_ids = [];
    try {
        checkFilePath(filePath);

        const data = readFileSync(filePath);
        const events = data.split('\n').slice(2);

        // Check if the file exists
        checkFilePath(urlPath);

        const currentPosList = parseJSONFromFile("current_position_list.json");
        // checkFilePath('generate_netlog/' + process.argv[2] +'/output/current_position_list.json');
        checkFilePath('current_position_list.json');

        // Populate the list array
        const list = currentPosList.map(item => item.id);
        // console.log(list);

        events.forEach((element, index) => {
            if (element.trim() === "") {
                return;
            }
            if (element.slice(-2) === ']}') {
                eachEvent = element.slice(0, -2);
            } else {
                eachEvent = element.slice(0, -1);
            }

            const eventData = JSON.parse(eachEvent);

            if (eventData.hasOwnProperty('params') && eventData.params.hasOwnProperty('source_dependency') && eventData.type === 160) {
                if (list.includes(eventData.source.id)) {
                    // console.log("Http stream job ID:", eventData.params.source_dependency.id);
                    http_stream_job_ids.push([eventData.source.id, eventData.params.source_dependency.id]);
                }
            }

        });
        // writeFileSync('generate_netlog/' + process.argv[2] + '/output/httpStreamJobIds.txt', http_stream_job_ids.join('\n'));
        writeFileSync('httpStreamJobIds.txt', http_stream_job_ids.join('\n'));

    } catch (error) {
        console.error("Error reading the file:", error);
    }
};

const processSocketIds = () => {
    socketIds = []
    try {
        const data = readFileSync(filePath);
        const events = data.split('\n').slice(2);

        // Read the URLs from the file
        // Read the content of the byte_time_list.json file
        // checkFilePath('generate_netlog/' + process.argv[2] +'/output/httpStreamJobIds.txt');
        checkFilePath('httpStreamJobIds.txt');

        // httpstreamJobs = readFileSync('generate_netlog/' + process.argv[2] + '/output/httpStreamJobIds.txt')
        httpstreamJobs = readFileSync('httpStreamJobIds.txt')

        // const httpstreamList = httpstreamJobs.split('\n');
        if (httpstreamJobs.length !== 0) {
            //currently each item in the list has a comma, split each of them and only taee the second value
            httpstreamList = httpstreamJobs.split('\n').map(item => parseInt(item.split(',')[1]));
            httpsourceID = httpstreamJobs.split('\n').map(item => parseInt(item.split(',')[0]));
            events.forEach((element, index) => {
                if (element.trim() === "") {
                    return;
                }
                if (element.slice(-2) === ']}') {
                    eachEvent = element.slice(0, -2);
                } else {
                    eachEvent = element.slice(0, -1);
                }

                const eventData = JSON.parse(eachEvent);

                if (eventData.hasOwnProperty('params') && eventData.params.hasOwnProperty('source_dependency') && eventData.type === 108) {
                    const eventIndex = httpstreamList.indexOf(eventData.source.id);
                    if (eventIndex !== -1) {
                        // console.log("Socket ID", eventData.params.source_dependency.id);
                        socketIds.push([httpsourceID[eventIndex], httpstreamList[eventIndex], eventData.params.source_dependency.id]);
                    }
                }
            });
        }
        // writeFileSync('generate_netlog/' + process.argv[2] + '/output/socketIds.txt', socketIds.join('\n'));
        writeFileSync('socketIds.txt', socketIds.join('\n'));

    } catch (error) {
        console.error("Error reading the file:", error);
    }
};

const processByteCounts = () => {
    try {
        const data = readFileSync(filePath);
        const events = data.split('\n').slice(2);

        // Read the URLs from the file
        // Read the content of the byte_time_list.json file
        // checkFilePath('generate_netlog/' + process.argv[2] +'/output/socketIds.txt');
        checkFilePath('socketIds.txt');

        // socketdata = readFileSync('generate_netlog/' + process.argv[2] + '/output/socketIds.txt')
        socketdata = readFileSync('socketIds.txt')

        const byte_time_list = [];

        // const httpstreamList = httpstreamJobs.split('\n');
        if (socketdata.length !== 0) {
            urlSourceID = socketdata.split('\n').map(item => parseInt(item.split(',')[0]));
            httpID = socketdata.split('\n').map(item => parseInt(item.split(',')[1]));
            socketID = socketdata.split('\n').map(item => parseInt(item.split(',')[2]));

            events.forEach((element, index) => {
                if (element.trim() === "") {
                    return;
                }
                if (element.slice(-2) === ']}') {
                    eachEvent = element.slice(0, -2);
                } else {
                    eachEvent = element.slice(0, -1);
                }

                const eventData = JSON.parse(eachEvent);

                if (eventData.hasOwnProperty('params') && eventData.params.hasOwnProperty('byte_count')) {
                    const eventIndex = socketID.indexOf(eventData.source.id);
                    if (eventIndex !== -1) {
                        if (!byte_time_list.some(item => item.id === urlSourceID[eventIndex])) {
                            byte_time_list.push({ id: urlSourceID[eventIndex], type: urltype, progress: [] });

                        }
                        byte_time_list.find(item => item.id === urlSourceID[eventIndex]).progress.push({ bytecount: eventData.params.byte_count, time: eventData.time });
                    }
                }
            }
            )
        }
        // writeFileSync('analysis/output/' + process.argv[2] + '/byte_time_list.json', JSON.stringify(byte_time_list, null, 2));

        writeFileSync('byte_time_list.json', JSON.stringify(byte_time_list, null, 2));
    } catch (error) {
        console.error("Error reading the file:", error);
    }
};

//These only need to be called if the urltype was upload as only upload requires multiple passes.
if (urltype == "upload") {
    processHttpStreamJobIds();
    processSocketIds();
    processByteCounts();

    //These are intermediary files that can be deleted at the end
    // deleteFile('analysis/output' + process.argv[2] + '/current_position_list.json');
    // deleteFile('analysis/output' + process.argv[2] + '/httpStreamJobIds.txt');
    // deleteFile('analysis/output' + process.argv[2] + '/socketIds.txt');

    deleteFile('current_position_list.json');
    deleteFile('httpStreamJobIds.txt');
    deleteFile('socketIds.txt');

}

