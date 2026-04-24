## Ookla Speed Test Analysis

This repository holds all scripts that were created to assist with the analysis of Ookla's web-based `speedtest.net` Internet speed test platform. This README gives a summary of the purpose and organization of how files are organized. For sub-directories that are much larger, there are also README files there that go into deeper detail.


TODO: Include setup section (mention their are other readme files throughout the repo to help with setup)
TODO: Update requirements.txt to remove any uncessary import statements

### General Information

Throughout this experiment, there were two methods for capturing Netlog data: manually capturing netlog data through the browser, and using an automated tool to run tests via Puppetteer. For the automated tests, the structure of the data files is set so automation of the analysis can occur smoothly. Most tests used during this research were captured manually, but **if** manually captured tests are used, here are some practices to keep in mind when performing analysis:

1) Structure of Automated Tests
> When tests are run using the automated tool, we can run many Ookla tests in one sitting. They generally follow this structure:

```
test-set/                                  # The overarching instance of when a suite of tests were performed
└── test-batch/                            # A set can be broken down into batches - this is just breaking down the test set to make it more manageable
    └── test-name/                              # This is one speed test on `speedtest.net` - one download test, and one upload ookla-test
        ├── download/
        └── upload/
```

> The `test-name` generally should follow this structure:

```
<server-name>-<flow-type>-<date-and-time>/
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

2) Location of Netlog Files

For an ookla test, the first step is making sure the raw netlog data is in a directory... the necessary files will populate inside this directory. It is recommended that the directory is the name of the test, including the server name/type of test (ex: michwave-multi-1/netlog.json). This already happens if the test was generated using the automated tool.

## Setup

There are two functions of this repo that require installing dependencies:

> Automated Testing Tool

1) Run `npm install` to install all node dependencies

2) From the root of this directory, run `./ookla/test-tool/tool-setup.sh` (or just `./tool-setup.sh` if you are already in that directory) to install some extra packages like wireshark and someta to capture packets and CPU usage during tests

**NOTE:** There are some architecture differences

> Data Processing and Analysis

1) Run `pip3 install -r requirements.txt` to download all python dependancies. This can be run in a virtual environment too.


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

There are two sub-directories. Since these directories are larger, there is a README that descibes them in more detail

> `test-tool/`
This is where the tool for performing many automated tests lives.

>`netlog-filter/`
This holds files for performing the netlog filtering.



#### ``rabbits``

A placeholder folder for the [RABBITs toolkit](https://github.com/CAIDA/rabbits-perf) developed by CAIDA, which was the inital motivation for this project. This toolkit performs a Netlog capture while connecting to one of six possible speed test platforms. This project currently is focused strictly on the behavior of Ookla, but there are future plans for expanding this project to other platforms.

#### ``plot-images``

Also a placeholder folder for keeping images of important plots.

## Note about RABBITS

While these scripts were primarily created on Netlog data captured from the automated testing tool, they should be compatable with any Netlog output generated by RABBITS.




