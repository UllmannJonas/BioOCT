"""
OCTViewer - A simple viewer for Thorlabs Optical Coherence Tomography (OCT) data.

It reads OCT data directly from the .oct file and visualizes the intensity data slice by slice in a loop.
Press SPACE to pause and any key to continue, or ESC to exit.

Build OCTViewer.exe with PyInstaller:
    cd src/octviewer
    pyinstaller --onefile -n OCTViewer_v2 octviewer.py
"""

import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import sys
import cv2
import time
from collections import deque

def main():
    filepath = Path(sys.argv[1])
    intensity, video = read_oct(filepath)
    display_oct(intensity, video)
###


def read_oct(filepath: Path) -> tuple[np.ndarray, np.ndarray]:

    with zipfile.ZipFile(filepath, 'r') as z:
        items = z.namelist()

        for item in items:
            if "xml" in item:
                header = item
            elif "Intensity" in item:
                intensity = item
            elif "Video" in item:
                videoimg = item

        # get metadata
        with z.open(header) as xmlf:
            root = ET.parse(xmlf).getroot()
            # get VideoImage data shape
            for df in root.iter("DataFile"):
                if "VideoImage" in df.text:
                    videoimg_width = int(df.attrib["SizeZ"])
                    videoimg_height = int(df.attrib["SizeX"])
                    videoformat = True
                    break
                else:
                    videoformat = False
        
            # get Intensity data shape
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

        # reformat video image into np.ndarray
        with z.open(videoimg) as f:
            videoimg_raw = f.read()
        if videoformat:
            shape = (videoimg_height, videoimg_width, 4)  # 4 channels (RGBA)
            videoimg = np.frombuffer(videoimg_raw, dtype=np.uint8).copy().reshape(shape)
        else:
            videoimg = np.zeros((videoimg_height, videoimg_width, 4), dtype=np.uint8)


    return intensity_data, videoimg

def display_oct(intensity_data: np.ndarray, video_image: np.ndarray = None) -> None:
        # Display Video Image if available
        if video_image.min() == video_image.max() == 0:
            cv2.putText(
                video_image,
                "Error getting VideoImage data.",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 255, 255),
                2,
                cv2.LINE_AA
            )
        else:
            cv2.imshow("OCT Viewer - Videoimage", video_image)
        
        
        # Display Intensity Data
        slice_axis = "y" # default: side-view
        i = 0
        delay = int(1000 / 120)  #=8.33. Start with 120(-rendering time = 60) FPS
        MAX_DELAY = 256
        show_help = False
        help_text = "SPACE to pause, +/- to change speed, ESC to exit, TAB to reslice ZX <-> YX, h to toggle help"

        cv2.namedWindow("OCT Viewer")
        fps_window = deque(maxlen=30)

        while True:
            t0 = time.perf_counter()

            if slice_axis == "y":
                slice = intensity_data[i, :, :].copy() # Y-Achse: ZX-Slice
                n_slices = intensity_data.shape[0]
            else:
                slice = intensity_data[:, i, :].copy() # Z-Achse: YX-Slice
                n_slices = intensity_data.shape[1]

            if show_help:
                slice = cv2.cvtColor(slice, cv2.COLOR_GRAY2BGR)
                y0, dy = 25, 25
                for j, line in enumerate(help_text.split(", ")):
                    y = y0 + j * dy
                    cv2.putText(
                        slice,
                        line,
                        (10, y),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 0, 0),
                        1,
                        cv2.LINE_AA
                    )
            cv2.imshow("OCT Viewer", slice)


            key = cv2.waitKey(delay)  # wait for the calculated delay
            if key == 32:  # SPACE = pause
                cv2.waitKey(0)  # wait for any key to continue
            elif key == ord('h'):  # 'h' = toggle help
                show_help = not show_help
            elif key == ord('+'):  # '+' = increase speed
                delay = max(8, delay // 2)
            elif key == ord('-'):  # '-' = decrease speed
                delay = min(MAX_DELAY, delay * 2)
            elif key == 9: # TAB to reslice
                if slice_axis == "y":
                    slice_axis = "z"
                    i = 0
                else:
                    slice_axis = "y"
                    i = 0
            elif key == 27:  # ESC = abbrechen
                break

            frame_time = time.perf_counter() - t0
            fps_window.append(1 / frame_time if frame_time > 0 else 0)
            avg_fps = sum(fps_window) / len(fps_window)

            text = f"OCT Viewer | Slice {i+1}/{n_slices} | {avg_fps:.1f} FPS || 'h' = Help"
            cv2.setWindowTitle(
                "OCT Viewer",
                text
            )
        
            i = (i + 1) % n_slices

        
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
