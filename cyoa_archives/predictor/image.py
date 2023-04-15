
import logging
import pathlib
from typing import Optional, Dict, List, Any

import cv2
import numpy as np

from .roi import CyoaROI
from .ocr import KerasOCR

logger = logging.getLogger(__name__)

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
        self.cv = cv2.imread(str(file_path.resolve()))
        self.height = self.cv.shape[0]
        self.width = self.cv.shape[1]
        self.resize_image()
        self.rois = self.generate_rois()

        # 3. Feed ROIs to OCR
        self.get_ocr_text()

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
                self.cv = cv2.resize(self.cv, dim, interpolation=cv2.INTER_AREA)
                self.height = self.cv.shape[0]
                self.width = self.cv.shape[1]
        return None

    def generate_rois(self, size: Optional[int] = None) -> List[CyoaROI]:
        input_size = size if size else self.CONFIG.get('input_size')
        sliding_step = int(input_size * 3 / 4)
        rois: List[CyoaROI] = []
        for y in range(0, self.height - sliding_step, sliding_step):
            for x in range(0, self.width - sliding_step, sliding_step):
                y2 = y + input_size if (y + input_size < self.height) else self.height
                x2 = x + input_size if (x + input_size < self.width) else self.width
                roi = self.cv[y:y2, x:x2]
                # roi = cv2.resize(roi, input_size)
                croi = CyoaROI(roi, x, y, input_size, self.file_path)
                rois.append(croi)
        return rois

    def get_ocr_text(self):
        text = KerasOCR.read_rois(self.rois)
        return text
