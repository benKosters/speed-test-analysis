#!/usr/bin/env python3
"""
Speed Test Visualization GUI Launcher

This script launches the Speed Test Visualization GUI.
"""

import os
import sys
import tkinter as tk

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the GUI application from the visualization_app package
from visualization_app import SpeedTestVisualizerApp

def main():
    """Main function to launch the GUI application"""
    # Create the root window
    root = tk.Tk()

    # Create the application
    app = SpeedTestVisualizerApp(root)

    # Start the main loop
    root.mainloop()

if __name__ == "__main__":
    main()
