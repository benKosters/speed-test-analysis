import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

"""
Python version of scripts used to capture Ookla test data.
Author: Ben Kosters, with assistance from AI
Date 10/3/2026

"""

RESULTS_DIR = Path(__file__).resolve().parent / "ookla-test-results"
BROWSER_SCRIPT = Path(__file__).resolve().parent / "launch-browser.js"
DEFAULT_BATCH_CONFIG = Path(__file__).resolve().parent / "batch-configurations.json"

#TODO: implement different orders for running many tests
ORDER_TYPES = ("alternate", "sequential")

def log(message):
    # Instead of printing, include a timestamp to track how long certain actions take
    print(f"[{datetime.now().strftime('%Y/%m/%d %H:%M:%S')}] {message}")

def check_permissions(pcap=False, interface="eth0"):
    # Confirm RESULTS_DIR exists and is writable, and (when pcap is set) that dumpcap can start
    if not RESULTS_DIR.is_dir():
        log(f"Error: {RESULTS_DIR} does not exist; create it before running.")
        return False
    if not os.access(RESULTS_DIR, os.R_OK | os.W_OK | os.X_OK):
        log(f"Error: Cannot read/write {RESULTS_DIR}")
        return False

    if pcap:
        if shutil.which("dumpcap") is None:
            log("Error: dumpcap not found; install wireshark-common.")
            return False

        # `dumpcap -D` only lists interfaces the current user is allowed to capture on
        result = subprocess.run(["dumpcap", "-D"], capture_output=True, text=True)
        if not any(f". {interface}" in line for line in result.stdout.splitlines()):
            log(f"Error: No permission to capture on '{interface}'; run with sudo or join the wireshark group.")
            return False

    return True

def parse_args(argv):
    # parse command line args for single or batch tests
    parser = argparse.ArgumentParser(description="Run a single Ookla speed test, or a batch of tests from a config file.")
    # Single-test options default to None so --batch can detect conflicting use
    parser.add_argument("-s", "--server", help="Server name to test against (default: Michwave)")
    parser.add_argument("-c", "--connection", choices=["single", "multi"], help="Connection type (default: multi)")
    parser.add_argument("-p", "--pcap", action="store_true", help="Enable packet capture during test")
    parser.add_argument("-i", "--interface", help="Network interface for packet capture (default: eth0)")
    parser.add_argument("-m", "--cpu-monitor", action="store_true", help="Enable CPU monitoring with someta")
    parser.add_argument("-b", "--batch", nargs="?", const=DEFAULT_BATCH_CONFIG, type=Path, metavar="CONFIG",
                        help=f"Run multiple tests using a JSON config file (default: {DEFAULT_BATCH_CONFIG.name})")
    args = parser.parse_args(argv)

    if args.batch:
        given = [flag for flag, used in (("--server", args.server), ("--connection", args.connection),
                                         ("--interface", args.interface), ("--pcap", args.pcap),
                                         ("--cpu-monitor", args.cpu_monitor)) if used]
        if given:
            parser.error(f"--batch takes these settings from the config file; remove: {' '.join(given)}")
        try:
            vars(args).update(load_batch_config(args.batch))
        except ValueError as e:
            parser.error(str(e))
    else:
        args.server = args.server or "Merit"
        args.connection = args.connection or "multi"
        args.interface = args.interface or "eth0"
    return args

def create_output_dir(server, connection):
    # Builds <server>-<connection>-<timestamp> under RESULTS_DIR and creates it
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    server_formatted = server.lower().replace(" ", "_")
    path = RESULTS_DIR / f"{server_formatted}-{connection}-{timestamp}"
    # Back-to-back batch tests can land in the same minute; never reuse an existing results directory
    suffix = 2
    while path.exists():
        path = RESULTS_DIR / f"{server_formatted}-{connection}-{timestamp}-{suffix}"
        suffix += 1
    path.mkdir(parents=True)

    # Under sudo, hand the directory back to the invoking user so the pcap can be written
    sudo_user = os.environ.get("SUDO_USER")
    if os.geteuid() == 0 and sudo_user:
        shutil.chown(path, user=sudo_user, group=sudo_user)
    return path

