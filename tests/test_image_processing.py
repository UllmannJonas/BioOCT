"""
Tests for the image_processing module
"""

import os
import tempfile
from unittest import mock

import numpy as np
import pytest

from oct_analysis.octools.processing_functions import (
    binary_mask,
    calculate_porosity,
    calculate_roughness,
    convert_to_8bit,
    find_max_zero,
    find_substratum,
    generate_B_Map,
    generate_Height_Map,
    read_tiff,
    save_tiff,
    untilt,
    voxel_count,
)


def test_read_tiff_file_not_found():
    """Test that FileNotFoundError is raised when the file doesn't exist"""
    with mock.patch("os.path.isfile", return_value=False):
        with pytest.raises(FileNotFoundError):
            read_tiff("nonexistent_file.tiff")


def test_read_tiff_returns_expected_outputs():
    """Test that read_tiff returns the expected outputs with correct metadata"""
    fake_image = np.zeros((10, 20, 30), dtype=np.float32)
    fake_description = "slices=10\nunit=mm\nspacing=1.0"

    with mock.patch("os.path.isfile", return_value=True):
        with mock.patch("tifffile.TiffFile") as mock_tif:
            # Setup mock for image data
            mock_tif.return_value.__enter__.return_value.asarray.return_value = fake_image

            # Setup mock for metadata
            mock_page = mock.Mock()
            mock_page.tags = {
                'ImageDescription': mock.Mock(value=fake_description),
                'ImageLength': mock.Mock(value=20),
                'ImageWidth': mock.Mock(value=30),
                'XResolution': mock.Mock(value=(1,1)),
                'YResolution': mock.Mock(value=(1,1))
            }
            mock_tif.return_value.__enter__.return_value.pages = [mock_page]

            # Setup mock for series info
            mock_series = mock.Mock()
            mock_series.shape = (10, 20, 30)
            mock_series.dtype = np.float32
            mock_series.axes = 'ZYX'
            mock_tif.return_value.__enter__.return_value.series = [mock_series]

            img, filename, metadata = read_tiff("fake_file.tiff")

            # Test image output
            assert isinstance(img, np.ndarray)
            assert img.shape == (10, 20, 30)
            assert img.dtype == np.float32

            # Test filename output
            assert isinstance(filename, str)
            assert filename == "fake_file"

            # Test metadata output
            assert isinstance(metadata, dict)
            assert metadata['Z'] == 10
            assert metadata['Y'] == 20
            assert metadata['X'] == 30
            assert metadata['shape'] == (10, 20, 30)
            assert metadata['dtype'] == str(np.float32)
            assert metadata['axes'] == 'ZYX'
            assert metadata['XResolution'] == (1, 1)
            assert metadata['YResolution'] == (1, 1)
            assert metadata['unit'] == 'mm'
            assert metadata['spacing'] == 1.0


def test_read_tiff_error_on_none_image():
    """Test that ValueError is raised when image reading fails"""
    with mock.patch("os.path.isfile", return_value=True):
        with mock.patch("tifffile.TiffFile") as mock_tif:
            mock_tif.return_value.__enter__.return_value.asarray.return_value = None
            with pytest.raises(ValueError):
                read_tiff("invalid_image.tiff")


def test_save_tiff():
    """Test saving a TIFF file with metadata"""
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test image
        test_image = np.zeros((10, 20, 30), dtype=np.uint8)
        test_metadata = {
            'shape': (10, 20, 30),
            'dtype': 'uint8',
            'axes': 'ZYX'
        }

        # Save the image
        save_tiff(test_image, temp_dir, "test_image", test_metadata)

        # Verify the file was created
        expected_path = os.path.join(temp_dir, "test_image.tif")
        assert os.path.exists(expected_path)


def test_save_tiff_invalid_input():
    """Test that ValueError is raised for invalid input"""
    with pytest.raises(ValueError):
        save_tiff(np.zeros((10, 20)), "path", "filename")  # 2D array instead of 3D


def test_convert_to_8bit():
    """Test conversion of images to 8-bit format"""
    # Test with float input
    float_img = np.random.rand(10, 20).astype(np.float32)
    uint8_img = convert_to_8bit(float_img)
    assert uint8_img.dtype == np.uint8
    assert np.min(uint8_img) >= 0
    assert np.max(uint8_img) <= 255

    # Test with uint32 input
    uint32_img = np.random.randint(0, 1000, (10, 20), dtype=np.uint32)
    uint8_img = convert_to_8bit(uint32_img)
    assert uint8_img.dtype == np.uint8
    assert np.min(uint8_img) >= 0
    assert np.max(uint8_img) <= 255


def test_find_substratum():
    """Test substratum detection in image stack"""
    # Create a test image with a clear substratum
    test_img = np.zeros((5, 20, 30), dtype=np.uint8)
    test_img[:, 10:15, :] = 255  # Create a bright band in the middle

    result = find_substratum(test_img, start_x=0, y_max=10, roi_width=5, scan_height=2, step_width=5)

    assert isinstance(result, np.ndarray)
    assert result.shape == test_img.shape
    assert result.dtype == np.uint8


