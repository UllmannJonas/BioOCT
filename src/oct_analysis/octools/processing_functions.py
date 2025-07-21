"""
Image processing functions for oct_analysis
"""

import tifffile as tiff
import os
import csv
import numpy as np
from numpy.typing import NDArray
import matplotlib.pyplot as plt
from skimage import exposure, filters, morphology
import scipy.ndimage
from pathlib import Path
import tempfile
import zipfile
import xml.etree.ElementTree as ET
import nibabel as nib
from napari.utils.notifications import show_info
from napari.utils.notifications import show_error

def read_tiff(file_path: str) -> tuple[np.ndarray, str, dict]:
    """
    Read a 3D TIFF stack and its metadata.

    Parameters
    ----------
    file_path : str
        Path to the TIFF file

    Returns
    -------
    tuple
        A tuple containing:
        - numpy.ndarray: The 3D image stack as a numpy array
        - str: The filename without extension
        - dict: The metadata from the TIFF file

    Raises
    ------
    FileNotFoundError
        If the file does not exist
    ValueError
        If the file could not be read as an image
    """
    # Check if the file exists before trying to read it
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    try:
        # Extract filename without extension
        filename = os.path.splitext(os.path.basename(file_path))[0]

        # Use tifffile to read the TIFF stack and metadata
        with tiff.TiffFile(file_path) as tif:
            page = tif.pages[0]  # Read the first page
            description = page.tags.get('ImageDescription') # type: ignore
            imagej_metadata = {}

            if description:
                desc = description.value
            for line in desc.split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    imagej_metadata[key] = value
            # Read the image stack
            img_stack = tif.asarray()
            assert img_stack.dtype == np.float32, "Image stack is not in float32 format!"
            metadata = {
            'Z': int(imagej_metadata.get('slices', 1)),
            'Y': page.tags['ImageLength'].value, # type: ignore
            'X': page.tags['ImageWidth'].value, # type: ignore
            'shape': tif.series[0].shape,
            'dtype': str(tif.series[0].dtype),
            'axes': tif.series[0].axes,
            'XResolution': page.tags['XResolution'].value, # type: ignore
            'YResolution': page.tags['YResolution'].value, # type: ignore
            'unit': imagej_metadata.get('unit', None),
            'spacing': float(imagej_metadata.get('spacing', 1.0)),
        }
        if img_stack is None:
            raise ValueError(f"Failed to read image from {file_path}")

        return img_stack, filename, metadata
    except Exception as e:
        raise ValueError(f"Error reading TIFF file: {str(e)}") from e

def _normalize_tiff(tiff_stack: np.ndarray) -> np.ndarray:
    """
    Normalize a 3D TIFF stack to the range [0, 1].

    Parameters
    ----------
    tiff_stack : numpy.ndarray
        The 3D image stack to normalize (slices, height, width)

    Returns
    -------
    numpy.ndarray
        The normalized 3D image stack as a float32 array
    """
    if len(tiff_stack.shape) != 3:
        raise ValueError("Input must be a 3D array (slices, height, width)")
    
    # Normalize each slice to the range [0, 1]
    tiff_stack = tiff_stack.astype(np.float32)
    tiff_stack -= np.min(tiff_stack)
    tiff_stack /= np.max(tiff_stack)
    
    return tiff_stack




    """
    Normalize a 3D TIFF stack to the range [0, 1].

    Parameters
    ----------
    tiff_stack : numpy.ndarray
        The 3D image stack to normalize (slices, height, width)

    Returns
    -------
    numpy.ndarray
        The normalized 3D image stack as a float32 array
    """
    if len(tiff_stack.shape) != 3:
        raise ValueError("Input must be a 3D array (slices, height, width)")
    
    # Normalize each slice to the range [0, 1]
    tiff_stack = tiff_stack.astype(np.float32)
    tiff_stack -= np.min(tiff_stack)
    tiff_stack /= np.max(tiff_stack)
    
    return tiff_stack

