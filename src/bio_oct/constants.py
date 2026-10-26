COLORMAP: dict[str, int] = {
    "Cyan": 2,
    "Yellow": 9,
    "Red": 10,
    "Blue": 34,
    "Green": 37,
    "Purple": 45,
}

TOOLTIPS: dict[str, dict[str, str]] = {
    "median": {
        "_widget": "Apply a 2D median filter to each B-scan to reduce noise while preserving edges.",
        "size": "Kernel size (odd). Larger values produce stronger smoothing.",
    },
    "gaussian": {
        "_widget": "Apply a Gaussian blur to reduce gaussian noise.",
        "sigma": "Standard deviation of Gaussian kernel. Higher values blur more.",
    },
    "sobel": {
        "_widget": "Compute axial image gradient (Sobel) to highlight lateral edges.",
        "image": "Input image layer to process.",
    },
    "contrast": {
        "_widget": "Adjust image contrast using gamma, clipping, or CLAHE methods.",
        "method": "Select contrast enhancement method.",
        "gamma": "Gamma value for nonlinear brightness adjustment.",
        "clip_low_percentile": "Lower histogram percentile to clip for contrast stretching.",
        "clip_high_percentile": "Upper histogram percentile to clip for contrast stretching.",
        "clahe_clip": "CLAHE clip limit; larger values increase local contrast but may amplify noise.",
        "clahe_tile": "Size of local regions for CLAHE. Smaller tiles increase local detail.",
    },
    "remove_outliers": {
        "_widget": "Remove connected components from a label image based on size threshold.",
        "size": "Maximum size of connected components (in pixels) to remove.",
    },
    "interpolate": {
        "_widget": "Interpolate gaps in located intensity coordinates.",
    },
    "zero_out": {
        "_widget": "Zero out (mask) areas above or below the labeled substratum.",
        "direction": "Choose whether to zero areas above or below the substratum labels.",
    },
    "replace_reflection": {
        "_widget": "Replace lateral reflection artifacts using nearby image context.",
        "offset": "Axial offset from reflection [px] to use for replacement values.",
        "padding": "Padding (thickness) used when replacing reflection regions.",
    },
    "untilt_widget": {
        "_widget": "Axially move substratum to bottom of the image.",
    },
    "export_to_tiff": {
        "_widget": "Export the given layer to a TIFF (.tiff) file in the source directory.",
        "image": "Layer to export.",
    },
    "export_to_nifti": {
        "_widget": "Export the given layer to a NIfTI (.nii.gz) file in the source directory.",
    },
    "h_map": {
        "_widget": "Create a height map (preview or save) from a binary label image.",
        "max_h": "Maximum height (µm) used for scaling the height map.",
        "preview": "When checked, only preview plot is shown instead of saving to file.",
    },
    "bv_map": {
        "_widget": "Create a biovolume map from a binary label image.",
        "max_h": "Maximum height (µm) used for scaling the height map.",
        "preview": "When checked, only preview plot is shown instead of saving to file.",
    },
    "save_metrics": {
        "_widget": "Calculate biofilm metrics based on a binary label image and save to CSV (.csv).",
    },
}

THRESHOLD_METHODS = ("otsu", "yen", "li", "mean", "isodata", "triangle", "manual")
