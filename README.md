## Speed Test Analysis

This repo is organized into the following sections:

1) url_filter.js  --> collects the relevant URLs from raw Netlog data
2) manual_netlog.js --> filters out the important events for finding throughput and latency for a manually collected test from Ookla only (A separate script is required for a CARROT test)
3) visualizations/ --> contains the following:
    - calculate_plot_throughput.py --> main program to run analysis on raw data after it has been filtered from the raw Netlog data
    - plotting_functions.py --> modularized functions for different variations of graphs
    - helper_functions.py --> a variety of helper functions used to collect information about filtered data
    - throughput_calculation_functions.py --> functions used for calculating throughput (a few versions were used for experimentation)
4) proces_netlog_data.sh --> a bash script to populate a directory the necessary files after raw netlog data is collected


The visualization files can be used for BOTH a Ookla test with manually collected netlog data and a CARROT test.
To run the visualization script, use the following command from the root of this directory:
```
python3 visualizations/calculate_throughput_with_plot.py path/to/directory/containing/filtered/data --save
```
The "save" flag is optional, and will create a subdirectory called "plot_images/" inside the directory where the filtered data is.

### CARROT
For a CARROT test, the visualization script can be run as long as the filtered data such as byte_time_list.jso/current_position_lit.json, socket_ids.txt, etc. are available (Note: the old version of the CARROT analysis may not have save the socket ids saved, so be sure to populate this file for old tests).

### Ookla
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
