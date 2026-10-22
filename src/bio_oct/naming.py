OUTPUT_LAYER_SUFFIXES = (
    "median",
    "gauss",
    "sobel",
    "enhanced",
    "cleaned",
    "interpolated",
    "zeroed",
    "reflection_removed",
    "untilted",
    "roi",
    "binary",
    "surface-coords",
)


def derive_name(input_name: str, suffix: str) -> str:
    if input_name.endswith(f"_{suffix}"):
        return input_name
    return f"{input_name}_{suffix}"
