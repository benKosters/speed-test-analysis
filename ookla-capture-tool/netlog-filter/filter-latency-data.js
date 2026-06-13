const captureLatencyData = (eventData, latencyStreams, urlList, eventType, logEvent_ids) => {
    const sourceId = eventData.source.id;
    const time = Number(eventData.time);

    // Find existing stream or create new one
    let existingStream = latencyStreams.find(item => item.id === sourceId);

    if (!existingStream) {
        existingStream = {
            id: sourceId,
            send_time: null,
            recv_time: null,
            rtt: null
        };
        latencyStreams.push(existingStream);
    }

    // Handle send time - event 176 (HTTP_TRANSACTION_SEND_REQUEST_HEADERS)
    if (eventData.type === logEvent_ids['HTTP_TRANSACTION_SEND_REQUEST_HEADERS'] &&
        eventData.params?.line) {
        existingStream.send_time = time;
    }

    // Handle receive time - event 181 (HTTP_TRANSACTION_READ_RESPONSE_HEADERS)
    if (eventData.type === logEvent_ids['HTTP_TRANSACTION_READ_RESPONSE_HEADERS']) {
        existingStream.recv_time = time;
        // Calculate RTT if we have both times
        if (existingStream.send_time !== null && existingStream.recv_time !== null) {
            existingStream.rtt = existingStream.recv_time - existingStream.send_time;
        }
    }
};

const calculateLatencyStatistics = (latencyStreams) => {
    // Make sure both send and receive times are present
    const validRtts = latencyStreams
        .filter(stream => stream.rtt !== null && stream.rtt >= 0)
        .map(stream => stream.rtt);

    if (validRtts.length === 0) {
        return {
            count_rtt: 0,
            mean_rtt: 0,
            median_rtt: 0
        };
    }

    const count_rtt = validRtts.length;

    const sum = validRtts.reduce((acc, rtt) => acc + rtt, 0);
    const mean_rtt = sum / count_rtt;

    const sortedRtts = [...validRtts].sort((a, b) => a - b);
    let median_rtt;

    if (sortedRtts.length % 2 === 0) {
        // Even number of values - average of middle two
        const mid1 = sortedRtts[sortedRtts.length / 2 - 1];
        const mid2 = sortedRtts[sortedRtts.length / 2];
        median_rtt = (mid1 + mid2) / 2;
    } else {
        median_rtt = sortedRtts[Math.floor(sortedRtts.length / 2)];
    }

    return {
        count_rtt: count_rtt,
        mean_rtt: Math.round(mean_rtt * 100) / 100,
        median_rtt: Math.round(median_rtt * 100) / 100
    };
};

const updateAllLatencyStatistics = (latency_data) => {
    latency_data.test_latency.latency_ms = calculateLatencyStatistics(latency_data.test_latency.streams);
    latency_data.unloaded_latency.latency_ms = calculateLatencyStatistics(latency_data.unloaded_latency.streams);
    latency_data.loaded_latency.latency_ms = calculateLatencyStatistics(latency_data.loaded_latency.streams);

    console.log("\nLatency metrics using GET and POST URLs:")
    console.log("Test latency statistics:", latency_data.test_latency.latency_ms);
    console.log("Unloaded latency statistics:", latency_data.unloaded_latency.latency_ms);
    console.log("Loaded latency statistics:", latency_data.loaded_latency.latency_ms);
};


module.exports = { captureLatencyData, calculateLatencyStatistics, updateAllLatencyStatistics };