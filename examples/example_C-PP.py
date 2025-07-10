import glob
import os

import numpy as np

from oct_analysis.octools import processing_functions as oct

input_folder = oct.select_tiff_folder()
output_folder = oct.select_tiff_folder()
tiff_files = glob.glob(os.path.join(input_folder, '*.tif'))

# Define headers and data
headers = [
    "Filename",
    "Slices",
    "Height (px)",
    "Width (px)",
    "X Voxel Size (mm/px)",
    "Y Voxel Size (mm/px)",
    "Z Voxel Size (mm/px)",
    "Image Area (mm²)",
    "Biovolume (mm³)",
    "Min Thickness (mm)",
    "Mean Thickness (mm)",
    "Max Thickness (mm)",
    "Std Thickness (mm)",
    "Surface Coverage (%)",
    "Mean Arithmetic Roughness (Ra)",
    "Std Arithmetic Roughness (Ra)",
    "Mean RMS Roughness (Rq)",
    "Std RMS Roughness (Rq)",
    "Mean Roughness Coefficient",
    "Std Roughness Coefficient",
    "Mean Porosity",
    "Std Porosity"
]

# This example file is for the C-PP example image

for input_filename in tiff_files:
    img, filename, metadata = oct.read_tiff(input_filename)
    img = oct.convert_to_8bit(img)
    slices, h, w =img.shape
    img = oct.untilt(img, thres=195, y_offset=6, top_crop=30) # Remove black area beneath substratum
    oct.save_tiff(img, output_folder, filename, metadata=metadata)

    # Create a binary mask of the image
    img_binary_raw = oct.binary_mask(
        img,
        thresholding_method='otsu',
        contrast=0.35,
        blurred=False,
        blur_size=0,
        outliers_size=0
    )
    img_binary_blurred = oct.binary_mask(
        img,
        thresholding_method='otsu',
        contrast=0.35,
        blurred=True,
        blur_size=5,
        outliers_size=5
    )
    img_binary_difference = (
        np.clip(img_binary_blurred.astype(np.int16) - img_binary_raw.astype(np.int16), 0, 255).astype(np.uint8)
    )
    img_binary = (
        np.clip(img_binary_blurred.astype(np.int16) - img_binary_difference.astype(np.int16), 0, 255).astype(np.uint8)
    )

    oct.save_tiff(img_binary, output_folder, f"{filename}_binary", metadata=metadata)


    # post-processing
    # get dimensions of the image
    slices, height, width = img_binary.shape
    x_resolution = metadata.get('XResolution', 1.0)  # pixels per mm
    y_resolution = metadata.get('YResolution', 1.0)  # pixels per mm
    x_voxel_size = round((x_resolution[1]/x_resolution[0]), 4)   # mm/px
    y_voxel_size = round((y_resolution[1]/y_resolution[0]), 4)   # mm/px
    z_voxel_size = round(metadata.get('spacing', 1.0), 4)
    image_area = slices*z_voxel_size*width*x_voxel_size # mm^2
    # Calculate volume of the biofilm
    biovolume = oct.voxel_count(img_binary, voxel_size=(z_voxel_size, y_voxel_size, x_voxel_size))
    # Calculate height map (thickness map) of the biofilm
    height_map, min_thickness, mean_thickness, max_thickness, std_thickness, substratum_coverage = (
        oct.generate_Height_Map(
            img_binary,
            voxel_size=(z_voxel_size, y_voxel_size, x_voxel_size),
            filename=filename,
            output_folder=output_folder,
            vmin=0,
            vmax=0.5
        )
    )
    # Calculate biovolume map of the biofilm
    (
        B_map,
        min_thickness_B,
        mean_thickness_B_map,
        max_thickness_B_map,
        std_thickness_B_map,
        substratum_coverage_B_map
    ) = (
        oct.generate_B_Map(
            img_binary,
            voxel_size=(z_voxel_size, y_voxel_size, x_voxel_size),
            filename=filename,
            output_folder=output_folder,
            vmin=0,
            vmax=0.5
        )
    )
    # Calculate roughness of the biofilm
    results = oct.calculate_roughness(img_binary, voxel_size=(z_voxel_size, y_voxel_size, x_voxel_size), threshold=0)
    (
        mean_arithmetic_roughness,
        std_arithmetric_roughness,
        mean_rms_roughness,
        std_rms_roughness,
        mean_roughness_coeff,
        std_roughness_coeff
    ) = results
    # Calculate porosity of the biofilm
    mean_porosity, std_porosity = oct.calculate_porosity(img_binary, threshold=0)


    # Save results to CSV
    data = [
    filename,
    slices,
    height,
    width,
    x_voxel_size,
    y_voxel_size,
    z_voxel_size,
    image_area,
    biovolume,
    min_thickness,
    mean_thickness,
    max_thickness,
    std_thickness,
    substratum_coverage,
    mean_arithmetic_roughness,
    std_arithmetric_roughness,
    mean_rms_roughness,
    std_rms_roughness,
    mean_roughness_coeff,
    std_roughness_coeff,
    mean_porosity,
    std_porosity
    ]
    oct.save_results_to_csv(output_folder, headers, data)
