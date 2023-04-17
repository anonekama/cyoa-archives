import csv
import logging
import pathlib
from typing import Optional, Dict, List, Any
from collections import namedtuple

import cv2
import numpy as np
import pytesseract

from .cv import CvChunk

logger = logging.getLogger(__name__)

BBoxTuple = namedtuple('BBoxTuple', ['xmin', 'xmax', 'ymin', 'ymax'])


class CyoaImage:
    """Represents a CYOA image; loaded from disk."""

    # Class variable storing configuration
    CONFIG = None

    def __init__(self, file_path: pathlib.Path):

        # Check if file exists

        self.file_path = file_path
        self.cv = cv2.imread(str(file_path.resolve()))
        self.height = self.cv.shape[0]
        self.width = self.cv.shape[1]
        self.bboxes = None

        logger.debug(f'File path: {file_path.resolve()}')
        logger.debug(f'Image Dimensions: {self.height} x {self.width}')

        # Resize and preprocess image
        # self.resize_image(width=1200)
        # self.cv = self.preprocess_image(self.cv, kernel_size=7)

        # Make section chunks
        # self.make_section_chunks()

    @classmethod
    def load_config(cls, config_object: Dict[str, Any]) -> None:
        cls.CONFIG = config_object

    def get_text_bboxes(self):
        # Run tesseract on the whole image
        # We want bounding boxes to guide segmentation later

        # First we transform image for tesseract
        scale = 2
        resize = cv2.resize(self.cv, (self.width * scale, self.height * scale), interpolation=cv2.INTER_AREA)
        blur = cv2.medianBlur(resize, 3)

        # Run tesseract
        logger.info(f'Starting tesseract...')
        d = pytesseract.image_to_data(blur, output_type=pytesseract.Output.DICT)
        logger.info(f'Finished tesseract. Found {len(d["level"])} words.')

        # We are interested in level 2 boundaries
        # But some level 2 boundaries are empty, so make sure to exclude those
        bboxes = []
        buffer = None
        for i in range(len(d['level'])):
            level = d['level'][i]
            text = d['text'][i]
            if level == 2:
                buffer = BBoxTuple(
                    xmin=int(d['left'][i] / scale),
                    xmax=int((d['left'][i] + d['width'][i]) / scale),
                    ymin=int(d['top'][i] / scale),
                    ymax=int((d['top'][i] + d['height'][i]) / scale)
                )
            if buffer is not None and len(text.strip()):
                bboxes.append(buffer)
                buffer = None
        self.bboxes = bboxes
        return bboxes


    def chunk_image(self, max_cols: int):
        main_image = CvChunk(self.cv, x=0, y=0)

        # Perform row chunks first
        # We are looking for greedy chunking, small minimums
        row_min_size = self.width * 0.02  # 600 px minimum height per section
        line_thickness = self.width * 0.002  # 0.3% of the image width
        margin = self.width * 0.025
        row_chunks = main_image.generate_subchunks(row_min_size, line_thickness, axis=1, margin=margin, bboxes=self.bboxes)

        # Next, perform column chunks for each row chunk
        # We do not include text bboxes for column chunks because I find that ocr is inaccurate
        all_chunks = []
        for chunk in row_chunks:
            col_min_size = self.width / max_cols
            col_chunks = chunk.generate_subchunks(col_min_size, line_thickness, axis=0, bboxes=self.bboxes)
            all_chunks.extend(col_chunks)
        return all_chunks


    def get_text(self):
        # We perform tesseract ocr on section chunks, after restoring to the original size
        all_text = []
        for section in self.chunks:
            ystart = int(section.y / self.scale)
            yend = int((section.y + section.height) / self.scale)
            xstart = int(section.x / self.scale)
            xend = int((section.x + section.width) / self.scale)
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

    def make_section_chunks(self):
        """We make chunks out of large sections for OCR."""
        main_image = CvChunk(self.cv, x=0, y=0)

        # We allow a minimum section size of a 1:2 aspect ratio with respect to the CYOA width
        min_size = self.width / 2  # 600 px minimum height per section
        line_thickness = 4  # 0.3% of the image width
        margin = 30  # 2.5% of the image width on the borders
        self.chunks = main_image.generate_subchunks(min_size, line_thickness, axis=1, margin=margin)


    def resize_image(self, width) -> None:
        """Resize input image to a uniform size comparable for all CYOAs in a project."""
        max_width = width
        if self.original_width > max_width:
            self.scale = max_width / self.original_width
            dim = (int(self.original_width * self.scale), int(self.original_height * self.scale))
            self.cv = cv2.resize(self.original_cv, dim, interpolation=cv2.INTER_AREA)
            self.height = self.cv.shape[0]
            self.width = self.cv.shape[1]
        else:
            self.cv = self.original_cv
            self.height = self.original_height
            self.width = self.original_width
        logger.debug(f'Resized image: {self.height} {self.width}')
        return None

    @classmethod
    def preprocess_image(cls, cv, kernel_size: int):
        gray = cv2.cvtColor(cv, cv2.COLOR_BGR2GRAY)
        return cv2.GaussianBlur(gray, (kernel_size, kernel_size), 0)
