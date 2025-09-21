/*
This file should generate 2 files:
1. netlog.json - contains the raw network data
2. metadata.json - contains metadata about the test (server, single/multi flow, date of test, etc) #FIXME
*/

const puppeteer = require('puppeteer');
const { Command } = require('commander');

const program = new Command();

program
    .option('-c, --connection <type>', 'A single or multiple connection test')
    .option('-s, --server <server>', 'The server to use for the speedtest')
    .option('-o, --output <directory>', 'The output directory for the test results. Default is current directory.');

program.parse(process.argv);

const server = program.opts().server || "Michwave"; //Default to Michwave if no server provided
const num_flows = program.opts().connection || "multi"; //Default to multi if no connection type provided



function validate_output_directory(outputOption) {
    /**
     * Validate the output directory exists. The default option is./netlog_output
     */
    const fs = require('fs');
    let output_dir;

    if (outputOption) {
        output_dir = outputOption;
    } else {
        const defaultDir = "netlog_output";
        if (!fs.existsSync(defaultDir)) {
            fs.mkdirSync(defaultDir, { recursive: true });
        }
        output_dir = defaultDir;
    }
    console.log('Output directory:', output_dir);
    return output_dir;
}

const output_dir = validate_output_directory(program.opts().output);
console.log('Using server:', server, "with a", num_flows, "flow test.");

(async () => {
    //const browser = await puppeteer.launch({ headless: false }); // Set to true to run headless
    //const keyarg = "--ssl-key-log-file=./sslkeylog.log"; //Save SSL keys to decrypt HTTP traffic
    const netlogarg = "--log-net-log=" + output_dir + "/netlog.json";
    const browser = await puppeteer.launch({ headless: true, args: [netlogarg, '--no-sandbox'] }) //#FIXME add keyarg later to save SSL keys
    const page = await browser.newPage();

    await page.setViewport({ width: 1280, height: 800 });
    await page.goto('https://www.speedtest.net/', { waitUntil: 'networkidle2' });

    //First, change the server
    try {
        // Hit the select server button
        const selectServerSelector = 'div.pure-u-5-12:nth-child(3) > div:nth-child(1) > div:nth-child(1) > div:nth-child(1) > div:nth-child(4) > a:nth-child(1)';
        await page.waitForSelector(selectServerSelector);
        await page.click(selectServerSelector);
        console.log("Selection server button clicked.");

        //wait for the search box, and type the server name
        const searchBoxSelector = '#host-search';
        await page.waitForSelector(searchBoxSelector);
        await page.type(searchBoxSelector, server);
        await new Promise(resolve => setTimeout(resolve, 2000));

        //Select the server that we want
        const serverSelection = `.server-hosts-list > ul:nth-child(2) > li:nth-child(1) > a:nth-child(1)`;
        await page.waitForSelector(serverSelection);
        await page.click(serverSelection);
        await new Promise(resolve => setTimeout(resolve, 2000));
    }
    catch {
        console.log("There is an error with the server selection process.");
        await browser.close();

    }

    //Second, confirm the connection type (single or multi flow)
    try {
        if (num_flows === "Single" || num_flows === "single") {
            const singleFlowSelector = 'a.test-mode:nth-child(4)';
            await page.waitForSelector(singleFlowSelector);
            await page.click(singleFlowSelector);
            console.log("Single flow test selected.");
        }
        else {
            const multiFlowSelector = 'a.test-mode:nth-child(2)';
            await page.waitForSelector(multiFlowSelector);
            await page.click(multiFlowSelector);
            console.log("Multi flow test selected.");
        }
    } catch (e) {
        console.log("Could not change the connection type. Default is a multi flow test.");
    }

    try {
        const gobutton = '.start-text';
        await page.waitForSelector(gobutton);
        await page.click(gobutton);
        console.log("Beginning test.");
    } catch (e) {
        console.log("There is an error with selecting the start button.");
    }

    // Wait for 35 seconds for the test to finish (the test is 30 seconds) - rudimentary, but works for now
    await new Promise(resolve => setTimeout(resolve, 35000));

    // Third, close the popup and take a screenshot of the results
    try {
        const popupSelector = "#container > div.pre-fold.mobile-test-complete > div.main-content > div > div > div > div.pure-u-custom-speedtest > div.speedtest-view > div > div.main-view > div > div.desktop-app-prompt-modal > div > a > svg";
        await page.waitForSelector(popupSelector, { timeout: 3000 });
        await page.click(popupSelector);
        console.log("Popup closed.");
    } catch {
        console.log("Popup did not appear.");
    }

    await page.screenshot({ path: output_dir + '/speedtest_result.png' });
    console.log("Test is complete!");

    // Ensure the browser is closed gracefully to finalize netlog capture
    console.log("Closing browser to finalize netlog capture...");
    await browser.close();
    console.log("Browser closed. Netlog capture should now be finalized.");
})();