def save_tiff(img, file_path, filename, metadata=None):
    """
    Save a 3D numpy array as a TIFF file with metadata.

    Parameters
    ----------
    img : numpy.ndarray
        The 3D image stack to save (slices, height, width)
    file_path : str
        Path where to save the TIFF file
    metadata : dict, optional
        Dictionary containing metadata to save with the image.
        Common keys include:
        - 'shape': tuple, shape of the image
        - 'dtype': str, data type of the image
        - 'axes': str, axes order (e.g., 'ZYX')
        - 'resolution': tuple, (x_resolution, y_resolution) µm per pixel
        - 'resolutionunit': str, unit of resolution (e.g., 'um')

    Returns
    -------
    None

    Raises
    ------
    ValueError
        If the input is not a 3D array or if saving fails
    """
    if len(img.shape) != 3:
        raise ValueError("Input must be a 3D array (slices, height, width)")
    
    # Check for zero-size array
    if img.size == 0 or any(dim == 0 for dim in img.shape):
        raise ValueError("Cannot save zero-size array or array with zero dimensions")

    try:
        # Prepare metadata
        if metadata is None:
            metadata = {}
        
        # Add basic metadata if not present
        if 'shape' not in metadata:
            metadata['shape'] = img.shape
        if 'dtype' not in metadata:
            metadata['dtype'] = str(img.dtype)
        if 'axes' not in metadata:
            metadata['axes'] = 'ZYX'  # Default axes order for 3D stack
        # Save the image with metadata
        save_path = os.path.join(file_path, f"{filename}.tif")
        with tiff.TiffWriter(save_path) as tif:
            tif.write(
                img,
                metadata=metadata,
                #resolution=metadata.get('resolution', ('X_Resolution', 'Y_Resolution')),
            )

    except Exception as e:
        raise ValueError(f"Error saving TIFF file: {str(e)}") from e

# >>>not needed with napari<<<
def select_tiff_folder():
    pass
    #     """
    #     Opens a window to select a folder containing TIFF files.

    #     Returns
    #     -------
    #     str
    #         The path to the selected folder.
    #     """
    #     root = ctk.CTk()
    #     root.withdraw()  # Hide the root window
    #     folder_path = ctk.filedialog.askdirectory(title="Select Folder")
    #     if folder_path:
    #         print(f"Selected Folder: {folder_path}")
    #     else:
    #         print("No folder selected.")
    #     return folder_path

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
    with open(csv_file_path, mode='a', newline='') as csvfile:
        writer = csv.writer(csvfile)

        # Write the header if the file is being created for the first time
        if not file_exists:
            writer.writerow(headers)

        # Write the data row
        writer.writerow(data)

# Pre-Processing functions
# >>>not needed for speed, rather keep orginal float32 data<<<
def convert_to_8bit(img):
    pass
    # """
    # Converts an image to 8-bit format.

    # Parameters
    # ----------
    # img : numpy.ndarray
    #     The image as a numpy array.

    # Returns
    # -------
    # numpy.ndarray
    #     The image as a numpy array.
    # """
    # if np.issubdtype(img.dtype, np.floating):
    #     img = (img - img.min()) / (img.max() - img.min())  # Normalize to [0, 1]
    #     img = (img * 255).astype(np.uint8)  # Scale to [0, 255]
    # else:
    #     # If the image is integer-based (like uint32), just scale it to [0, 255]
    #     img = (img.astype(np.float32) - img.min()) / (img.max() - img.min())  # Normalize to [0, 1]
    #     img = (img * 255).astype(np.uint8)  # Scale to [0, 255]
    # return img

