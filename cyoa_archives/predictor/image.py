import csv
import math
import logging
import pathlib
from typing import Dict, List, Any
from collections import namedtuple

import cv2
import numpy as np
import pytesseract

from .cv import CvChunk
from ..util.functions import calc_intersect

logger = logging.getLogger(__name__)

BBoxTuple = namedtuple('BBoxTuple', ['xmin', 'xmax', 'ymin', 'ymax'])


class CyoaImage:
    """Represents a CYOA image; loaded from disk."""

    def __init__(self, file_path: pathlib.Path):

        # Check if file exists

        self.file_path = file_path
        self.cv = cv2.imread(str(file_path.resolve()))
        self.height = self.cv.shape[0]
        self.width = self.cv.shape[1]

        logger.debug(f'File path: {file_path.resolve()}')
        logger.debug(f'Image Dimensions: {self.height} x {self.width}')

    def as_chunk(self):
        """Return the CYOA Image as a CvChunk object for processing."""
        return CvChunk(
            cv=self.cv,
            x=0,
            y=0
        )


    def get_text(self):
        # We perform tesseract ocr on section chunks, after restoring to the original size
        all_text = []
        for section in self.chunks:
            ystart = int(section.ymin / self.scale)
            yend = int((section.ymin + section.height) / self.scale)
            xstart = int(section.xmin / self.scale)
            xend = int((section.xmin + section.width) / self.scale)
            roi = self.original_cv[ystart:yend, xstart:xend]

            # Make roi even larger for better results
            roi = cv2.resize(roi, (roi.shape[0] * 2, roi.shape[1] * 2), interpolation=cv2.INTER_AREA)
            roi = self.preprocess_image(roi, kernel_size=7)

            # Run tesseract
            bboxes = []
            text = []
            data = pytesseract.image_to_data(roi)
            reader = csv.reader(data.splitlines(), delimiter='\t')
            next(reader)
            last_block = 0
            for row in reader:
                conf = float(row[10])
                block = int(row[2])
                if block != last_block:
                    # This is a bounding box for a whole block fo text
                    bbox = BBoxTuple(
                        left=int(row[6]),
                        top=int(row[7]),
                        width=int(row[8]),
                        height=int(row[9])
                    )
                    bboxes.append(bbox)
                    text.append('\n')
                if conf > 0:
                    text.append(row[11])
                last_block = block
            section.text = ' '.join(text)
            section.bboxes = bboxes
            all_text.extend(text)
        return ' '.join(all_text)
