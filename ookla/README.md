## Ookla Conventional Test Information

*This sub-directory contains the tool used for running many Ookla Conventional Tests, as well as the JavaScript files for performing the Netlog filtering*

 #### test-tool

This sub-directory holds the files for performing many Ookla speed tests. There is another README that describes how to set up and run tests. It is designed to be highly configurable, running tests in a variety of orders.
*Note: The Docker file does not work and needs to be corrected*

 #### netlog-filter

 This sub-directory is for netlog filtering. It is designed to extract both download **and** upload events from one netlog file. The main file that runs this is `main.js`. The filter is designed to be called from other places in the repo. It can be called by the test tool to perform filtering **before** uploading files to the AWS bucket.

These files have been refactored a number of times from their original design with some help from AI to speed up the process, but the original logic was written by hand.