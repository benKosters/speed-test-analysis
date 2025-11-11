#Generated with the help of GitHub Copilot
FROM node:18-bullseye

# Set non-interactive mode and pre-configure wireshark
ENV DEBIAN_FRONTEND=noninteractive
RUN echo "wireshark-common wireshark-common/install-setuid boolean true" | debconf-set-selections

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    xvfb \
    wireshark-common \
    tshark \
    awscli \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Set up packet capture permissions
RUN setcap cap_net_raw,cap_net_admin+eip /usr/bin/dumpcap

# Create app directory
WORKDIR /app

# Copy application files
COPY . .

# Make scripts executable
RUN chmod +x *.sh