def start_pcap(interface, file):
    # Returns the dumpcap process, or None if it failed to start
    # -q stops dumpcap from writing a running packet count to the unread stderr pipe
    process = subprocess.Popen(["dumpcap", "-q", "-i", interface, "-w", str(file)],
                               stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)

    # dumpcap exits immediately on permission or interface errors
    time.sleep(2)
    if process.poll() is not None:
        log(f"Warning: dumpcap failed to start: {process.stderr.read().strip()}")
        return None

    log(f"dumpcap started on {interface} with PID {process.pid}")
    return process

def stop_pcap(process, file):
    if process is None:
        return
    file = Path(file)

    if process.poll() is not None:
        log("Warning: dumpcap was not running")
    else:
        # SIGTERM lets dumpcap flush and close the pcap cleanly
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    if file.exists():
        log(f"Packet capture saved to {file} ({file.stat().st_size / 1e6:.1f} MB)")
    else:
        log("Warning: packet capture file was not created")

def parse_someta_output(out_dir, basename="cpu_metrics"):
    # Someta appends a timestamp to the basename; rename to a stable name and return its contents.
    # basename must match the -f prefix passed to someta; filter-cpu-data.js expects cpu_metrics.json.
    out_dir = Path(out_dir)
    matches = sorted(out_dir.glob(f"{basename}_*.json"), key=lambda p: p.stat().st_mtime)
    if not matches:
        log(f"Warning: no someta output found in {out_dir}")
        return None

    final_path = out_dir / f"{basename}.json"
    matches[-1].replace(final_path)
    log(f"Renamed someta output to {final_path.name}")

    #TODO: CPU data is being captured, but is not being analyzed. This needs to be analyzed.

def run_ookla_test(server, connection, out_dir, cpu_monitor=False):
    # Runs launch-browser.js exits 0 even when the test fails, so also check for speedtest_result.json.
    cmd = ["node", str(BROWSER_SCRIPT), "-s", server, "-c", connection, "-o", str(out_dir)]

    if cpu_monitor:
        # someta takes the wrapped command as a single string
        cmd = ["someta", "-M", "cpu", "-f", str(Path(out_dir) / "cpu_metrics"), "-c", shlex.join(cmd)]

    return subprocess.run(cmd).returncode

def run_single_test(args):
    # Returns True if the browser exited cleanly and wrote speedtest_result.json. This function starts the pcap, launches the test, then stops the pcap
    out_dir = create_output_dir(args.server, args.connection)
    pcap_file = out_dir / "packet_capture.pcap"

    pcap_process = start_pcap(args.interface, pcap_file) if args.pcap else None
    try:
        exit_code = run_ookla_test(args.server, args.connection, out_dir, args.cpu_monitor)
    finally:
        stop_pcap(pcap_process, pcap_file)

    if args.cpu_monitor:
        parse_someta_output(out_dir)

    success = exit_code == 0 and (out_dir / "speedtest_result.json").exists()
    log(f"Test {'completed' if success else 'FAILED'}; results in {out_dir}")
    return success


# -----------------------Functions required for performing batch tests -----------------------------

def load_batch_config(path):
    # Returns the batch settings as a dict; raises ValueError with a readable message if the file is invalid
    try:
        with open(path) as f:
            config = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise ValueError(f"cannot read batch config {path}: {e}")

    if not isinstance(config, dict):
        raise ValueError(f"{path} must contain a JSON object")
    missing = {"servers", "connections", "order"} - config.keys()
    if missing:
        raise ValueError(f"{path} is missing: {', '.join(sorted(missing))}")
    if not config["servers"] or not isinstance(config["servers"], list):
        raise ValueError("'servers' must be a non-empty list")
    if not config["connections"] or not set(config["connections"]) <= {"single", "multi"}:
        raise ValueError("'connections' must be a non-empty list of 'single' and/or 'multi'")
    if config["order"] not in ORDER_TYPES:
        raise ValueError(f"'order' must be one of: {', '.join(ORDER_TYPES)}")
    tests_per_connection = config.get("tests_per_connection", 1)
    if not isinstance(tests_per_connection, int) or tests_per_connection < 1:
        raise ValueError("'tests_per_connection' must be a positive integer")

    return {
        "servers": config["servers"],
        "connections": config["connections"],
        "order": config["order"],
        "tests_per_connection": tests_per_connection,
        "pcap": bool(config.get("pcap", False)),
        "cpu_monitor": bool(config.get("cpu_monitor", False)),
        "interface": config.get("interface", "eth0"),
    }

