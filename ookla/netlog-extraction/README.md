**Ookla: Processing of Manual Test Data**

To verify RABBITS, we performed a manual capture of Netlog data while running an Ookla speed test, just like the typical end user would. Since there are some differences in how netlog data is processed between RABBITS and a manual test, we have separated the data extraction/processing scripts.

Key differences in the Netlog data from a manual test and RABBITS:
* RABBITS data is only upload or download, but a manual test contains both
* For RABBITS tests, the URLS are already provided. Manual tests must collect URLS first