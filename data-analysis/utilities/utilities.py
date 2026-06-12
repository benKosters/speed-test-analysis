import os
import json
import sys

def load_json(filepath):
    """
    Load the data we need, stored in JSON format.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
    with open(filepath, 'r') as f:
        return json.load(f)

def save_json(data, filepath):
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)


def check_and_load_files(required_files, optional_files=None):
    # Check required files
    for file_path in required_files:
        print(f"Checking: {file_path}")
        if not os.path.exists(file_path):
            print(f"    ERROR: File not found - {file_path}\n")
        else:
            print(f"    File exists: {file_path}\n")

    if optional_files is None:
        optional_files = []
    else:
        print("Checking optional files:")
        for file_path in optional_files:
            print(f"Checking: {file_path}")
            if not os.path.exists(file_path):
                print(f"    Optional file not found (this is OK if not needed) - {file_path}\n")
            else:
                print(f"    Optional file exists: {file_path}\n")
    return