def find_substratum(img, start_x, y_max, roi_width, scan_height, step_width):

    """
    Find the substratum in a 3D image stack.

    Parameters
    ----------
    img : numpy.ndarray
        The 3D image stack as a numpy array (slices, height, width)
    start_x : int
        The x-coordinate of the starting point of the scan (default = 0)
    y_max : int
        Maximum y-coordinate of the substratum at the starting point (typically the half of the height of the image)
    roi_width : int
        Width of the region of interest (default = 20)
    scan_height : int
        Height of the scan area (default = 10)
    step_width : int
        Width of the scan steps (default = 5)

    Returns
    -------
    numpy.ndarray
        The image as a numpy array

    Raises
    ------
    No Errors
    """
    # Ensure we're working with a 3D stack
    if len(img.shape) != 3:
        raise ValueError("Input image must be a 3D stack (slices, height, width)")

    # Flip the stack horizontally
    img = img[:, ::-1, :]
    slices, h, w = img.shape
    
    # Process each slice
    for slice_idx in range(slices):
        maxSum = 0
        memBot = 0
        # Find the bottom of the membrane in the first slice
        for i in range(y_max):
            roi = img[slice_idx, i, start_x:start_x+roi_width]
            sum_val = np.mean(roi)
            if sum_val > maxSum:
                maxSum = sum_val
                memBot = i
        memBot1 = memBot
    # Vorschlag: loops vektorisieren --> schneller
    # 1. precompute roi-mean für ganzen stack:
    # filtered = scipy.ndimage.uniform_filter1d(stack, size=roi, axis=2, mode='reflect')
    # 2. maximum intensity in bestimmtem y-bereich finden:
    # y_coords = np.argmax(filtered[:, ymin:ymax, :], axis=1)
    # apply y-offset
    # y_coords += y_offset
    # nach diesen drei zeilen haben wir die koordinaten und können untilt oder remove_window machen


        # Process each slice
        for x in range(start_x, w, step_width):
            memBot = memBot1
            for y in range(memBot - scan_height, memBot + scan_height, 1):
                # Ensure 'y' is within bounds for the image height
                if y < 0:
                    y = 0
                elif y >= h:
                    y = h - 1
                roi = img[slice_idx, y, x:x+roi_width]
                sum_val = np.mean(roi)
                if sum_val > maxSum:
                    maxSum = sum_val
                    memBot = y
                if start_x == 0:
                    memBot1 = memBot
            maxSum = 0
            if memBot > 0:
                img[slice_idx, :memBot, x:x+step_width] = 0  # Set area to black
    
    # Flip the stack back
    img = img[:, ::-1, :]
    return img

def find_two_point_line(img, x1=0, x2=None, thres_line=1):
    """
    Find a line between two points in an image and draw it on the image stack.
    This is a Python implementation of the line finding part from the ImageJ macro '2PointsLine.ijm'.

    Parameters
    ----------
    img : numpy.ndarray
        The 3D image stack as a numpy array (slices, height, width)
    x1 : int, optional
        X-coordinate of the first point (default=0)
    x2 : int, optional
        X-coordinate of the second point. If None, uses image width - 1 (default=None)
    thres_line : int, optional
        Threshold for line detection (default=1)

    Returns
    -------
    tuple
        A tuple containing:
        - numpy.ndarray: The image stack with lines drawn
        - list: List of (x1, y1, x2, y2) coordinates for each slice
    """
    if len(img.shape) != 3:
        raise ValueError("Input image must be a 3D stack (slices, height, width)")

    slices, height, width = img.shape
    if x2 is None:
        x2 = width - 1

    # Create a copy of the input image to draw lines on
    img_with_lines = img.copy()
    line_coords = []

    def find_y_coordinate(slice_img, x):
        """Find the y-coordinate where the intensity exceeds threshold."""
        profile = slice_img[:, x]
        for y in range(len(profile)-1, -1, -1):
            if profile[y] >= thres_line:
                return y
        return 0

    def draw_line(slice_img, x1, y1, x2, y2):
        """Draw a line on the image using Bresenham's line algorithm."""
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy

        while True:
            # Set the pixel to white (255)
            slice_img[y1, x1] = 255

            if x1 == x2 and y1 == y2:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x1 += sx
            if e2 < dx:
                err += dx
                y1 += sy

    # Process each slice
    for s in range(slices):
        current_slice = img_with_lines[s]
        
        # Find y-coordinates for both points
        y1 = find_y_coordinate(current_slice, x1)
        y2 = find_y_coordinate(current_slice, x2)
        
        # Store line coordinates
        line_coords.append((x1, y1, x2, y2))
        
        # Draw the line on the current slice
        draw_line(current_slice, x1, y1, x2, y2)

    return img_with_lines, line_coords

def find_max_zero(img, top_crop):
    """
    Finds the maximum number of consecutive zero pixels from the top in any column
    and removes that many rows from the top of the image.

    Parameters
    ----------
    img : numpy.ndarray
        The image as a numpy array.
    top_crop : int
        Additional number of pixels to crop from the top of the image.

    Returns
    -------
    numpy.ndarray
        The image as a numpy array with top zero pixels removed.
    """
    slices, h, w = img.shape
    # Variable to keep track of the maximum number of consecutive zero pixels from top
    max_zero_pixels = 0

    # Loop through each slice
    for s in range(slices):
        # Get the current slice
        slice_img = img[s]

        # Loop through each pixel column (x) in the slice
        for x in range(w):
            profile = slice_img[:, x]
            
            # Find the first non-zero pixel
            non_zero_idx = np.where(profile > 0)[0]
            if len(non_zero_idx) > 0:
                # Count consecutive zeros from top until first non-zero
                zero_count = non_zero_idx[0]
                max_zero_pixels = max(max_zero_pixels, zero_count)

    # Add the additional top_crop to the number of rows to remove
    rows_to_remove = max_zero_pixels + top_crop
    
    # Ensure we don't remove more rows than the image height
    rows_to_remove = min(rows_to_remove, h-1)
    
    # Remove the rows from the top
    if rows_to_remove > 0:
        img = img[:, rows_to_remove:, :]
    
    return img

