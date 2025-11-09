/**
 * This file contains utility functions for validating file paths,
 * loading JSON data from files, and splitting URLs by type.
 *
 * This will keep the driver code clean.
 */

const fs = require('fs');

const checkFilePath = (filePath) => {
    if (!fs.existsSync(filePath)) {
        console.log("The file ", filePath, " does not exist.");
        process.exit(1);
    }
};

const readFileSync = (filePath) => {
    const fileContent = fs.readFileSync(filePath, { encoding: 'utf-8' });
    console.log('File ', filePath, ' read success!');
    return fileContent;
};

const writeFileSync = (filePath, data) => {
    fs.writeFileSync(filePath, data);
    console.log('File ', filePath, ' write success!');
};

const parseJSONFromFile = (filePath) => {
    const fileContent = readFileSync(filePath);
    return JSON.parse(fileContent);
};

const ensureDirectoryExists = (dirPath) => {
    //If the directory doesn't exist, create it
    if (!fs.existsSync(dirPath)) {
        console.log("Creating directory:", dirPath);
        fs.mkdirSync(dirPath, { recursive: true });
        return false; // Directory didn't exist before
    }
    return true; // Directory already existed
};

function fixAndParseJSON(jsonString, originalFilePath) {
    // Handles two cases for Puppeteer-collected netlog.json files:
    // 1. Missing closing `]}` at the end
    // 2. Has trailing comma, and is missing closing `]}`

    jsonString = jsonString.trim();

    try {
        return JSON.parse(jsonString);
    } catch (e) {
        console.log('Error with Netlog JSON data:', e.message);

        let fixedString;

        // Check if the string ends with a comma (case 2)
        if (jsonString.endsWith(',')) {
            // Remove trailing comma then add closing brackets
            fixedString = jsonString.slice(0, -1) + ']}';
            console.log('Detected trailing comma, removing it and adding closing brackets');
        } else {
            // Just add closing brackets (case 1)
            fixedString = jsonString + ']}';
            console.log('Adding missing closing brackets');
        }

        try {
            const parsedJson = JSON.parse(fixedString);

            if (parsedJson) {
                console.log('Writing fixed JSON back to file:', originalFilePath);
                fs.writeFileSync(originalFilePath, fixedString);
                console.log('JSON file has been fixed and saved.');
            }

            return parsedJson;
        } catch (e2) {
            console.error('Failed to parse JSON with first fix attempt:', e2.message);

            // If the first attempt failed, try the other approach as a fallback
            try {
                if (jsonString.endsWith(',')) {
                    // We already tried removing the comma, now just try adding brackets
                    fixedString = jsonString + ']}';
                } else {
                    // We already tried adding brackets, now try removing potential hidden comma and adding brackets
                    // This handles cases where there might be a non-visible comma or other character
                    const lastBraceIndex = jsonString.lastIndexOf('}');
                    if (lastBraceIndex !== -1) {
                        fixedString = jsonString.substring(0, lastBraceIndex + 1) + ']}';
                    } else {
                        console.error('Could not find a closing brace to fix the JSON');
                        return null;
                    }
                }

                const parsedJson = JSON.parse(fixedString);

                if (parsedJson) {
                    console.log('Writing fixed JSON back to file with second attempt:', originalFilePath);
                    fs.writeFileSync(originalFilePath, fixedString);
                    console.log('JSON file has been fixed and saved with second approach.');
                }

                return parsedJson;
            } catch (e3) {
                console.error('Failed to parse JSON even after multiple fixing attempts:', e3.message);
                return null;
            }
        }
    }
}


module.exports = {
    checkFilePath,
    readFileSync,
    ensureDirectoryExists,
    writeFileSync,
    parseJSONFromFile,
    fixAndParseJSON
};