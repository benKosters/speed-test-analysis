l# Automated Ookla Speed Test Tool

This tool runs Ookla speed tests using a headless browser and can collect network data via a Nelog capture. Pcap files can optionally be captured as well.

## Setup

• Run `./run-tool-setup.sh` once to configure packet capture permissions

• Create `.env` file with AWS credentials (for batch uploads):
  ```
  AWS_ACCESS_KEY_ID=your_key
  AWS_SECRET_ACCESS_KEY=your_secret
  AWS_DEFAULT_REGION=region
  S3_BUCKET_NAME=your_bucket
  ```
• **Note** If this tool is being used on a raspberry pi, additional steps must be taken:

  In the CLI, use this command:
  `sudo apt install chromium-browser`

• In ookla-test.js, line 53-55, update the executablePath to point to the chrome brower executable


## Single Test

• Use `./execute-ookla-test.sh` to run one test

• Example: `./execute-ookla-test.sh -s spacelink -c multi -p -i eth0`

• Use `./execute-ookla-test.sh --help` for all configuration options

## Multiple Tests

• Use `./run-many-tests.sh` to run many tests automatically

• Configure tests in `test-configurations.txt` (one test per line)

• Example line: `./execute-ookla-test.sh -s spacelink -c multi -p -i eth0`

• Use `./run-many-tests.sh --help` for all configuration options

### Batch Processing

• Tests run in batches to manage disk space on the test device (ex: raspberry pi)

• After each batch: compresses results → uploads to S3 → deletes local files

• Default: 20 tests per batch, 120 second cooldown

• Customize: `./run-many-tests.sh -b 10 -w 60`

## Output

• Individual tests: saved in `ookla-test-results/` subdirectories

• Batch uploads: compressed archives in S3 bucket
