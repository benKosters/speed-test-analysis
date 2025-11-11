#!/bin/bash
# filepath: run-tool-setup.sh
# Run this once during initial setup

echo "Setting up system for packet capture..."

# Install wireshark (which includes dumpcap)
if command -v apt-get >/dev/null 2>&1; then # >/dev/null 2>&1 to hide output
    sudo apt-get update
    sudo apt-get install -y wireshark-common
elif command -v yum >/dev/null 2>&1; then
    sudo yum install -y wireshark
fi

# Add current user to wireshark group
sudo usermod -a -G wireshark $USER

# Set capabilities on dumpcap (allows non-root packet capture)
sudo setcap cap_net_raw,cap_net_admin+eip /usr/bin/dumpcap

echo "Setup complete. Please log out and log back in for group changes to take effect." #sudo reboot
echo "After logging back in, you can run ./execute-ookla-test.sh without sudo."