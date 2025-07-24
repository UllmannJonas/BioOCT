"""
OCTViewer - A simple viewer for Thorlabs Optical Coherence Tomography (OCT) data.

It reads OCT data directly from the .oct file and visualizes the intensity data slice by slice in a loop.
Press SPACE to pause and any key to continue, or ESC to exit.

Build OCTViewer.exe with PyInstaller:
    cd src/octviewer
    pyinstaller --onefile -n OCTViewer octviewer.py
"""

import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import sys
import cv2

def main():
    filepath = Path(sys.argv[1])
    load_oct(filepath)
###


def load_oct(filepath: Path) -> None:

    with zipfile.ZipFile(filepath, 'r') as z:
        items = z.namelist()

        for item in items:
            if "xml" in item:
                header = item
            elif "Intensity" in item:
                intensity = item
            # elif "Video" in item:
            #     videoimg = item

        # get metadata
        with z.open(header) as xmlf:
            tree = ET.parse(xmlf)
            root = tree.getroot()
        
        def get(path, cast=str):
            element = root.find(path)
            return cast(element.text) if element is not None else 0
        
        px_z = get("Image/SizePixel/SizeZ", int)
        px_y = get("Image/SizePixel/SizeY", int)
        px_x = get("Image/SizePixel/SizeX", int)

        # reformat intensity.data into np.ndarray
        with z.open(intensity) as f:
            intensity_data_raw = f.read()
        shape = (px_y, px_x, px_z) # YXZ
        intensity_data = np.frombuffer(intensity_data_raw, dtype=np.float32).copy().reshape(shape)
        intensity_data = intensity_data.transpose(0, 2, 1)
        intensity_data -= intensity_data.min()
        intensity_data /= intensity_data.max()
        intensity_data *= 255
        intensity_data = intensity_data.astype(np.uint8)

        # TODO: need metadata from VideoImage first
        # with z.open(videoimg) as f:
        #     videoimage_raw = f.read()
        # shape = (meta['videoimg']['width'], meta['videoimg']['height'], 4) # 4 channels (RGBA)
        # video_image = np.frombuffer(videoimage_raw, dtype=np.uint8).reshape(shape)

        # visualize intensity data
        i = 0
        while True:
            slice = intensity_data[i, :, :]
            cv2.imshow("OCT Viewer", slice)

            key = cv2.waitKey(3) # 3 ms per frame
            if key == 32:  # SPACE = pause
                cv2.waitKey(0)  # wait for any key to continue
            elif key == 27:  # ESC = abbrechen
                break
        
            i = (i + 1) % px_y
        
        cv2.destroyAllWindows()
#

if __name__ == "__main__":
    main()
