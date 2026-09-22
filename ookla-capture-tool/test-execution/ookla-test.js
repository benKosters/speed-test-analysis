/*
This file should generate 2 outputs:
1. netlog.json - contains the raw network data
2. speedtest_result.json - contains the speedtest results and metadata in JSON format

NOTE: speedtest.net no longer uses pure html/css. It uses Material UI.

*/

import puppeteer from 'puppeteer';
import { Command } from 'commander';
import fs from 'fs';
import path from 'path';
import { createRequire } from 'module';

const require = createRequire(import.meta.url);

const program = new Command();

program
    .option('-c, --connection <type>', 'A single or multiple connection test')
    .option('-s, --server <server>', 'The server to use for the speedtest')
    .option('-l , --location <location>', 'The location of the speed test, if the server is not unique.')
    .option('-o, --output <directory>', 'The output directory for the test results. Default is current directory.');

program.parse(process.argv);

const server = program.opts().server || "Michwave"; //Default to Michwave if no server provided
const num_flows = program.opts().connection || "multi"; //Default to multi if no connection type provided
const location = program.opts().location || ""; //Default to empty if no location provided



function validate_output_directory(outputOption) {
    /**
     * Validate the output directory exists. The default option is./netlog_output
     */
    let output_dir;

    if (outputOption) {
        output_dir = outputOption;
    } else {
        const defaultDir = "./netlog_output";
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
    // const browser = await puppeteer.launch({ headless: false }); // Set to true to run headless
    console.log("Using Puppeteer version:", require('puppeteer/package.json').version);
    const keyarg = "--ssl-key-log-file=" + output_dir + "/sslkeylog.log"; //Save SSL keys to decrypt HTTP traffic
    const netlogarg = "--log-net-log=" + output_dir + "/netlog.json";
    const browser = await puppeteer.launch({ headless: false, args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu'] })
    // const browser = await puppeteer.launch({ headless: false, dumpio: true, args: [keyarg, netlogarg, '--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu', '--disable-features=NetworkService'] }) //#FIXME add keyarg later to save SSL keys
    // NOTE: For ARM architecture, the chrome browser executable path must be specified
    // Example: const browser = await puppeteer.launch({ executablePath: '/usr/bin/chromium-browser', headless: 'new', args: [keyarg, netlogarg, '--no-sandbox'] });

    const page = await browser.newPage();

    await page.setViewport({ width: 1280, height: 800 });
    await page.goto('https://www.speedtest.net/', { waitUntil: 'domcontentloaded', timeout: 60000 });
    // Wait a bit for dynamic content to load
    console.log("page has loaded")
    // await new Promise(resolve => setTimeout(resolve, 3000));

    try {
        // First, change the server
        await page.waitForFunction(() => {
            return Array.from(document.querySelectorAll('button')).some(b => b.textContent.trim() === 'Change Server');
        });
        await page.evaluate(() => {
            const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === 'Change Server');
            btn.click();
        });
        console.log("Selection server button clicked.");

        // Select the search input for the server
        const searchInputSelector = 'input[placeholder="Search"]';
        await page.click(searchInputSelector);
        await page.keyboard.type(server);

        const serverResultSelector = 'ul.MuiList-root > div.MuiListItemButton-root[role="button"]:first-of-type';
        console.log("server selector:", serverResultSelector);
        await page.waitForFunction((expectedServer, selector) => {
            const firstResult = document.querySelector(selector);
            return firstResult && firstResult.textContent.toLowerCase().includes(expectedServer.toLowerCase());
        }, {}, server, serverResultSelector);
        console.log("about to click server button:", serverResultSelector);
        await page.click(serverResultSelector);

        await new Promise(resolve => setTimeout(resolve, 2000));
    }
    catch (e) {
        console.log("There is an error with the server selection process.", e);
        await browser.close();
        return;
    }
    console.log("selecting connection type")
    try {
        const modeName = num_flows.toLowerCase() === "single" ? "Single" : "Multi";
        const modeSelector = `button[aria-label^="${modeName}"][aria-pressed]`;
        await page.waitForSelector(modeSelector);

        const modeIsSelected = await page.$eval(
            modeSelector,
            element => element.getAttribute('aria-pressed') === 'true'
        );
        if (!modeIsSelected) {
            await page.click(modeSelector);
            await page.waitForFunction((selector) => {
                const button = document.querySelector(selector);
                return button && button.getAttribute('aria-pressed') === 'true';
            }, {}, modeSelector);
        }
        console.log(`${modeName} flow test selected.`);
    } catch (e) {
        console.log("Could not change the connection type. Default is a multi flow test.");
    }

    try {
        const gobutton = 'button[aria-label^="start speed test - connection type"]';
        await page.waitForSelector(gobutton);
        await page.click(gobutton);
        console.log("Beginning test.");
    } catch (e) {
        console.log("There is an error with selecting the start button.");
    }

    try {
        const pingLatencySelector = 'svg[aria-label="Idle Latency"] + span';
        const downloadLatencySelector = 'svg[aria-label="Download Latency"] + span';
        const uploadLatencySelector = 'svg[aria-label="Upload Latency"] + span';
        const downloadSpeedSelector = 'svg[aria-label="Receiving Time"] + div h3';
        const uploadSpeedSelector = 'svg[aria-label="Sending Time"] + div h3';

        await page.waitForFunction((selectors) => {
            return selectors.every(selector => {
                const element = document.querySelector(selector);
                return element && Number.isFinite(Number.parseFloat(element.textContent.trim()));
            });
        }, { timeout: 180000 }, [
            pingLatencySelector,
            downloadLatencySelector,
            uploadLatencySelector,
            downloadSpeedSelector,
            uploadSpeedSelector
        ]);

        console.log("Test metrics are complete; collecting results.");
        const latency = await page.$eval(pingLatencySelector, el => el.textContent);
        const downloadLatency = await page.$eval(downloadLatencySelector, el => el.textContent);
        const uploadLatency = await page.$eval(uploadLatencySelector, el => el.textContent);
        const downloadSpeed = await page.$eval(downloadSpeedSelector, el => el.textContent);
        const uploadSpeed = await page.$eval(uploadSpeedSelector, el => el.textContent);

        const time = new Date();
        const testResults = {
            date: time.toISOString().split('T')[0],
            time: time.toTimeString().split(' ')[0],
            server: server,
            connection_type: num_flows,
            ping_latency: parseInt(latency.trim()),
            download_latency: parseInt(downloadLatency.trim()),
            upload_latency: parseInt(uploadLatency.trim()),
            ookla_download_speed: parseFloat(downloadSpeed.trim()),
            ookla_upload_speed: parseFloat(uploadSpeed.trim()),
            chrome_version: await browser.version(),
            puppeteer_version: require('puppeteer/package.json').version,
            client_os: process.platform,
            node_version: process.version
        }

        const resultsPath = path.join(output_dir, 'speedtest_result.json');
        fs.writeFileSync(resultsPath, JSON.stringify(testResults, null, 2));

        console.log("\nPing Latency:", latency);
        console.log("Download Latency:", downloadLatency);
        console.log("Upload Latency:", uploadLatency);
        console.log("\nDownload Speed:", downloadSpeed, "Mbps");
        console.log("Upload Speed:", uploadSpeed, "Mbps\n");
    }
    catch (e) {
        console.log("There was in issue with the test finishing")
    }

    // Third, close the popup and take a screenshot of the results
    try {
        const popupSelector = "#container > div.pre-fold.mobile-test-complete > div.main-content > div > div > div > div.pure-u-custom-speedtest > div.speedtest-view > div > div.main-view > div > div.desktop-app-prompt-modal > div > a > svg";
        await page.waitForSelector(popupSelector, { timeout: 3000 });
        await page.click(popupSelector);
        console.log("Popup closed.");
    }
    catch {
        console.log("Popup did not appear.");
    }

    await page.screenshot({ path: output_dir + '/speedtest_result.png' });
    console.log("Test is complete!");

    console.log("Closing browser to finalize netlog capture");
    // Close the pages before closing the browser to make browser closure faster
    const pages = await browser.pages();
    for (const page of pages) {
        await page.close();
    }
    await browser.close();
    console.log("Browser closed. Netlog capture should now be finalized.");
})();