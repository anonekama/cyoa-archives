
import pathlib
from typing import Optional, Dict, Any

import cv2
import numpy as np

from .roi import CyoaROI

class CyoaImage:
    """Represents a CYOA image; loaded from disk."""

    # Class variable storing configuration
    CONFIG = None

    def __init__(self, file_path: pathlib.Path):

        # Assert config has essential values
        if 'max_width' not in self.CONFIG:
            raise ValueError(f'Please configure (max_width) attribute for image processing.')
        if 'input_size' not in self.CONFIG:
            raise ValueError(f'Please configure (input_size) attribute for image processing.')

        self.file_path = file_path
        self.cv2 = cv2.imread(str(file_path.resolve()))
        self.resize_image()
        self.height = self.cv2.shape[0]
        self.width = self.cv2.shape[1]

        self.rois = self.generate_rois()


        # max_width

        # Process image
        # 1. Resize image
        # 2. Generate ROIs
        # 3. Feed ROIs to OCR

    @classmethod
    def load_config(cls, config_object: Dict[str, Any]) -> None:
        cls.CONFIG = config_object

    def resize_image(self, width: Optional[int] = None, do_resize_wide: Optional[bool] = False) -> None:
        """Resize input image to a uniform size comparable for all CYOAs in a project."""
        max_width = width if width else self.CONFIG.get('max_width')
        if self.width > max_width:
            if not do_resize_wide or self.height > self.width:
                scale_percent = max_width / self.width
                dim = (int(self.width * scale_percent), int(self.height * scale_percent))
                self.cv2 = self.cv2.resize(self.cv2, dim, interpolation=cv2.INTER_AREA)
        return None

    def generate_rois(self, size: Optional[int] = None) -> None:
        input_size = size if size else self.CONFIG.get('input_size')
        sliding_step = int(input_size / 2)
        rois = []
        for y in range(0, self.height, sliding_step):
            for x in range(0, self.width, sliding_step):
                roi = CyoaROI(self, x, y, input_size)
                rois.append(roi)
        self.rois = rois
