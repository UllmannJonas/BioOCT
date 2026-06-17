from enum import StrEnum


# registry function names to avoid typos
class Fn(StrEnum):
    CONVERT_TO_8BIT = "convert_to_8bit"
    MEDIAN_FILTER = "median_filter"


# pipeline placeholders
BASE_LAYER_PLACEHOLDER = "$base"
SOURCE_DIR_PLACEHOLDER = "$source_dir"
LAYER_NAME_PLACEHOLDER = "$layer_name"
