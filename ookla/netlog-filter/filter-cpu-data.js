/**
 * Filter CPU metrics from JSON and save to CSV
 * Extracts date, time, individual CPU idle percentages, and the mean idle percentage amont all CPUs.
 */

const fs = require('fs');
const path = require('path');
const { readFileSync, writeFileSync, checkFilePath, ensureDirectoryExists } = require('./file-utils');

function parseTimestamp(timestamp) {
    const date = new Date(timestamp);
    const dateStr = date.toISOString().split('T')[0]; // YYYY-MM-DD
    const timeStr = date.toISOString().split('T')[1].split('.')[0]; // HH:MM:SS
    return { date: dateStr, time: timeStr };
}

function processCPUIdleData(cpuidle) {
    const cpuKeys = Object.keys(cpuidle).sort((a, b) => {
        // Sort by CPU number (extract number from 'cpuX_idle')
        const numA = parseInt(a.match(/\d+/)[0]);
        const numB = parseInt(b.match(/\d+/)[0]);
        return numA - numB;
    });

    const cpuValues = cpuKeys.map(key => cpuidle[key]);
    const mean = cpuValues.reduce((sum, val) => sum + val, 0) / cpuValues.length;

    return {
        cpuKeys,
        cpuValues,
        mean
    };
}

function convertToCSV(data) {
    if (data.length === 0) {
        return '';
    }

    const rows = [];

    // Determine CPU columns from first entry
    const firstEntry = data[0];
    const { cpuKeys } = processCPUIdleData(firstEntry.cpuidle);

    const header = ['date', 'time', ...cpuKeys, 'mean_idle'];
    rows.push(header.join(','));

    for (const entry of data) {
        const { date, time } = parseTimestamp(entry.timestamp);
        const { cpuValues, mean } = processCPUIdleData(entry.cpuidle);

        const row = [
            date,
            time,
            ...cpuValues.map(val => val.toFixed(6)),
            mean.toFixed(6)
        ];
        rows.push(row.join(','));
    }

    return rows.join('\n');
}

function filterCPUData(inputFilePath, outputFilePath) {
    // Validate input file
    checkFilePath(inputFilePath);

    // Read file content
    console.log('Reading CPU metrics from:', inputFilePath);
    const fileContent = readFileSync(inputFilePath);

    // CPU output will generate 2 json objects: one for system data, and one for cpu data
    const lines = fileContent.trim().split('\n');

    let cpuMetrics = null;

    // Find the JSON object that contains the "data" array
    for (const line of lines) {
        if (!line.trim()) continue; // Skip empty lines

        try {
            const obj = JSON.parse(line);
            if (obj.data && Array.isArray(obj.data)) {
                cpuMetrics = obj;
                break;
            }
        } catch (error) {
            console.error('Warning: Failed to parse line:', error.message);
            continue;
        }
    }

    // Validate that we found CPU data
    if (!cpuMetrics || !cpuMetrics.data) {
        console.error('Error: Could not find a valid "data" array in the JSON file');
        process.exit(1);
    }

    console.log(`Found ${cpuMetrics.data.length} data points`);

    // Convert to CSV
    const csvContent = convertToCSV(cpuMetrics.data);

    // Determine output file path
    if (!outputFilePath) {
        const inputDir = path.dirname(inputFilePath);
        const inputBasename = path.basename(inputFilePath, '.json');
        outputFilePath = path.join(inputDir, `cpu_data.csv`);
    }

    // Ensure output directory exists
    const outputDir = path.dirname(outputFilePath);
    ensureDirectoryExists(outputDir);

    // Write to file
    writeFileSync(outputFilePath, csvContent);
    console.log('CSV file created successfully:', outputFilePath);
}

/**
 * Main driver function to filter CPU data from a test directory
 * @param {string} testDirectoryPath - Path to the test directory containing cpu_metrics.json
 * @returns {object|null} Object with output file path if successful, null if no CPU data found
 */
function filterCpuData(testDirectoryPath) {
    const cpuMetricsPath = path.join(testDirectoryPath, 'cpu_metrics.json');

    if (!fs.existsSync(cpuMetricsPath)) {
        console.log('No CPU metrics file found, skipping CPU filtering');
        return null;
    }

    const outputPath = path.join(testDirectoryPath, 'cpu_data.csv');
    filterCPUData(cpuMetricsPath, outputPath);

    return { outputPath };
}

// Export functions for use as module
module.exports = {
    filterCpuData,
    filterCPUData,
    parseTimestamp,
    processCPUIdleData,
    convertToCSV
};
