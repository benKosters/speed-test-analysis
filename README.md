## Ookla Speed Test Analysis

This repository holds all scripts that were created to assist with the analysis of Ookla's web-based `speedtest.net` Internet speed test platform. This README gives a summary of the purpose and organization of how files are organized. For sub-directories that are much larger, there are also README files there that go into deeper detail.

### General Information

Throughout this experiment, there were two methods for capturing Netlog data: manually capturing netlog data through the browser, and using an automated tool to run tests via Puppetteer. For the automated tests, the structure of the data files is set so automation of the analysis can occur smoothly. Most tests used during this research were captured manually, but **if** manually captured tests are used, here are some practices to keep in mind when performing analysis:

1) Structure of Automated Tests
> Tests generally follow this structure:

```
test-set/                                  # The overarching instance of when a suite of tests were performed
└── test-batch/                            # A set can be broken down into batches - this is just breaking down the test set to make it more manageable
    └── test-name/                              # This is one speed test on `speedtest.net` - one download test, and one upload ookla-test
        ├── download/
        └── upload/
```

2) Location of Netlog Files

It is best practice to have a raw netlog file saved in its own directory - this way all files that get populated are associated with that one test

## Setup

`npm install`




### Repository Organization

#### ``automation-scripts``

Contains scripts that were designed to help speed up the process of automating tasks with the analysis of the Ookla tests. All these scripts were written in bash with the help of AI. All scripts have a -h flag to describe the parameters in more detail and give examples how they can be used.

- **download_data_from_aws_s3_bucket.sh**: Automates the downloading of raw test data from an AWS S3 bucket to your local machine.

- **process-netlog-data.sh**: This script automates the pipeline of processing **ONE** Ookla speedtest. This script filters out the important Netlog data, and performs the default configuration for throughput modeling.

- **process-many-tests.sh**: This script automates the pipeline for processing **MANY** Ookla speedtests at once (basically it calls process-netlog-data.sh on an entire suite of tests or just a single batch). To successfully run this script, all Ookla tests must follow the same structure they were generated in (test-set/test-batch/ookla-test)

#### ``data-analysis``

This directory is quite large. It is grouped into two sub-directories:
> `single-test-analysis/`
 This sub-directory holds all files for normalizing the filtered Netlog data, and computing throughput models of various configurations for the **upload** or **download** portion of an Ookla test. It is important to note that the target is the download or upload portion and not the whole Ookla test itself. These scripts also generate metrics about the results, which are saved in the corresponding `upload/` or `download/` directory for an Ookla test.

>`comparative-analysis/`
This sub-directory contains files that are used for comparing results **accross** different Ookla tests. There are python scripts that aggregate metrics from individual tests into one, unified csv file that can be used for plotting.

More information on the specific scripts are listed in the README in this sub-directory.

#### ``datasets``

This is just a placeholder directory for storing datasets generated in `data-analysis/comparative-analysis/`.

#### ``ookla``

#### ``rabbits``