def untilt(img, thres, y_offset, top_crop):
    """
    Finds the substratum in an image and tilts it until the substratum is horizontal.

    Parameters
    ----------
    img : numpy.ndarray
        The image as a numpy array.
    thres : int
        The threshold for the substratum.
    y_offset : int
        The y-offset of the substratum.
    top_crop : int
        The number of pixels to crop from the top of the image.

    Returns
    -------
    numpy.ndarray
        The image as a numpy array.
    """
    slices, h, w = img.shape
    img = img[:, ::-1, :]
    # Create an empty array for the resulting image with same dimensions
    new_img_array = np.zeros_like(img)

    for s in range(slices):
        # Get the current slice
        slice_img = img[s]

        # Loop through each pixel column (x) in the slice
        for x in range(w):
            profile = slice_img[:, x]
            
            # Find the first pixel that exceeds the threshold
            first_pixel_idx = np.where(profile > thres)[0]
            
            if len(first_pixel_idx) > 0:
                first_pixel_idx = first_pixel_idx[0]
                # Get all pixels from the first threshold-exceeding pixel to the end
                non_zero_pixels = profile[first_pixel_idx:]
                # Move these pixels to the top of the column, rest remains 0
                new_img_array[s, :len(non_zero_pixels), x] = non_zero_pixels
                # The rest of the column is already 0 from np.zeros_like

    img = new_img_array[:, ::-1, :]
    
    # Ensure we don't crop more than the image height
    y_offset = min(y_offset, h-1)
    if y_offset > 0:
        img = img[:, :-y_offset, :]
    
    img = find_max_zero(img, top_crop)
    
    # Final check to ensure we have a valid image
    if img.size == 0 or any(dim == 0 for dim in img.shape):
        raise ValueError("Untilt operation resulted in zero-size array. Check threshold and crop parameters.")
        
    return img

# untested vectorized version of untilt
def vectorized_untilt(stack: np.ndarray, substratum_coords: np.ndarray) -> np.ndarray:
    _, y, x = stack.shape
    result = np.empty_like(stack)

    y_subs = substratum_coords[:, np.newaxis, :] # transpose coords for broadcasting
    y_range = np.arange(y).reshape(1, y, 1) # y-axis as array for broadcasting

    keep_mask = y_range < y_subs # boolmask: True=Substratum
    zeros_below = ~keep_mask # boolmask: True=Zeroed-out substratum

    body = stack[keep_mask].reshape(-1, x)  # stack content (=keep_mask) as 2D array
    zeros = stack[zeros_below].reshape(-1, x)  # zeros below substratum as 2D array
    new_stack = np.concatenate([zeros, body], axis=0) # stick together, zeros on top

    result = new_stack.reshape(stack.shape) # reshape to original

    return result


