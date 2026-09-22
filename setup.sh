#!/usr/bin/env bash

# This setup script walks through the necessary dependencies for running the tools in this repo.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"

usage() {
  cat <<'EOF'
Usage: ./setup.sh

This installer guides you through setting up the dependencies needed for this
repository on a fresh Linux machine.
EOF
}

prompt_yes_no() {
  local prompt="$1"
  local answer=""

  read -r -p "$prompt [Y/n]: " answer

  case "${answer:-Y}" in
    [yY]|[yY][eE][sS]|"")
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

run_sudo() {
  if [[ "$(id -u)" -eq 0 ]]; then
    "$@"
  else
    if command -v sudo >/dev/null 2>&1; then
      sudo "$@"
    else
      echo "sudo is required but not available. Please run this script as root or enable sudo." >&2
      exit 1
    fi
  fi
}

ensure_package_manager() {
  if command -v apt-get >/dev/null 2>&1; then
    PACKAGE_MANAGER="apt"
  elif command -v dnf >/dev/null 2>&1; then
    PACKAGE_MANAGER="dnf"
  elif command -v yum >/dev/null 2>&1; then
    PACKAGE_MANAGER="yum"
  else
    echo "Could not detect a supported package manager. Supported options are apt, dnf, and yum." >&2
    exit 1
  fi
}

install_packages() {
  local packages="$1"

  case "$PACKAGE_MANAGER" in
    apt)
      run_sudo apt-get update
      run_sudo apt-get install -y $packages
      ;;
    dnf)
      run_sudo dnf install -y $packages
      ;;
    yum)
      run_sudo yum install -y $packages
      ;;
  esac
}

ensure_python() {
  echo "Required dependency: Python3"

  if command -v python3 >/dev/null 2>&1; then
    echo -e "Python 3 is already available: $(python3 --version 2>&1)\n"
    return 0
  fi

  echo "Python 3 is not installed."
  if prompt_yes_no "Would you like to install Python 3 now?"; then
    install_packages "python3 python3-pip python3-venv"
  else
    echo "Python 3 installation was skipped."
    return 1
  fi

  if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 installation did not succeed." >&2
    return 1
  fi
}

ensure_node() {
  echo "Required dependency: Node.js/npm"

  if command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1; then
    echo -e "Node.js/npm are already available: $(node --version 2>/dev/null) / $(npm --version 2>/dev/null)\n"
    return 0
  fi

  echo "Node.js/npm were not found."
  if prompt_yes_no "Would you like to install Node.js and npm now?"; then
    install_packages "nodejs npm"
  else
    echo "Node.js/npm installation was skipped."
    return 1
  fi

  if ! command -v npm >/dev/null 2>&1; then
    echo "Node.js/npm installation did not succeed." >&2
    return 1
  fi
}

ensure_go() {
  echo "Optional dependency: Go"

  if command -v go >/dev/null 2>&1; then
    echo -e "Go is already available: $(go version 2>/dev/null || true)\n"
    return 0
  fi

  echo "Go is not installed."
  if prompt_yes_no "Would you like to install Go now?"; then
    install_packages "golang-go"
  else
    echo "Go installation was skipped."
    return 1
  fi

  if ! command -v go >/dev/null 2>&1; then
    echo "Go installation did not succeed." >&2
    return 1
  fi
}

ensure_wireshark() {
  echo "Optional dependency: Wireshark"

  if command -v dumpcap >/dev/null 2>&1; then
    echo -e "Wireshark/dumpcap is already available.\n"
    return 0
  fi

  echo "Wireshark is not installed."
  if prompt_yes_no "Would you like to install Wireshark now?"; then
    install_packages "wireshark-common"
  else
    echo "Wireshark installation was skipped."
    return 1
  fi

  if command -v dumpcap >/dev/null 2>&1; then
    if [[ "$(id -u)" -ne 0 ]]; then
      run_sudo usermod -a -G wireshark "$USER" || true
    else
      usermod -a -G wireshark "$USER" || true
    fi
    if [[ -x /usr/bin/dumpcap ]]; then
      run_sudo setcap cap_net_raw,cap_net_admin+eip /usr/bin/dumpcap || true
    fi
  fi
}

setup_python_environment() {
  if [[ ! -f "$REPO_ROOT/requirements.txt" ]]; then
    echo "requirements.txt not found in $REPO_ROOT" >&2
    return 1
  fi

  cd "$REPO_ROOT"
  if [[ -d "$REPO_ROOT/.venv" ]]; then
    echo "A Python virtual environment already exists at $REPO_ROOT/.venv"
  else
    python3 -m venv "$REPO_ROOT/.venv"
  fi

  "$REPO_ROOT/.venv/bin/pip" install -r requirements.txt
}

install_node_dependencies() {
  if [[ ! -f "$REPO_ROOT/package.json" ]]; then
    echo "package.json not found in $REPO_ROOT" >&2
    return 1
  fi

  cd "$REPO_ROOT"
  npm install
}

ensure_someta() {
  echo "Optional dependency: SoMeta"

  if command -v someta >/dev/null 2>&1; then
    echo -e "SoMeta is already installed.\n"
    return 0
  fi

  echo "SoMeta is not installed."
  if ! command -v go >/dev/null 2>&1; then
    echo -e "Go is not available, so SoMeta cannot be installed right now.\n"
    return 0
  fi

  if prompt_yes_no "Would you like to install SoMeta now?"; then
    export GOPATH="$HOME/go"
    export PATH="$PATH:$GOPATH/bin"
    go install github.com/jsommers/someta@latest
  else
    echo "SoMeta installation was skipped."
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
  shift
done

echo "Starting the setup wizard for $REPO_ROOT"
echo "This installer walks through installing all dependencies for this repository."

echo ""

ensure_package_manager

ensure_python || true
ensure_node || true
ensure_go || true
ensure_wireshark || true
ensure_someta || true

echo ""
echo "Setup complete."
if [[ -d "$REPO_ROOT/.venv" ]]; then
  echo "Activate the Python environment with: source $REPO_ROOT/.venv/bin/activate"
fi
if command -v someta >/dev/null 2>&1; then
  echo "SoMeta is available on your PATH."
fi
