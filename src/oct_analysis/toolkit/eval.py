"""
Functions for post-processing of binarized OCT image stacks.

Includes:
- Voxel counting
- Height map generation
- Biovolume map generation
- Roughness calculation
- Porosity calculation
- Saving results to CSV
"""

# Python native imports
import os
import csv

# Third party imports
import numpy as np
import matplotlib.pyplot as plt

# Local imports
from oct_analysis.toolkit import utils


# Post-Processing functions
def voxel_count(binarized_stack: np.ndarray) -> int:
    """
    Counts the number of pixels with value 1.

    Parameters
    ----------
    img : numpy.ndarray
        The image as a numpy array.

    Returns
    -------
    count: int
    """

    utils.binary_check(binarized_stack)

    return np.sum(binarized_stack == 1)


def height_map(binarized_stack: np.ndarray, voxel_dimensions: tuple) -> np.ndarray:
    utils.binary_check(binarized_stack)

    dz, dy, dx = voxel_dimensions  # in mm
    slices, h, w = binarized_stack.shape

    max_indices = np.argmax(binarized_stack, axis=0)

    height_map = np.where(np.max(binarized_stack, axis=0) == 0, 0, max_indices + 1)
    height_map *= dz  # Convert index to physical height

    return height_map


def generate_Height_Map(img, voxel_size, filename, output_folder, vmin, vmax):
    """
    Generates a height map from an image.

    Parameters
    ----------
    img : numpy.ndarray
        The image as a numpy array.
    voxel_size : tuple
        The voxel size of the image. (z, y, x) in mm
    filename : str
        The filename of the image.

    Returns
    -------
    height_map : numpy.ndarray
        The height map as a numpy array.
    min_thickness : float
        The minimum thickness of the image.
    mean_thickness : float
        The mean thickness of the image.
    max_thickness : float
        The maximum thickness of the image.
    std_thickness : float
        The standard deviation of the thickness of the image.
    surface_coverage_3px : float
        The surface coverage of the image ignoring the bottom 3 pixels.
    surface_coverage_5px : float
        The surface coverage of the image ignoring the bottom 5 pixels.
    surface_coverage_10px : float
        The surface coverage of the image ignoring the bottom 10 pixels.
    Raises
    ------
    No Errors
    """
    # Change to 32-bit float for calculations
    img = img.astype(np.float32)
    # image_stack=np.flip(image_stack, axis=1)

    # Normalize by dividing by 255
    img /= 255.0

    # Get voxel size (assuming isotropic pixels in X and Y, different Z)
    dy, slice_thickness, dx = voxel_size  # Adjust if metadata is available
    print(f"Slice Thickness = {slice_thickness} mm")
    print(f"Pixel_dim_y = {dy} mm")
    print(f"Pixel_dim_x = {dx} mm")

    resliced_stack = np.transpose(img, (1, 2, 0))
    # Flip along the new z-axis to correct orientation
    # resliced_stack = np.flip(resliced_stack, axis=0)
    slices, h, w = resliced_stack.shape
    # Calculate the height map (maximum z value for each (x, y) position)
    max_indices = np.argmax(
        resliced_stack, axis=0
    )  # Maximum index along z-axis for each (x, y)
    height_map = slices - max_indices

    # Ensure zero indices remain zero
    height_map[max_indices == 0] = 0  # Set zero indices to zero height
    height_map = height_map * slice_thickness  # Convert index to physical height

    # Calculate figure size in inches based on the actual dimensions
    # Convert pixels to inches
    fig_width = w * dx
    fig_height = h * dy
    print(fig_width)
    print(fig_height)
    # Generate and save Fire-coded height map
    output_path = os.path.join(output_folder, f"{filename}_HM")
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    im = ax.imshow(
        height_map, cmap="inferno", vmin=vmin, vmax=vmax
    )  # Set min and max range for cmap
    ax.axis("off")
    plt.savefig(f"{output_path}.tiff", dpi=300, bbox_inches="tight", pad_inches=0)

    # Add a colorbar with reduced height
    cbar = plt.colorbar(im, ax=ax, fraction=0.03, pad=0.04)
    cbar.ax.set_ylabel("Height (mm)", rotation=270, labelpad=15)
    # Add a scale bar in the bottom right corner
    scale_bar_length = 100  # Length of the scale bar in pixels
    scale_bar_mm = scale_bar_length * dx  # Convert to mm
    ax.plot([w - scale_bar_length - 10, w - 10], [h - 20, h - 20], color="white", lw=2)
    ax.text(
        w - scale_bar_length - 10,
        h - 30,
        f"{scale_bar_mm:.1f} mm",
        color="white",
        fontsize=10,
        ha="left",
    )

    plt.savefig(f"{output_path}.png", dpi=300, bbox_inches="tight", pad_inches=0)
    plt.close()

    # Compute thickness statistics
    valid_pixels = height_map
    min_thickness = np.min(valid_pixels) if valid_pixels.size > 0 else 0
    mean_thickness = np.mean(valid_pixels) if valid_pixels.size > 0 else 0
    max_thickness = np.max(valid_pixels) if valid_pixels.size > 0 else 0
    std_thickness = np.std(valid_pixels) if valid_pixels.size > 0 else 0

    # Compute surface coverage using histogram method
    histogram, _ = np.histogram(height_map, bins=256, range=(0, np.max(height_map)))
    n_pixels = height_map.size
    substratum_coverage = (1 - np.sum(histogram[:3]) / n_pixels) * 100

    # Prepare results
    results = [
        "Statistics:",
        "-------------",
        f"Slice Thickness = {slice_thickness} mm",
        f"Min Thickness = {min_thickness} mm",
        f"Mean Thickness = {mean_thickness:.2f} mm",
        f"Max Thickness = {max_thickness} mm",
        f"Standard Deviation of Thickness = {std_thickness:.2f} mm",
        f"Surface Coverage 3px = {substratum_coverage:.2f} %",
    ]
    # Print results
    for line in results:
        print(line)

    return (
        height_map,
        min_thickness,
        mean_thickness,
        max_thickness,
        std_thickness,
        substratum_coverage,
    )