def binary_mask(img, thresholding_method, contrast, blurred, blur_size, outliers_size):
    """
    Create a binary mask from an image stack using various preprocessing steps.

    Parameters
    ----------
    img : numpy.ndarray
        The 3D image stack as a numpy array (slices, height, width)
    thresholding_method : str
        The method to use for thresholding. Options are:
        - 'yen': Yen's thresholding method
        - 'otsu': Otsu's thresholding method
    contrast : float
        The contrast enhancement percentile. Values between 0 and 100.
        For example, if contrast=2, the intensity range will be stretched
        between the 2nd and 98th percentiles.
    blurred : bool
        Whether to apply Gaussian blur before thresholding
    blur_size : int
        Size of the Gaussian blur kernel. Must be positive and odd.
    outliers_size : int
        Minimum size of objects to keep after thresholding.
        Objects smaller than this size will be removed.

    Returns
    -------
    numpy.ndarray
        The processed binary mask as a 3D numpy array (slices, height, width)
        with values 0 (black) and 255 (white)

    Notes
    -----
    The function performs the following steps:
    1. Optional Gaussian blur for noise reduction
    2. Contrast enhancement using percentile-based stretching
    3. Thresholding using either Yen's or Otsu's method
    4. Removal of small objects (outliers)
    """
    processed_frames = []
    for _, image in enumerate(img):
        if blurred:
            # Apply Gaussian blur before contrast enhancement
            sigma = 0.3 * ((blur_size - 1) * 0.5 - 1) + 0.8
            image_blurred = scipy.ndimage.gaussian_filter(image, sigma=sigma)
        else:
            image_blurred = image
        
        # Enhance contrast
        p2, p98 = np.percentile(image_blurred, (contrast, 100-contrast))  
        image_contrast = exposure.rescale_intensity(image_blurred, in_range=(p2, p98)) # type: ignore

        if thresholding_method == 'yen':
            # Apply Yen's thresholding method
            yen_threshold = filters.threshold_yen(image_contrast)
            image_thresholded = image_contrast > yen_threshold
        elif thresholding_method == 'otsu':
            # Apply Otsu's thresholding method
            otsu_threshold = filters.threshold_otsu(image_contrast)
            image_thresholded = image_contrast > otsu_threshold

        # Remove small bright objects
        image_no_outliers = morphology.remove_small_objects(image_thresholded, min_size=outliers_size, connectivity=1)

        # Append processed frame to the list
        processed_frames.append(image_no_outliers.astype(np.uint8) * 255)

    # Convert list to 3D numpy array (num_frames, height, width)
    img = np.stack(processed_frames, axis=0)
    return img

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

    if not set(np.unique(binarized_stack)).issubset({0, 1}):
        raise ValueError("Passed stack is not binarized, contains values unequal to 0 or 1.")

    return np.sum(binarized_stack==1)

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
    #image_stack=np.flip(image_stack, axis=1)

    # Normalize by dividing by 255
    img /= 255.0
    
    # Get voxel size (assuming isotropic pixels in X and Y, different Z)
    dy, slice_thickness, dx = voxel_size  # Adjust if metadata is available
    print(f"Slice Thickness = {slice_thickness} mm")
    print(f"Pixel_dim_y = {dy} mm")
    print(f"Pixel_dim_x = {dx} mm")
    
    resliced_stack = np.transpose(img, (1, 2, 0))
    # Flip along the new z-axis to correct orientation
    #resliced_stack = np.flip(resliced_stack, axis=0) 
    slices, h, w = resliced_stack.shape
    # Calculate the height map (maximum z value for each (x, y) position)
    max_indices = np.argmax(resliced_stack, axis=0)  # Maximum index along z-axis for each (x, y)  
    height_map = (slices-max_indices) 

    # Ensure zero indices remain zero
    height_map[max_indices == 0] = 0 # Set zero indices to zero height
    height_map = height_map * slice_thickness  # Convert index to physical height

    # Calculate figure size in inches based on the actual dimensions
    # Convert pixels to inches
    fig_width = w*dx
    fig_height = h*dy
    print(fig_width)
    print(fig_height)
    # Generate and save Fire-coded height map
    output_path = os.path.join(output_folder, f"{filename}_HM")
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    im = ax.imshow(height_map, cmap='inferno', vmin=vmin, vmax=vmax)  # Set min and max range for cmap
    ax.axis('off')
    plt.savefig(f"{output_path}.tiff", dpi=300, bbox_inches='tight', pad_inches=0)
    
    # Add a colorbar with reduced height
    cbar = plt.colorbar(im, ax=ax, fraction=0.03, pad=0.04)
    cbar.ax.set_ylabel('Height (mm)', rotation=270, labelpad=15)
    # Add a scale bar in the bottom right corner
    scale_bar_length = 100  # Length of the scale bar in pixels
    scale_bar_mm = scale_bar_length * dx  # Convert to mm
    ax.plot([w - scale_bar_length - 10, w - 10], [h - 20, h - 20], color='white', lw=2)
    ax.text(w - scale_bar_length - 10, h - 30, f"{scale_bar_mm:.1f} mm", color='white', fontsize=10, ha='left')

    plt.savefig(f"{output_path}.png", dpi=300, bbox_inches='tight', pad_inches=0)
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
    
    return height_map, min_thickness, mean_thickness, max_thickness, std_thickness, substratum_coverage

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
    #image_stack=np.flip(image_stack, axis=1)

    # Normalize by dividing by 255
    img /= 255.0
    
    # Get voxel size (assuming isotropic pixels in X and Y, different Z)
    dy, slice_thickness, dx = voxel_size  # Adjust if metadata is available
    print(f"Slice Thickness = {slice_thickness} mm")
    print(f"Pixel_dim_y = {dy} mm")
    print(f"Pixel_dim_x = {dx} mm")
    
    resliced_stack = np.transpose(img, (1, 2, 0))
    # Flip along the new z-axis to correct orientation
    #resliced_stack = np.flip(resliced_stack, axis=0) 
    slices, h, w = resliced_stack.shape
    # Calculate the biovolume map (maximum z value for each (x, y) position)
    non_zero_counts = np.count_nonzero(resliced_stack, axis=0)  # Maximum index along z-axis for each (x, y)   
    B_map = non_zero_counts * slice_thickness  # Convert index to physical height
    # Convert pixels to inches
    fig_width = w*dx
    fig_height = h*dy
    print(fig_width)
    print(fig_height)
    
    # Generate and save Fire-coded height map
    output_path = os.path.join(output_folder, f"{filename}_BM")
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    im = ax.imshow(B_map, cmap='inferno', vmin=vmin, vmax=vmax)  # Set min and max range for cmap
    ax.axis('off')
    plt.savefig(f"{output_path}.tiff", dpi=300, bbox_inches='tight', pad_inches=0)
    
    # Add a colorbar with reduced height
    cbar = plt.colorbar(im, ax=ax, fraction=0.03, pad=0.04)
    cbar.ax.set_ylabel('Height (mm)', rotation=270, labelpad=15)
    # Add a scale bar in the bottom right corner
    scale_bar_length = 100  # Length of the scale bar in pixels
    scale_bar_mm = scale_bar_length * dx  # Convert to mm
    ax.plot([w - scale_bar_length - 10, w - 10], [h - 20, h - 20], color='white', lw=2)
    ax.text(w - scale_bar_length - 10, h - 30, f"{scale_bar_mm:.1f} mm", color='white', fontsize=10, ha='left')

    plt.savefig(f"{output_path}.png", dpi=300, bbox_inches='tight', pad_inches=0)
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
    
    return B_map, min_thickness_B_map, mean_thickness_B_map, max_thickness_B_map, std_thickness_B_map, substratum_coverage_B_map

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
                biofilm_down = height-above_threshold[0]
            else:
                biofilm_down = 0  # No biofilm found

            surface_heights.append(biofilm_down)

        surface_heights = np.array(surface_heights)*slice_thickness

        mean_thickness = np.mean(surface_heights)
        arithmetic_roughness = np.mean(np.abs(surface_heights - mean_thickness))  # Ra
        rms_roughness = np.std(surface_heights)  # Rq
        roughness_coeff = arithmetic_roughness / mean_thickness if mean_thickness > 0 else 0

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


    return (mean_arithmetic_roughness,
            std_arithmetric_roughness, 
            mean_rms_roughness, 
            std_rms_roughness, 
            mean_roughness_coeff, 
            std_roughness_coeff)

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
            total_surface_voxels += height-surface_pos

        porosity = total_void_voxels / total_surface_voxels if total_surface_voxels > 0 else 0
        porosity_list.append(porosity)

    mean_porosity = np.mean(porosity_list)*100 # Convert to percentage
    std_porosity = np.std(porosity_list)*100 # Convert to percentage

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
    mask = binarized_stack.astype(bool) # 1=True, 0=False

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



