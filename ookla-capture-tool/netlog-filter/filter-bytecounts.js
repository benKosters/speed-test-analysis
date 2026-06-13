/**
 *  This function captures byte count data from netlog data.
 *  @param {*} eventData - The event data from the netlog
 *  @param {*} results - The results array to store the captured data
 *  @param {*} byte_time_list - The list of byte counts for download events
 *  @param {*} current_position_list - The list of current positions for upload events
 *  @param {*} testType - The type of test ("download" or "upload")
 *  @param {*} logEvent_ids - The mapping of log event names to ID numbers
 */
const captureBytecountData = (eventData, results, byte_time_list, current_position_list, testType, logEvent_ids) => {
    // Check if this event belongs to a recognized source from the speed test server
    if (!results.some(result => result.sourceID && result.sourceID.id === eventData.source.id)) {
        return;
    }

    // Download events
    if (((eventData.type === logEvent_ids['URL_REQUEST_JOB_FILTERED_BYTES_READ']) ||
        (eventData.type === logEvent_ids['URL_REQUEST_BYTES_READ'])) &&
        eventData.hasOwnProperty('params') &&
        (testType == "download") &&
        eventData.params.hasOwnProperty('byte_count')) {

        let existingIdIndex = byte_time_list.findIndex(item => item.id === eventData.source.id);
        if (existingIdIndex === -1) {
            // If id does not exist, add it to byte_time_list (progress will store an object containing the byte_count and timestamp)
            byte_time_list.push({ id: eventData.source.id, type: testType, progress: [] });
            existingIdIndex = byte_time_list.length - 1;
        }
        // Push new progress values
        byte_time_list[existingIdIndex].progress.push({ bytecount: eventData.params.byte_count, time: eventData.time });

        // For testing: print out the source dependency id
        if (eventData.params.hasOwnProperty('source_dependency') && eventData.type === 160) {
            // console.log(eventData.params.source_dependency.id);
        }
    }
    // Upload events
    else if (eventData.type === logEvent_ids['UPLOAD_DATA_STREAM_READ'] &&
        eventData.hasOwnProperty('params') &&
        (testType == "upload") &&
        eventData.params.hasOwnProperty('current_position')) {

        let existingIdIndex = current_position_list.findIndex(item => item.id === eventData.source.id);
        if (existingIdIndex === -1) {
            // If id does not exist, add it to current_position_list
            current_position_list.push({ id: eventData.source.id, type: testType, progress: [] });
            existingIdIndex = current_position_list.length - 1;
        }
        // Push new progress values (larger uploads may have multiple events recording current position, similar to how large downloads may have multiple events for byte_count)
        current_position_list[existingIdIndex].progress.push({ current_position: eventData.params.current_position, time: eventData.time });
    }
};


module.exports = { captureBytecountData };
