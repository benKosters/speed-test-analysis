"""
This module contains the main application class for the GUI.
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from .data_loader import DataLoader
from .visualizations import Visualizations as VisualizationsPackage
from .visualizations.registry import get_visualization_types

class SpeedTestVisualizerApp:
    """Main application class for the Speed Test Visualizer GUI"""

    def __init__(self, root):
        """Constructor to initialize the application"""
        self.root = root
        self.root.title("Speed Test Visualization")
        self.root.geometry("1200x800+500+500") #1200x800 window at (100,50)

        # Application state
        self.loaded_tests = {}  # Dictionary of loaded tests: {test_name: test_data}
        self.current_figure = None
        self.current_canvas = None

        # Initialize components
        self.data_loader = DataLoader()
        self.visualizations = get_visualization_types()

        # Create main layout
        self.create_layout()

    def create_layout(self):
        """Defines the main layout of the GUI"""
        # Create main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create left panel for controlling the application
        left_panel = ttk.Frame(main_frame, width=300)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        # Create right panel for visualization
        self.right_panel = ttk.Frame(main_frame)
        self.right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Test selection section
        test_frame = ttk.LabelFrame(left_panel, text="Test Selection")
        test_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(test_frame, text="Load a Single Test",
                   command=self.load_test_directory).pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(test_frame, text="Load a Multiple of Tests",
                   command=self.load_multiple_tests).pack(fill=tk.X, padx=5, pady=5)

        # Create a frame for the test listbox and scrollbar
        test_list_frame = ttk.Frame(test_frame)
        test_list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Add scrollbar for test listbox
        test_scrollbar = ttk.Scrollbar(test_list_frame)
        test_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Create test listbox with multiple selection enabled
        self.test_listbox = tk.Listbox(test_list_frame, selectmode=tk.MULTIPLE,
                                       yscrollcommand=test_scrollbar.set,
                                       selectbackground="#90EE90",  # Light green
                                       selectforeground="black")  # Black text for contrast
        self.test_listbox.pack(fill=tk.BOTH, expand=True)
        test_scrollbar.config(command=self.test_listbox.yview)

        # Analysis Type selection section
        analysis_frame = ttk.LabelFrame(left_panel, text="Select Analysis Type")
        analysis_frame.pack(fill=tk.X, padx=5, pady=5)

        self.analysis_type_var = tk.StringVar(value="Single Test Analysis")
        self.analysis_type_combobox = ttk.Combobox(analysis_frame, textvariable=self.analysis_type_var,
                                                  values=["Single Test Analysis", "Multiple Tests Analysis", "Test Metadata Analysis"])
        self.analysis_type_combobox.pack(fill=tk.X, padx=5, pady=5)
        self.analysis_type_combobox.bind("<<ComboboxSelected>>", self.on_analysis_type_selected)

        # Visualization selection section
        viz_frame = ttk.LabelFrame(left_panel, text="Visualization Type")
        viz_frame.pack(fill=tk.X, padx=5, pady=5)

        self.viz_type_var = tk.StringVar()
        self.viz_type_combobox = ttk.Combobox(viz_frame, textvariable=self.viz_type_var)
        self.viz_type_combobox.pack(fill=tk.X, padx=5, pady=5)
        self.viz_type_combobox.bind("<<ComboboxSelected>>", self.on_viz_type_selected)

        # Parameters section - will be dynamically populated
        self.params_frame = ttk.LabelFrame(left_panel, text="Parameters")
        self.params_frame.pack(fill=tk.X, padx=5, pady=5)

        # Action buttons
        action_frame = ttk.Frame(left_panel)
        action_frame.pack(fill=tk.X, padx=5, pady=15)

        ttk.Button(action_frame, text="Generate Visualization",
                   command=self.generate_visualization).pack(side=tk.LEFT, padx=5)

        ttk.Button(action_frame, text="Save Plot",
                   command=self.save_current_plot).pack(side=tk.RIGHT, padx=5)

        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Initialize with default selection
        self.analysis_type_combobox.current(0)
        self.on_analysis_type_selected(None)

    def on_analysis_type_selected(self, event):
        """Handle analysis type selection"""
        analysis_type = self.analysis_type_var.get()

        # Map the user-friendly names to category values
        category_map = {
            "Single Test Analysis": "single_test",
            "Multiple Tests Analysis": "comparison",
            "Test Metadata Analysis": "metadata"
        }

        selected_category = category_map.get(analysis_type, "single_test")

        # Filter visualizations by the selected category
        filtered_viz = {}
        for viz_name, viz_info in self.visualizations.items():
            if viz_info.get("category", "") == selected_category:
                filtered_viz[viz_name] = viz_info

        # Update the visualization type combobox
        self.viz_type_combobox['values'] = list(filtered_viz.keys())

        # Set first item as selected if available
        if self.viz_type_combobox['values']:
            self.viz_type_combobox.current(0)
            self.viz_type_var.set(self.viz_type_combobox['values'][0])
            self.on_viz_type_selected(None)
        else:
            self.viz_type_var.set("")
            self.on_viz_type_selected(None)

        # Show a hint about how many tests to select based on the visualization type
        viz_type = self.viz_type_var.get()
        if viz_type and viz_type in self.visualizations:
            min_tests = self.visualizations[viz_type]["min_tests"]
            max_tests = self.visualizations[viz_type]["max_tests"]
            if min_tests > 1:
                self.status_var.set(f"Please select {min_tests} to {max_tests} tests for comparison")
            elif selected_category == "metadata":
                self.status_var.set(f"Metadata analysis requires {min_tests} to {max_tests} tests")
            else:
                self.status_var.set("Ready")

    def on_viz_type_selected(self, event):
        """Handle visualization type selection"""
        # Clear existing parameters
        for widget in self.params_frame.winfo_children():
            widget.destroy()

        viz_type = self.viz_type_var.get()
        if not viz_type or viz_type not in self.visualizations:
            return

        # Add description
        description = self.visualizations[viz_type]["description"]
        ttk.Label(self.params_frame, text=description, wraplength=280).pack(padx=5, pady=5)

        # Add test requirements
        min_tests = self.visualizations[viz_type]["min_tests"]
        max_tests = self.visualizations[viz_type]["max_tests"]
        test_req = f"Visualization Usage: {min_tests}"
        if min_tests != max_tests:
            test_req += f" to {max_tests}"
        test_req += " test(s)"
        ttk.Label(self.params_frame, text=test_req).pack(padx=5, pady=5)

        # Add parameter controls
        self.param_vars = {}
        params = self.visualizations[viz_type].get("params", {})
        for param_name, param_info in params.items():
            param_frame = ttk.Frame(self.params_frame)
            param_frame.pack(fill=tk.X, padx=5, pady=2)

            ttk.Label(param_frame, text=param_info["label"]).pack(side=tk.LEFT)

            if param_info["type"] == "numeric":
                var = tk.DoubleVar(value=param_info["default"])
                ttk.Entry(param_frame, textvariable=var, width=10).pack(side=tk.RIGHT)
                self.param_vars[param_name] = var
            elif param_info["type"] == "boolean":
                var = tk.BooleanVar(value=param_info["default"])
                ttk.Checkbutton(param_frame, variable=var).pack(side=tk.RIGHT)
                self.param_vars[param_name] = var
            elif param_info["type"] == "choice":
                var = tk.StringVar(value=param_info["default"])
                ttk.Combobox(param_frame, textvariable=var,
                            values=param_info["choices"]).pack(side=tk.RIGHT)
                self.param_vars[param_name] = var

    def load_test_directory(self):
        """Load a single test directory"""
        directory = filedialog.askdirectory(
            title="Select Test Directory",
            initialdir=os.getcwd()
        )

        if directory:
            self.status_var.set(f"Loading test from {directory}...")
            self.root.update()

            try:
                if self.data_loader.is_valid_test_directory(directory):
                    test_name = os.path.basename(directory)
                    test_data = self.data_loader.load_test_data(directory)

                    self.loaded_tests[test_name] = {
                        "path": directory,
                        "data": test_data
                    }

                    # Update the listbox
                    self.update_test_listbox()
                    self.status_var.set(f"Loaded test: {test_name}")
                else:
                    messagebox.showinfo("Invalid Test Directory",
                                       "The selected directory does not appear to be a valid test directory.")
                    self.status_var.set("Error loading test")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load test: {str(e)}")
                self.status_var.set("Error loading test")

    def load_multiple_tests(self):
        """Load multiple test directories"""
        parent_dir = filedialog.askdirectory(
            title="Select Parent Directory Containing Multiple Tests",
            initialdir=os.getcwd()
        )

        if parent_dir:
            self.status_var.set(f"Scanning for tests in {parent_dir}...")
            self.root.update()

            try:
                # Look for subdirectories that contain required test files
                test_dirs = self.data_loader.scan_for_tests(parent_dir)

                if test_dirs:
                    for test_name, test_dir in test_dirs.items():
                        test_data = self.data_loader.load_test_data(test_dir)
                        self.loaded_tests[test_name] = {
                            "path": test_dir,
                            "data": test_data
                        }

                    # Update the listbox
                    self.update_test_listbox()
                    self.status_var.set(f"Loaded {len(test_dirs)} tests")
                else:
                    messagebox.showinfo("No Tests Found",
                                       "No valid test directories were found. Each test directory should contain byte_time_list.json or current_position_list.json files.")
                    self.status_var.set("No tests found")
            except Exception as e:
                messagebox.showerror("Error", f"Error scanning for tests: {str(e)}")
                self.status_var.set("Error loading tests")

    def update_test_listbox(self):
        """Update the test listbox with loaded tests"""
        self.test_listbox.delete(0, tk.END)
        for test_name in sorted(self.loaded_tests.keys()):
            self.test_listbox.insert(tk.END, test_name)

    def get_selected_tests(self):
        """Get the selected tests from the listbox"""
        selected_indices = self.test_listbox.curselection()
        selected_tests = {}

        for index in selected_indices:
            test_name = self.test_listbox.get(index)
            selected_tests[test_name] = self.loaded_tests[test_name]

        return selected_tests

    def generate_visualization(self):
        """Generate the selected visualization"""
        viz_type = self.viz_type_var.get()
        if not viz_type:
            messagebox.showinfo("Info", "Please select a visualization type")
            return

        selected_tests = self.get_selected_tests()
        if not selected_tests:
            messagebox.showinfo("Info", "Please select at least one test")
            return

        # Check if number of selected tests matches requirements
        min_tests = self.visualizations[viz_type]["min_tests"]
        max_tests = self.visualizations[viz_type]["max_tests"]

        if len(selected_tests) < min_tests:
            messagebox.showinfo("Info", f"This visualization requires at least {min_tests} tests")
            return

        if len(selected_tests) > max_tests:
            messagebox.showinfo("Info", f"This visualization supports at most {max_tests} tests")
            return

        # Get the category to provide better feedback
        category = self.visualizations[viz_type].get("category", "")
        if category == "comparison" and len(selected_tests) < 2:
            messagebox.showinfo("Info", "Comparison visualizations require at least 2 tests")
            return
        elif category == "metadata" and len(selected_tests) < 3:
            messagebox.showinfo("Info", "Metadata visualizations typically require at least 3 tests")
            return

        # Get parameter values
        params = {}
        for param_name, var in self.param_vars.items():
            params[param_name] = var.get()

        # Set status
        self.status_var.set(f"Generating {viz_type}...")
        self.root.update()

        try:
            # Get the visualization function
            viz_function_name = self.visualizations[viz_type]["function"]
            viz_function = getattr(VisualizationsPackage, viz_function_name)

            # Call the visualization function
            fig = viz_function(selected_tests, params)

            if fig:
                self.display_figure(fig)
                self.status_var.set(f"Generated {viz_type}")
            else:
                messagebox.showinfo("Info", "No data available for this visualization")
                self.status_var.set("No data available")
        except Exception as e:
            messagebox.showerror("Error", f"Error generating visualization: {str(e)}")
            self.status_var.set("Error generating visualization")

    def clear_visualization_area(self):
        """Clear the visualization area"""
        # Clear the right panel
        for widget in self.right_panel.winfo_children():
            widget.destroy()

        # Reset the current figure and canvas
        self.current_figure = None
        self.current_canvas = None

    def display_figure(self, fig):
        """Display a matplotlib figure in the right panel"""
        # Clear any existing figure
        self.clear_visualization_area()

        self.current_figure = fig

        # Create a canvas to display the figure
        canvas = FigureCanvasTkAgg(fig, master=self.right_panel)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Add navigation toolbar
        toolbar_frame = ttk.Frame(self.right_panel)
        toolbar_frame.pack(fill=tk.X)
        toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
        toolbar.update()

        # Store the canvas for later reference
        self.current_canvas = canvas

    def save_current_plot(self):
        """Save the current plot to a file"""
        if self.current_figure is None:
            messagebox.showinfo("Info", "No visualization to save")
            return

        try:
            # Define the "plot_images" subdirectory in the directory of the first selected test
            selected_tests = self.get_selected_tests()
            if not selected_tests:
                messagebox.showinfo("Info", "No test selected to determine save directory")
                return

            # Get the directory of the first selected test
            first_test = next(iter(selected_tests.values()))
            directory = first_test["path"]

            plot_images_dir = os.path.join(directory, "plot_images")
            if not os.path.exists(plot_images_dir):
                os.makedirs(plot_images_dir)

            # Generate a default filename using a timestamp
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"plot_{timestamp}.png"
            save_path = os.path.join(plot_images_dir, default_filename)

            # Save the plot as a PNG in the "plot_images" directory
            self.current_figure.savefig(save_path, dpi=300, bbox_inches='tight')

            # Show a popup with the absolute path
            messagebox.showinfo("Info", f"Plot saved successfully at: {os.path.abspath(save_path)}")
            self.status_var.set(f"Saved plot to {save_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Error saving plot: {str(e)}")
            self.status_var.set("Error saving plot")
