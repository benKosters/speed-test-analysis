#!/bin/bash

BASE_DIR="$(dirname "$0")"
COMMANDS_FILE="$BASE_DIR/test-configurations.txt"
LOG_FILE="$BASE_DIR/driver.log"

echo "[$(date)] Starting driver..." | tee -a "$LOG_FILE"

# Loop through each command in the commands file
while IFS= read -r CMD; do
    if [ -n "$CMD" ]; then
        echo "[$(date)] Running: $CMD" | tee -a "$LOG_FILE"
        eval "$CMD" >> "$LOG_FILE" 2>&1
        echo "[$(date)] Finished: $CMD" | tee -a "$LOG_FILE"

        #sleep 200
    fi
done < "$COMMANDS_FILE"

echo "[$(date)] All commands finished." | tee -a "$LOG_FILE"
