"""
This script is a concept, needs to be implemented. This is for the next person working on this project to look at :)
"""

import argparse
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


parser = argparse.ArugmentParser(description = 'Run a comparative analysis across tests')
parser.add_argument('data_path', type=str, help='Path to CSV data')
parser.add_argument('output_dir', type= str, help = "Output directory of any generated plots/other files")
parser.add_argument('--save', action='store_true', help='Save plots to <output_dir> directory')

args = parser.parse_args()
data = pd.read_csv(args.data_path)