# Labeling functions
## utility functions
def load_oct(filepath: Path):

    ext = ''.join(filepath.suffixes).lower()
    if ext in ['.nii', '.nii.gz', '.niigz']:
        img = nib.nifti1.load(str(filepath))
        data = img.get_fdata(dtype=np.float32)
        header = img.header

        meta = {
            'size_px': {
                'x': int(header['dim'][1]),
                'z': int(header['dim'][2]),
                'y': int(header['dim'][3]),
            },
            'spacing_mm': {
                'x': float(header.get_zooms()[0]),
                'y': float(header.get_zooms()[1]), # type: ignore
                'z': float(header.get_zooms()[2]), # type: ignore
            },
            'filename': str(filepath.stem)
        }
        print(meta)
        return data, meta
    
    oct_as_zip = filepath.with_suffix('.zip')
    renamed = False
    try:
        filepath.rename(oct_as_zip)
        renamed = True

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            header_path = tmp_path / 'Header.xml'
            data_path = tmp_path / 'data' / 'Intensity.data'
            with zipfile.ZipFile(oct_as_zip, 'r') as zip_ref:
                zip_ref.extractall(tmp_path)

            # get metadata
            tree = ET.parse(header_path)
            root = tree.getroot()

            try:
                def get(path, cast=str):
                    element = root.find(path)
                    return cast(element.text) if element is not None else 0

                meta = {
                    'size_px': {
                        'z': int(get("Image/SizePixel/SizeZ")),
                        'y': int(get("Image/SizePixel/SizeY")),
                        'x': int(get("Image/SizePixel/SizeX")),
                    },
                    'fov_mm': {
                        'z': float(get("Image/SizeReal/SizeZ")),
                        'y': float(get("Image/SizeReal/SizeY")),
                        'x': float(get("Image/SizeReal/SizeX")),
                    },
                    'spacing_mm': {
                        'z': float(get("Image/PixelSpacing/SizeZ")),
                        'y': float(get("Image/PixelSpacing/SizeY")),
                        'x': float(get("Image/PixelSpacing/SizeX")),
                    },
                    'instrument': {
                        'model': get("Instrument/Model"),
                        'serial': get("Instrument/Serial"),
                        'central_wavelength': float(get("Instrument/CentralWavelength")),
                    },
                    'dtype': get("Image/DataType"),
                    'timestamp': int(get("Acquisition/Timestamp")),
                    'filename': str(Path(filepath).stem)
                }
                # Fallback falls PixelSpacing = 0:
                for axis in ['x', 'y', 'z']:
                    if meta['spacing_mm'][axis] == 0.0:
                        if meta['size_px'][axis] > 0 and meta['fov_mm'][axis] > 0:
                            meta['spacing_mm'][axis] = meta['fov_mm'][axis] / meta['size_px'][axis]
                        else:
                            print(f"[WARN] Invalid pixel size for axis {axis}, fallback not possible")

            except (TypeError, ValueError, AttributeError) as e:
                print(f"[ERROR] Failed to parse metadata: {e}. Process terminated. Please check Header.xml file.")
                return

            # reformat intensity.data into np.ndarray
            with open(data_path, 'rb') as f:
                intensity_data_raw = f.read()

            shape_raw = (meta['size_px']['y'], meta['size_px']['x'], meta['size_px']['z']) # ZXY
            data = np.frombuffer(intensity_data_raw, dtype=np.float32).copy().reshape(shape_raw)
            data = data.transpose(0, 2, 1)
        
    finally:
        if renamed and oct_as_zip.exists:
            oct_as_zip.rename(filepath)

    return data, meta