def generate_B_Map(img, voxel_size, filename, output_folder, vmin, vmax):
    """
    Generates a biovolume map from an image.

    Parameters
    ----------
    img : numpy.ndarray
        The image as a numpy array.
    voxel_size : tuple
        The voxel size of the image. (z, y, x) in mm
    filename : str
        The filename of the image.

    Returns
    -------
    B_map : numpy.ndarray
        The biovolume map as a numpy array.
    min_thickness : float
        The minimum thickness of the image.
    mean_thickness : float
        The mean thickness of the image.
    max_thickness : float
        The maximum thickness of the image.
    std_thickness : float
        The standard deviation of the thickness of the image.
    surface_coverage_3px : float
        The surface coverage of the image ignoring the bottom 3 pixels.
    surface_coverage_5px : float
        The surface coverage of the image ignoring the bottom 5 pixels.
    surface_coverage_10px : float
        The surface coverage of the image ignoring the bottom 10 pixels.
    Raises
    ------
    No Errors
    """
    # Change to 32-bit float for calculations
    img = img.astype(np.float32)
    # image_stack=np.flip(image_stack, axis=1)

    # Normalize by dividing by 255
    img /= 255.0

    # Get voxel size (assuming isotropic pixels in X and Y, different Z)
    dy, slice_thickness, dx = voxel_size  # Adjust if metadata is available
    print(f"Slice Thickness = {slice_thickness} mm")
    print(f"Pixel_dim_y = {dy} mm")
    print(f"Pixel_dim_x = {dx} mm")

    resliced_stack = np.transpose(img, (1, 2, 0))
    # Flip along the new z-axis to correct orientation
    # resliced_stack = np.flip(resliced_stack, axis=0)
    slices, h, w = resliced_stack.shape
    # Calculate the biovolume map (maximum z value for each (x, y) position)
    non_zero_counts = np.count_nonzero(
        resliced_stack, axis=0
    )  # Maximum index along z-axis for each (x, y)
    B_map = non_zero_counts * slice_thickness  # Convert index to physical height
    # Convert pixels to inches
    fig_width = w * dx
    fig_height = h * dy
    print(fig_width)
    print(fig_height)

    # Generate and save Fire-coded height map
    output_path = os.path.join(output_folder, f"{filename}_BM")
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    im = ax.imshow(
        B_map, cmap="inferno", vmin=vmin, vmax=vmax
    )  # Set min and max range for cmap
    ax.axis("off")
    plt.savefig(f"{output_path}.tiff", dpi=300, bbox_inches="tight", pad_inches=0)

    # Add a colorbar with reduced height
    cbar = plt.colorbar(im, ax=ax, fraction=0.03, pad=0.04)
    cbar.ax.set_ylabel("Height (mm)", rotation=270, labelpad=15)
    # Add a scale bar in the bottom right corner
    scale_bar_length = 100  # Length of the scale bar in pixels
    scale_bar_mm = scale_bar_length * dx  # Convert to mm
    ax.plot([w - scale_bar_length - 10, w - 10], [h - 20, h - 20], color="white", lw=2)
    ax.text(
        w - scale_bar_length - 10,
        h - 30,
        f"{scale_bar_mm:.1f} mm",
        color="white",
        fontsize=10,
        ha="left",
    )

    plt.savefig(f"{output_path}.png", dpi=300, bbox_inches="tight", pad_inches=0)
    plt.close()

    # Compute thickness statistics
    valid_pixels = B_map
    min_thickness_B_map = np.min(valid_pixels) if valid_pixels.size > 0 else 0
    mean_thickness_B_map = np.mean(valid_pixels) if valid_pixels.size > 0 else 0
    max_thickness_B_map = np.max(valid_pixels) if valid_pixels.size > 0 else 0
    std_thickness_B_map = np.std(valid_pixels) if valid_pixels.size > 0 else 0

    # Compute surface coverage using histogram method
    histogram, _ = np.histogram(B_map, bins=256, range=(0, np.max(B_map)))
    n_pixels = B_map.size
    substratum_coverage_B_map = (1 - np.sum(histogram[:4]) / n_pixels) * 100

    # Prepare results
    results = [
        "Statistics:",
        "-------------",
        f"Slice Thickness = {slice_thickness} mm",
        f"Min Thickness = {min_thickness_B_map} mm",
        f"Mean Thickness = {mean_thickness_B_map:.2f} mm",
        f"Max Thickness = {max_thickness_B_map} mm",
        f"Standard Deviation of Thickness = {std_thickness_B_map:.2f} mm",
        f"Surface Coverage 3px = {substratum_coverage_B_map:.2f} %",
    ]
    # Print results
    for line in results:
        print(line)

    return (
        B_map,
        min_thickness_B_map,
        mean_thickness_B_map,
        max_thickness_B_map,
        std_thickness_B_map,
        substratum_coverage_B_map,
    )


