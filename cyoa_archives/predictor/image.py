import csv
import math
import logging
import pathlib
from typing import Dict, List, Any
from collections import namedtuple

import cv2

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