def _normalize(stack: NDArray[np.float32]) -> NDArray[np.float32]:
    stack_norm = (stack - np.min(stack)) / (np.max(stack) - np.min(stack))
    return stack_norm.astype(np.float32)

def save(stack: np.ndarray, stack_metadata: dict, binary_stack: np.ndarray, output_dir: Path) -> bool:
    spacing = stack_metadata['spacing_mm']
    if any(v == 0 for v in spacing.values()):
        affine = np.diag([0.01, 0.01, 0.01, 1.0])
        print("[WARN]: Fallback values used for pixel spacing!")
    else:
        affine = np.diag([spacing['x'], spacing['y'], spacing['z'], 1.0])

    nii_stack = nib.nifti1.Nifti1Image(stack.astype(np.float32), affine)
    nii_binary = nib.nifti1.Nifti1Image(binary_stack.astype(np.uint8), affine)

    # metadaten für nifti header
    model = stack_metadata['instrument']['model']
    wl = stack_metadata['instrument']['central_wavelength']
    timestamp = stack_metadata['timestamp']
    descrip = f"{model}_{wl:.0f}nm_{timestamp}"

    nii_stack.header['descrip'] = descrip[:80]
    nii_binary.header['descrip'] = descrip[:80]

    # speichern
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        nib.save(nii_stack, output_dir / f"{stack_metadata['filename']}.nii.gz") # type: ignore
        nib.save(nii_binary, output_dir / f"{stack_metadata['filename']}_mask.nii.gz") # type: ignore
        return True
    except Exception as e:
        show_error(f"Failed to save NIfTI files: {e}")
        return False