def test_find_substratum_invalid_input():
    """Test that ValueError is raised for invalid input"""
    with pytest.raises(ValueError):
        find_substratum(np.zeros((10, 20)), 0, 10, 5, 2, 5)  # 2D array instead of 3D


def test_find_max_zero():
    """Test finding maximum zero pixels and cropping"""
    # Create test image with known zero regions
    test_img = np.ones((5, 20, 30), dtype=np.uint8)
    test_img[:, :5, :] = 0  # First 5 rows are zero

    result = find_max_zero(test_img, top_crop=2)

    assert isinstance(result, np.ndarray)
    assert result.shape[1] == test_img.shape[1] - 7  # 5 zero rows + 2 crop rows
    assert result.dtype == np.uint8


def test_untilt():
    """Test untilting of image stack"""
    # Create a test image with a tilted pattern
    test_img = np.zeros((5, 20, 30), dtype=np.uint8)
    for i in range(min(20, 30)):  # Ensure i does not exceed the bounds
        test_img[:, i, i:i+5] = 255  # Create a diagonal pattern

    result = untilt(test_img, thres=1, y_offset=2, top_crop=1)

    assert isinstance(result, np.ndarray)
    assert result.dtype == np.uint8


def test_voxel_count():
    """Test voxel counting and volume calculation"""
    # Create test image with known number of white pixels
    test_img = np.zeros((5, 20, 30), dtype=np.uint8)
    test_img[:, 10:15, :] = 255  # 5x5x30 = 750 white pixels

    voxel_size = (0.1, 0.1, 0.1)  # 0.1mm per pixel
    volume = voxel_count(test_img, voxel_size)

    expected_volume = 750 * 0.1 * 0.1 * 0.1  # volume in mm³
    assert abs(volume - expected_volume) < 1e-10


def test_generate_Height_Map():
    """Test height map generation"""
    # Create test image
    test_img = np.zeros((5, 20, 30), dtype=np.uint8)
    test_img[2:, :, :] = 255  # Set bottom half to white

    with tempfile.TemporaryDirectory() as temp_dir:
        height_map, min_thickness, mean_thickness, max_thickness, std_thickness, coverage = generate_Height_Map(
            test_img, (0.1, 0.1, 0.1), "test", temp_dir, 0, 1
        )

        assert isinstance(height_map, np.ndarray)
        assert height_map.shape == (30, 5)  # After transpose and processing
        assert isinstance(min_thickness, float)
        assert isinstance(mean_thickness, float)
        assert isinstance(max_thickness, float)
        assert isinstance(std_thickness, float)
        assert isinstance(coverage, float)

        # Verify the output files were created
        assert os.path.exists(os.path.join(temp_dir, "test_HM.tiff"))
        assert os.path.exists(os.path.join(temp_dir, "test_HM.png"))


def test_generate_B_Map():
    """Test biovolume map generation"""
    # Create test image
    test_img = np.zeros((5, 20, 30), dtype=np.uint8)
    test_img[2:, :, :] = 255  # Set bottom half to white

    with tempfile.TemporaryDirectory() as temp_dir:
        b_map, min_thickness, mean_thickness, max_thickness, std_thickness, coverage = generate_B_Map(
            test_img, (0.1, 0.1, 0.1), "test", temp_dir, 0, 1
        )

        assert isinstance(b_map, np.ndarray)
        assert b_map.shape == (30, 5)  # After transpose and processing
        assert isinstance(min_thickness, float)
        assert isinstance(mean_thickness, float)
        assert isinstance(max_thickness, float)
        assert isinstance(std_thickness, float)
        assert isinstance(coverage, float)

        # Verify the output files were created
        assert os.path.exists(os.path.join(temp_dir, "test_BM.tiff"))
        assert os.path.exists(os.path.join(temp_dir, "test_BM.png"))


def test_calculate_roughness():
    """Test roughness calculation"""
    # Create test image with known surface profile
    test_img = np.zeros((5, 20, 30), dtype=np.uint8)
    test_img[2:, :, :] = 255  # Set bottom half to white

    roughness_metrics = calculate_roughness(test_img, (0.1, 0.1, 0.1))

    assert len(roughness_metrics) == 6
    assert all(isinstance(x, float) for x in roughness_metrics)


def test_calculate_porosity():
    """Test porosity calculation"""
    # Create test image with known porosity
    test_img = np.zeros((5, 20, 30), dtype=np.uint8)
    test_img[2:, :, :] = 255  # Set bottom half to white

    mean_porosity, std_porosity = calculate_porosity(test_img)

    assert isinstance(mean_porosity, float)
    assert isinstance(std_porosity, float)
    assert 0 <= mean_porosity <= 100
    assert 0 <= std_porosity <= 100


def test_binary_mask():
    """Test binary mask generation"""
    # Create test image
    test_img = np.zeros((5, 20, 30), dtype=np.uint8)
    test_img[2:, :, :] = 255  # Set bottom half to white

    result = binary_mask(test_img, 'otsu', 2, True, 5, 10)

    assert isinstance(result, np.ndarray)
    assert result.shape == test_img.shape
    assert result.dtype == np.uint8
    assert np.all(np.logical_or(result == 0, result == 255))
