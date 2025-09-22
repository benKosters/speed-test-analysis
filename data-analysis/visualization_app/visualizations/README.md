# Speed Test Visualizations Package

This package contains modular visualization components for analyzing network speed test data and is organized in this way to make adding visualizations easier.

## Package Structure

```
visualizations/
├── __init__.py                     # Main interface and unified access point
├── registry.py                     # Registry of all available visualizations
├── test_visualizations.py          # Single test visualizations
├── comparison_visualizations.py    # Multi-test comparison visualizations
└── metadata_visualizations.py      # Test metadata analysis visualizations
```

## How to Add a New Visualization

Process for adding a new visualization to the package as we expand our analysis capabilities:

### Step 1: Decide Which Module to Use

Choose the appropriate module based on your visualization type:

- `test_visualizations.py` - For visualizations that analyze a single test (e.g., throughput analysis)
- `comparison_visualizations.py` - For visualizations that compare multiple tests
- `metadata_visualizations.py` - For visualizations that analyze test metadata
- Or create a new module if your visualization fits a new category

### Step 2: Write Your Visualization Function

Add your function to the appropriate module. The function should:

1. Accept `selected_tests` (a dictionary of test data) and `params` (user-defined parameters)
2. Return a matplotlib `Figure` object

Example structure:

```python
def plot_your_new_visualization(selected_tests, params):
    """
    Description of what your visualization shows

    Args:
        selected_tests (dict): Dictionary of test data in the format {test_name: test_info}
            where test_info is a dict with 'data' and 'path' keys
        params (dict): Dictionary of user-defined parameters from the GUI

    Returns:
        matplotlib.figure.Figure: The figure object to display, or None if visualization cannot be generated
    """
    # Check if we have enough tests
    if len(selected_tests) < 1:  # Adjust minimum required tests
        return None

    # Extract parameters with defaults
    param1 = params.get("param1", default_value)

    # Create a figure
    fig = Figure(figsize=(12, 8))
    ax = fig.add_subplot(1, 1, 1)

    # Process test data and generate the visualization
    # ...

    # Configure the plot (labels, titles, etc.)
    ax.set_xlabel('X Label')
    ax.set_ylabel('Y Label')
    ax.set_title('Visualization Title')

    return fig
```

### Step 3: Register Your Visualization

Add your visualization to the registry in `registry.py`:

```python
"Your Visualization Name": {
    "function": "plot_your_new_visualization",  # Must match your function name
    "description": "Concise description of what the visualization shows",
    "params": {
        "param1": {
            "type": "numeric",     # Can be "numeric", "boolean", or "choice"
            "default": 10,         # Default value
            "label": "Parameter 1" # Label shown in the GUI
        },
        "param2": {
            "type": "boolean",
            "default": True,
            "label": "Enable Feature"
        },
        "param3": {
            "type": "choice",
            "default": "option1",
            "choices": ["option1", "option2", "option3"],
            "label": "Select Option"
        }
    },
    "min_tests": 1,           # Minimum number of tests required
    "max_tests": 5,           # Maximum number of tests supported
    "category": "category_name"  # "single_test", "comparison", "metadata", etc.
}
```

### Step 4: Import and Expose Your Function

Update `__init__.py` to import and expose your function:

1. Add your function to the appropriate import section:
   ```python
   from .your_module import plot_your_new_visualization
   ```

2. Add your function to the `Visualizations` class:
   ```python
   plot_your_new_visualization = staticmethod(plot_your_new_visualization)
   ```

### Step 5: Test Your Visualization

1. Launch the GUI application
2. Load appropriate test data
3. Select your visualization from the dropdown
4. Configure parameters if needed
5. Click "Generate Visualization"

## Visualization Best Practices

For consistent and user-friendly visualizations:

1. **Clear Titles and Labels**: Always include descriptive titles, axis labels, and legends
2. **Appropriate Color Schemes**: Use colorblind-friendly palettes when possible
3. **Interactive Elements**: Add tooltips or clickable elements where useful
4. **Reasonable Defaults**: Set default parameters that work well in most cases
5. **Error Handling**: Check for missing or invalid data and handle gracefully
6. **Informative Messages**: Return None with appropriate messages when data is insufficient
7. **Efficient Processing**: Process data efficiently for large datasets

## Example: Adding a New Metadata Visualization

Here's a complete example of adding a new metadata visualization:

1. Add your function to `metadata_visualizations.py`:
   ```python
   def plot_server_comparison(selected_tests, params):
       """Compare different servers by upload and download speeds"""
       # ... visualization code ...
       return fig
   ```

2. Register it in `registry.py`:
   ```python
   "Server Speed Comparison": {
       "function": "plot_server_comparison",
       "description": "Compare upload and download speeds across different servers",
       "params": {
           "metric": {
               "type": "choice",
               "default": "max",
               "choices": ["max", "average", "median"],
               "label": "Speed Metric"
           }
       },
       "min_tests": 3,
       "max_tests": 20,
       "category": "metadata"
   }
   ```

3. Update `__init__.py`:
   ```python
   from .metadata_visualizations import (
       plot_test_duration_comparison,
       plot_server_comparison  # Add your new function
   )

   class Visualizations:
       # ... existing code ...
       plot_server_comparison = staticmethod(plot_server_comparison)  # Add this line
   ```

## Debugging Tips

If your visualization doesn't appear in the GUI:

1. Check if it's correctly registered in `registry.py`
2. Verify imports in `__init__.py`
3. Make sure the function name in the registry matches your actual function name
4. Check the function's return value (should be a matplotlib Figure or None)
5. Check for exceptions using try/except blocks in your visualization function

## Advanced Features

### Categorized Visualizations

Visualizations are categorized to help organize them in the GUI:
- `single_test` - Visualizations for analyzing a single test
- `comparison` - Visualizations for comparing multiple tests
- `metadata` - Visualizations for analyzing test metadata

Add custom categories by setting the `category` field in the registry.

### Custom Parameter Types

The GUI supports these parameter types:
- `numeric` - Numbers (integer or float)
- `boolean` - True/False toggles
- `choice` - Selection from predefined options

### Multi-Panel Visualizations

Create rich visualizations with multiple subplots:

```python
fig = Figure(figsize=(12, 8))
ax1 = fig.add_subplot(2, 1, 1)  # Top subplot
ax2 = fig.add_subplot(2, 1, 2)  # Bottom subplot
```