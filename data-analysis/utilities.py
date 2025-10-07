import os
import json

def load_json(filepath):
    """
    Load the data we need, stored in JSON format.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
    with open(filepath, 'r') as f:
        return json.load(f)