# Labeling-Functions
## processing functions
def median_blur(stack: np.ndarray, filter_size: int) -> np.ndarray:
    return scipy.ndimage.median_filter(stack, size=(1, filter_size, filter_size)) # filterplane=2D (xz), not filtering depth (y) since it's anistropic to xz

def roi_filter(stack: np.ndarray, roi_width: int) -> np.ndarray:
    return scipy.ndimage.uniform_filter1d(stack, roi_width, axis=2, mode='reflect')

def roi_filter_2D(stack: np.ndarray, roi_size: int) -> np.ndarray:
    return scipy.ndimage.uniform_filter(stack, size=(roi_size, roi_size), axes=(0, 2), mode='reflect') # type: ignore

def locate_window(stack: np.ndarray, ymin: int, ymax: int, y_offset: int) -> np.ndarray:
    y_coords = np.argmax(stack[:, ymin:ymax, :], axis=1)
    y_coords += y_offset

    return y_coords

def zero_out_window(stack: np.ndarray, window_coords: np.ndarray) -> np.ndarray:
    yy = np.arange(stack.shape[1])  # Create a range for y-coordinates
    yy = yy.reshape(1, -1, 1)  # Reshape to ensure it can be broadcasted
    copy = stack.copy()  # Create a copy of the image to avoid modifying the original
    copy[yy < window_coords[:, np.newaxis, :]] = 0 # Set pixels above the window to zero
    return copy

def locate_substratum(stack: np.ndarray, ymin: int, ymax: int, y_offset: int) -> np.ndarray:
    y_coords = np.argmax(stack[:, ymin:ymax, :], axis=1)
    y_coords = y_coords + ymin + y_offset

    return y_coords

def zero_out_substratum(stack: np.ndarray, substratum_coords: np.ndarray) -> np.ndarray:
    yy = np.arange(stack.shape[1])  # Create a range for y-coordinates
    yy = yy.reshape(1, -1, 1)  # Reshape to ensure it can be broadcasted
    copy = stack.copy()  # Create a copy of the image to avoid modifying the original
    copy[yy >= substratum_coords[:, np.newaxis, :]] = 0  # Set pixels below the substratum to zero
    return copy

def increase_contrast(stack: np.ndarray, percentile: float) -> np.ndarray:
    nonzero_values = stack[stack > 0]  # Extract non-zero values
    min_val = np.percentile(nonzero_values, percentile)  # Find the 1st percentile without zeros
    max_val = np.percentile(stack, 100 - percentile) 
    if max_val == min_val:
        show_info("Image has no contrast to enhance.")
        return stack

    contrast_enhanced = np.clip(((stack - min_val) / (max_val - min_val)), 0, 1)
    return contrast_enhanced

def plot_histograms(original: np.ndarray, new: np.ndarray, percentile: float):
    plt.figure(figsize=(12, 6))

    plt.subplot(1, 2, 1)
    plt.hist(original.ravel(), bins=256, range=(0, 1), color='blue', alpha=0.7, log = True)
    plt.title('Original image histogram')
    plt.xlabel('Pixel intensity')
    plt.ylabel('Pixel amount')

    plt.subplot(1, 2, 2)
    plt.hist(new.ravel(), bins=256, range=(0, 1), color='green', alpha=0.7, log = True)
    plt.title(f'Contrast enhanced image histogram with percentile {percentile}') 
    plt.xlabel('Pixel intensity')
    plt.ylabel('Pixel amount')
    plt.show()

def get_threshold(stack: np.ndarray):
    """
    Create a binary mask from an image stack, ignoring zero pixels.
    """

    nonzero_values = stack[stack > 0]  # Extract non-zero values

    thresh = filters.threshold_triangle(nonzero_values)  # Use triangle thresholding on non-zero values

    return thresh

def rm_outliers(stack: np.ndarray, size: int) -> np.ndarray:
    bool_stack = stack.astype(bool)

    stack_transformed = morphology.remove_small_objects(bool_stack, size, connectivity=1)

    stack = stack_transformed.astype(np.uint8)

    return stack
