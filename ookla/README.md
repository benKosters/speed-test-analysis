**Ookla Conventional Test Information**

*This sub-directory contains **both** the tool for performing the Ookla Conventional Test, as well as the script for filtering out the relevant netlog events/data. This is different from the RABBITS directory, which **only** contains the filtering scripts.*


1) test-execution

* This directory contains the scripts for running a speed test against the Ookla server and collecting the necessary raw data (netlog, pcap, metadata).

2) data-extraction

* This directory contains scripts for processing the raw network data into structured data that can be used for analysis. Currently we are only examining netlog data but will expand the extraction process.