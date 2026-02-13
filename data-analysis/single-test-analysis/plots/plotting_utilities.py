""""
The following functions are defined:
1) ensure_plot_dir: Ensures that the plot directory exists - used when we need to save the plots to their corresponding tests
2) save_figure: Saves the figure to the plot_images directory if it doesn't already exist
"""
import os


def ensure_plot_dir(base_path):
    #If the plot_images directory does not exist in the directory that the test resides in, create it
    plot_dir = os.path.join(base_path, "plot_images")
    if not os.path.exists(plot_dir):
        os.makedirs(plot_dir)
        print(f"Created directory: {plot_dir}")
    return plot_dir

def save_figure(fig, base_path, filename):
    #Save a figure to the plot_images directory if it doesn't already exist.
    plot_dir = ensure_plot_dir(base_path)
    filepath = os.path.join(plot_dir, filename)

    # If the file already exists, don't overwrite it - just keep the current one
    if os.path.exists(filepath):
        print(f"File already exists, not saving: {filepath}")
        return False

    # Otherwise, save the plot
    fig.savefig(filepath, dpi=300, bbox_inches='tight')
    print(f"Saved plot to: {filepath}")
    return True