def calculate_roughness(img, voxel_size, threshold=0):
    """
    Calculate roughness metrics across all slices.

    Parameters:
    ----------
    img_stack : 3D numpy array (slices, height, width)
    threshold : Intensity threshold

    Returns:
    ----------
    mean_thickness : float
    mean_arithmetic_roughness (Ra) : float
    mean_rms_roughness (Rq) : float
    std_rms_roughness (Rq) : float
    mean_roughness_coeff (Ra / mean_thickness) : float
    std_roughness_coeff (Ra / mean_thickness) : float
    """
    import numpy as np

    slices, height, width = img.shape
    dy, slice_thickness, dx = voxel_size  # Adjust if metadata is available

    mean_thickness_list = []
    arithmetic_roughness_list = []
    rms_roughness_list = []
    roughness_coeff_list = []

    for k in range(slices):
        slice_img = img[k]
        surface_heights = []

        for i in range(width):
            column = slice_img[:, i]
            above_threshold = np.where(column > threshold)[0]

            if len(above_threshold) > 0:
                biofilm_down = height - above_threshold[0]
            else:
                biofilm_down = 0  # No biofilm found

            surface_heights.append(biofilm_down)

        surface_heights = np.array(surface_heights) * slice_thickness

        mean_thickness = np.mean(surface_heights)
        arithmetic_roughness = np.mean(np.abs(surface_heights - mean_thickness))  # Ra
        rms_roughness = np.std(surface_heights)  # Rq
        roughness_coeff = (
            arithmetic_roughness / mean_thickness if mean_thickness > 0 else 0
        )

        mean_thickness_list.append(mean_thickness)
        arithmetic_roughness_list.append(arithmetic_roughness)
        rms_roughness_list.append(rms_roughness)
        roughness_coeff_list.append(roughness_coeff)

    # Global metrics across slices
    mean_thickness = np.mean(mean_thickness_list)
    mean_arithmetic_roughness = np.mean(arithmetic_roughness_list)
    std_arithmetric_roughness = np.std(arithmetic_roughness_list)
    mean_rms_roughness = np.mean(rms_roughness_list)
    std_rms_roughness = np.std(rms_roughness_list)
    mean_roughness_coeff = np.mean(roughness_coeff_list)
    std_roughness_coeff = np.std(roughness_coeff_list)

    print(f"Mean Thickness = {mean_thickness:.3f} mm")
    print(f"Mean Arithmetic Roughness (Ra) = {mean_arithmetic_roughness:.3f} mm")
    print(f"Mean RMS Roughness (Rq) = {mean_rms_roughness:.3f} mm")
    print(f"Mean Roughness Coefficient = {mean_roughness_coeff:.3f}")
    print(f"Std Roughness Coefficient = {std_roughness_coeff:.3f}")
    print(f"Std Arithmetic Roughness (Ra) = {std_arithmetric_roughness:.3f} mm")
    print(f"Std RMS Roughness (Rq) = {std_rms_roughness:.3f} mm")

    return (
        mean_arithmetic_roughness,
        std_arithmetric_roughness,
        mean_rms_roughness,
        std_rms_roughness,
        mean_roughness_coeff,
        std_roughness_coeff,
    )


