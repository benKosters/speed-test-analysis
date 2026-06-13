## Plot Directory

#### plot_driver.py

This is the main file for generating throughput related plots.


#### plot_bar_bytecount.py
![Barchart](visualizations/readme-examples/bytecount_barchart_example.png)

This plot is used for plotting

When called directly from the command line:
`python3 plot_bar_bytecount.py /mnt/d/usa-server-tests/usa_ookla_tests_batch1_2026-02-05_2346/michwave-multi-2026-02-05_2258/download/byte_count.json `

When called in `plot_driver.py`:

`plots.create_bytecount_bar_chart(plot_data['byte_count'], source_times=plot_data['source_times'])`

TODO: The gantt chart is not part of the plot when it is generated via the command line. Fix this.

####

