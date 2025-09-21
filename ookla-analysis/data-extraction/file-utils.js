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


module.exports = {
    checkFilePath,
    readFileSync,
    ensureDirectoryExists,
    writeFileSync,
    parseJSONFromFile
};