def confirm_batch(config_json):
    print("Batch test parameters:")
    print(f"Config:      {config_json}")
    print(f"Servers:     {', '.join(config_json['servers'])}")
    print(f"Connections: {', '.join(config_json['connections'])}")
    print(f"Order:       {config_json['order']}")
    print(f"Tests per connection type: {config_json['tests_per_connection']}")
    print(f"Packet cap enabled:  {config_json['pcap']}" + (f" on {config_json['interface']}" if config_json['pcap'] else ""))
    print(f"CPU monitor enabled : {config_json['cpu_monitor']}")
    print(f"Batch size:      {config_json['batch_size']}")
    print(f" Wait period between batches: {config_json['wait_between_batches_seconds']}")
    print("Upload results to S3 bucket: " + str(config_json.get("upload_to_s3", False)))
    print("Filter netlog: " + str(config_json.get("process_netlog_before_upload", False)))
    print(f"Batch name: {config_json['batch_name']}")


    return input("If these parameters are correct, confirm to proceed [y/N]: ").strip().lower() in ("y", "yes")

def set_test_order(batch_config):
    # Returns the (server, connection) pairs in the order they should run
    servers = batch_config["servers"]
    connections = batch_config["connections"]
    count = batch_config["tests_per_connection"]

    if batch_config["order"] == "alternate":
        # One test per connection on each server, then go back and repeat
        return [(s, c) for _ in range(count) for s in servers for c in connections]
    if batch_config["order"] == "sequential":
        # All tests of one connection type on a server, then the next connection type, then the next server
        return [(s, c) for s in servers for c in connections for _ in range(count)]
    raise ValueError(f"unknown order '{batch_config['order']}'")

def run_batch(batch_config):
    # Returns True if every test succeeded; a failed test is recorded and the batch continues
    tests = set_test_order(batch_config)
    failed = []

    for number, (server, connection) in enumerate(tests, 1):
        log(f"Starting test {number}/{len(tests)}: {server}, {connection} flow")
        test_args = argparse.Namespace(server=server, connection=connection,
                                       pcap=batch_config["pcap"], interface=batch_config["interface"],
                                       cpu_monitor=batch_config["cpu_monitor"])
        if not run_single_test(test_args):
            failed.append((number, server, connection))

    log(f"Batch finished: {len(tests) - len(failed)}/{len(tests)} tests succeeded")
    for number, server, connection in failed:
        log(f"  Failed: test {number} ({server}, {connection} flow)")
    return not failed

def upload_to_s3():
    #upload results to s3 bucket
    pass

#------------------------------End section on functions required for running set of many tests ---------------

def run_session(argv=None):
    # This is the main driver for running tests. Parse the CLI, check permissions, then run single or batch tests
    args = parse_args(argv)

    if check_permissions(args.pcap, args.interface):
        log("Permissions are correct, proceeding")
    else:
        log("There is an issue with permissions, exiting")
        sys.exit(1)

    # Run a single test
    if not args.batch:
        run_single_test(args)
    # Run a batch of many tests at one time
    else:
        config = vars(args)
        if confirm_batch(config) == False:
            log("Stopping batch run, configurations are incorrect")
            sys.exit(0)
        else:
            log("Running many tests as a batch are not yet implemented")
            #TODO: Complete code here to perform batches of Ookla tests

run_session()




