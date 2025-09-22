/**
 * This file contains utility functions for validating file paths,
 * loading JSON data from files, and splitting URLs by type.
 *
 * This will keep the driver code clean.
 */

const fs = require('fs');
const path = require('path');

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

function convertToJson(inputFile) {
    console.log('path is', inputFile);
    if (!fs.existsSync(inputFile)) {
        throw new Error('Error: File', inputFile, 'does not exist');
    }

    const content = fs.readFileSync(inputFile, 'utf-8');

    let jsonData;
    try {
        jsonData = JSON.parse(content);
    } catch (error) {
        throw new Error('Error: Invalid JSON format in the input file:', error.message);
    }

    const outputFile = path.join(
        path.dirname(inputFile),
        `${path.basename(inputFile, path.extname(inputFile))}.json`
    );

    fs.writeFileSync(outputFile, JSON.stringify(jsonData, null, 2));
    fs.rmSync(inputFile);

    console.log('Successfully converted', inputFile, 'to', outputFile);
}


module.exports = {
    checkFilePath,
    readFileSync,
    writeFileSync,
    parseJSONFromFile,
    convertToJson
};