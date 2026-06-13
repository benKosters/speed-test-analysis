/**
 *
 * @param {*} urlJSON - A full set of important URLs captured during the initial phase of capturing
 * @returns - An object containing a trimmed set of URLs. These will be used for identifying other netlog events related to these URLs
 */
const splitTestTypeUrls = (urlJSON) => {
    let split_urls = [], split_unloaded_urls = [], split_loaded_urls = [];
    let testUrls = [];
    if (urlJSON.download.length > 0) {
        testType = 'download';
        testUrls = urlJSON.download;
    } else if (urlJSON.upload.length > 0) {
        testType = 'upload';
        testUrls = urlJSON.upload;
    }

    for (var i = 0; i < testUrls.length; i++) {
        var parts = testUrls[i].split("/");
        var split_url = parts.slice(3).join("/");
        split_urls.push(split_url);
    }

    if (urlJSON.unload.length > 0) {
        for (var i = 0; i < urlJSON.unload.length; i++) {
            var parts = urlJSON.unload[i].split("/");
            var split_url = parts.slice(3).join("/");
            split_unloaded_urls.push(split_url);
        }
    }
    if (urlJSON.load.length > 0) {
        for (var i = 0; i < urlJSON.load.length; i++) {
            var parts = urlJSON.load[i].split("/");
            var split_url = parts.slice(3).join("/");
            split_loaded_urls.push(split_url);
        }
    }
    console.log("Example", testType, "split URL:", split_urls[0]);
    console.log("Example loaded split URL:", split_loaded_urls[0]);
    console.log("Example unloaded split URL:", split_unloaded_urls[0])
    return { split_urls: split_urls, split_unloaded_urls: split_unloaded_urls, split_loaded_urls: split_loaded_urls, testType: testType };
};

module.exports = { splitTestTypeUrls };