def calculate_porosity(img, threshold=0):
    """
    Calculate porosity per slice and return mean and std over all slices.

    Parameters:
    ----------
    img_stack : 3D numpy array (slices, height, width)
    threshold : Intensity threshold

    Returns:
    ----------
    mean_porosity : float
    std_porosity : float
    """
    import numpy as np

    slices, height, width = img.shape
    porosity_list = []

    for k in range(slices):
        slice_img = img[k]
        total_void_voxels = 0
        total_surface_voxels = 0

        for i in range(width):
            column = slice_img[:, i]
            above_threshold = np.where(column > threshold)[0]

            if len(above_threshold) > 0:
                surface_pos = above_threshold[0]
            else:
                surface_pos = height  # No biofilm found → whole column is considered

            void_voxels = np.sum(column[surface_pos:height] <= threshold)
            total_void_voxels += void_voxels
            total_surface_voxels += height - surface_pos

        porosity = (
            total_void_voxels / total_surface_voxels if total_surface_voxels > 0 else 0
        )
        porosity_list.append(porosity)

    mean_porosity = np.mean(porosity_list) * 100  # Convert to percentage
    std_porosity = np.std(porosity_list) * 100  # Convert to percentage

    print(f"Mean Porosity = {mean_porosity:.3f} %")
    print(f"Std Porosity = {std_porosity:.3f} %")

    return mean_porosity, std_porosity


def calculate_porosity_between_bounds(binarized_stack: np.ndarray) -> float:
    """
    Calculates porosity in a binary 3D stack (0=void, 1=material),
    considering only the region between the first and last material voxel (1) in each column.

    Parameters:
    ----------
    img : 3D numpy array with values 0 and 1

    Returns:
    ----------
    porosity : float (in %)
    """
    _, h, _ = binarized_stack.shape
    mask = binarized_stack.astype(bool)  # 1=True, 0=False

    # Für jede Spalte: erste(oberste) und letzte(unterste) Position mit 1 finden
    first = np.argmax(mask, axis=1)  # shape (slices, width)
    last = h - np.argmax(mask[:, ::-1, :], axis=1) - 1  # von unten suchen

    # Leere Spalten werden für die Porositätsberechnung ignoriert
    no_material = ~np.any(mask, axis=1)
    first[no_material] = 0
    last[no_material] = -1  # sorgt für leere Auswahl im nächsten Schritt

    rows = np.arange(h).reshape(1, h, 1)
    in_bounds = (rows >= first[:, None, :]) & (rows <= last[:, None, :])

    void_region = (binarized_stack == 0) & in_bounds

    void_voxels = np.sum(void_region)
    total_voxels = np.sum(in_bounds)

    porosity = (void_voxels / total_voxels * 100) if total_voxels > 0 else 0

    print(f"Porosity (between bounds) = {porosity:.3f} %")
    return porosity


def save_results_to_csv(output_folder, headers, data):
    """
    Save calculated results to a CSV file.

    Parameters
    ----------
    output_folder : str
        The folder where the CSV file will be saved.
    filename : str
        The name of the file being processed (used as the first column in the CSV).
    headers : list
        A list of column headers for the CSV file.
    data : list
        A list of calculated values to save in the CSV.

    Returns
    -------
    None
    """
    # Ensure the output folder exists
    os.makedirs(output_folder, exist_ok=True)

    # Define the output CSV file path
    csv_file_path = os.path.join(output_folder, "results.csv")

    # Check if the file already exists to determine if headers need to be written
    file_exists = os.path.isfile(csv_file_path)

    # Open the CSV file in append mode
    with open(csv_file_path, mode="a", newline="") as csvfile:
        writer = csv.writer(csvfile)

        # Write the header if the file is being created for the first time
        if not file_exists:
            writer.writerow(headers)

        # Write the data row
        writer.writerow(data)
