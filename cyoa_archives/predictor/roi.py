import logging
import pathlib

import cv2

logger = logging.getLogger(__name__)

class CyoaROI:
    """Represents a region of interest (ROI) in a CYOA image."""

    def __init__(self, roi, x: int, y: int, size: int, cyoa_filepath: pathlib.Path):
        self.roi = roi
        self.x = x
        self.y = y
        self.size = size

        # Save ROI to file
        self.filename = str(pathlib.Path(cyoa_filepath.parent, cyoa_filepath.stem + f'_{x}_{y}.jpg'))
        logger.info(f'Writing to file: {self.filename}')
        cv2.imwrite(self.filename, self.roi)

    def ocr_text(self):
        pass

    def ocr_images(self):
        pass