A placeholder folder for the (RABBITs toolkit)[https://github.com/CAIDA/rabbits-perf] developed by CAIDA, which was the inital motivation for this project. This toolkit performs a Netlog capture while connecting to one of six possible speed test platforms. This project currently is focused strictly on the behavior of Ookla, but there are future plans for expanding this project to other platforms.

#### ``plot-images``

Also a placeholder folder for keeping images of important plots.

## General Information

For `speedtest.net` tests that were collected using the automated tool, they follow this general structure:

test set >> batch >> test >>upload/download

```
michwave-multi-<date-and-time>/
├── netlog.json                            # Raw netlog data
├── download/
│   ├── download_urls.json                 # Filtered download urls
│   ├── socketIds.txt                      # HTTP stream IDs and corresponding socket IDs
│   ├── byte_time_list.json                # Filtered byte time data for download
│   ├── latency.json                       # Latency information
│   ├── normalized_latency.json            # latency with normalized timestamps
│   ├── socket_ids.txt                     # Socket ID mappings
│   └── plot_images/                       # Created when using --save flag
│       ├── throughput_2ms_interval.png    # Example plot images
│       └── all_flows_2ms_interval.png
└── upload/
    ├── upload_urls.json                   # Filtered upload urls
    ├── byte_time_list.json                # Filtered byte time data for upload(this should be empty for the time being, is used for grouping bytecounts by socket)
    ├── current_position_list.json         # Position list data
    ├── latency.json                       # Latency information
    ├── normalized_latency.json            # latency with normalized timestamps
    ├── socketIds.txt                      # Socket ID mappings
    └── plot_images/                       # Created when using --save flag
        ├── throughput_2ms_interval.png    # Example plot images
        └── all_flows_2ms_interval.png
```


This repository includes all automated tools, data capturing, filtering, and processing scripts associated with

TODO: Include setup section (mention their are other readme files throughout the repo to help with setup)
TODO: Update requirements.txt to remove any uncessary import statements


This repo is organized into the following sections:
```
speed-test-analysis/
├── url_filter.js                              #collects the relevant URLs from raw Netlog data
├── manual_netlog.js                           #filters out the important events for finding throughput and latency for a manually collected test from Ookla only (A separate script is required for a CARROT test)
├── proces_netlog_data.sh                      #a bash script to populate a directory the necessary files after raw netlog data is collected
└── visualizations/
    ├── calculate_plot_throughput.py           # main program to run analysis on raw data after it has been filtered from the raw Netlog data
    ├── plotting_functions.py                  # modularized functions for different variations of graphs
    └──  throughput_calculation_functions.py   #functions used for calculating throughput (a few versions were used for experimentation)
```

The visualization files can be used for BOTH a Ookla test with manually collected netlog data and a CARROT test.
To run the visualization script, use the following command from the root of this directory:
```
python3 visualizations/calculate_plot_throughput.py path/to/directory/containing/filtered/data --save
```
The "save" flag is optional, and will create a subdirectory called "plot_images/" inside the directory where the filtered data is.



##

#### Manual Netlog Captures


#### Automated Netlog Captures
For an ookla test, the first step is making sure the raw netlog data is in a directory... the necessary files will populate inside this directory. It is recommended that the directory is the name of the test, including the server name/type of test (ex: michwave-multi-1/netlog.json). When netlog data is collected for an Ookla test, there are techincally two tests that are collected in one netlog file (upload and download). This is different than a CARROT test, which only performs upload or download. Once all files are populated, the following directory structure will look something like this:


```
michwave-multi-1/
├── netlog.json                            # Raw netlog data
├── download/
│   ├── download_urls.json                 # Filtered download urls
│   ├── socketIds.txt                      # HTTP stream IDs and corresponding socket IDs
│   ├── byte_time_list.json                # Filtered byte time data for download
│   ├── latency.json                       # Latency information
│   ├── normalized_latency.json            # latency with normalized timestamps
│   ├── socket_ids.txt                     # Socket ID mappings
│   └── plot_images/                       # Created when using --save flag
│       ├── throughput_2ms_interval.png    # Example plot images
│       └── all_flows_2ms_interval.png
└── upload/
    ├── upload_urls.json                   # Filtered upload urls
    ├── byte_time_list.json                # Filtered byte time data for upload(this should be empty for the time being, is used for grouping bytecounts by socket)
    ├── current_position_list.json         # Position list data
    ├── latency.json                       # Latency information
    ├── normalized_latency.json            # latency with normalized timestamps
    ├── socketIds.txt                      # Socket ID mappings
    └── plot_images/                       # Created when using --save flag
        ├── throughput_2ms_interval.png    # Example plot images
        └── all_flows_2ms_interval.png
```
When you specific the path to the netlog data, there CAN be other files also present in the directory too.
If these files are already populated and you desire to perform the test with more graphs, be sure to specify the specific upload or download test as the path to the filtered data (ex: /path/michwave-multi-1/upload)
