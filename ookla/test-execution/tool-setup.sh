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

echo "Installing Go"

echo "Checking for Go installation..."
if ! command -v go >/dev/null 2>&1; then
    echo "Go not found. Installing Go..."
    if command -v apt-get >/dev/null 2>&1; then
        # For Debian/Ubuntu/Raspberry Pi OS
        sudo apt-get install -y golang-go
    fi

    # Set up Go environment variables if they don't exist
    if ! grep -q "GOPATH" ~/.bashrc; then
        echo 'export GOPATH=$HOME/go' >> ~/.bashrc
        echo 'export PATH=$PATH:$GOPATH/bin' >> ~/.bashrc
        export GOPATH=$HOME/go
        export PATH=$PATH:$GOPATH/bin
    fi
else
    echo "Go is already installed ($(go version))"
fi

# Add Go to PATH permanently
if ! grep -q "/usr/local/go/bin" ~/.bashrc; then
    echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc
    echo 'export GOPATH=$HOME/go' >> ~/.bashrc
    echo 'export PATH=$PATH:$GOPATH/bin' >> ~/.bashrc
fi

echo "Installing someta..."

# Install someta
if ! command -v someta >/dev/null 2>&1; then
    go install github.com/jsommers/someta@latest
else
    echo "someta is already installed"
fi

echo "Setup complete. Use sudo reboot to apply group changes."
echo "After reboot, run 'source ~/.bashrc' to update PATH in your current shell."