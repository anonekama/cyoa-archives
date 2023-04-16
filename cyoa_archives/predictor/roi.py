import logging
import math
import numpy
import pathlib
from typing import TypeVar, List

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
        self.filename = str(pathlib.Path(cyoa_filepath.parent, cyoa_filepath.stem + f'_{y}_{x}.jpg'))
        logger.info(f'Writing to file: {self.filename}')
        cv2.imwrite(self.filename, self.roi)

    def ocr_text(self):
        pass

    def ocr_images(self):
        pass


class BoundingBox:
    char_hw_ratio = 1
    img_xmax = None
    img_ymax = None
    def __init__(self, text: str, roi_x: int, roi_y: int, xmin: float, xmax: float, ymin: float, ymax: float):
        input_ymin = roi_y + int(ymin if ymin > 0 else 0)
        input_ymax = roi_y + int(ymax if ymax > 0 else 0)

        self.text = text
        self.xmin = self.safe_set(roi_x + int(xmin if xmin > 0 else 0), max_value=self.img_xmax)
        self.xmax = self.safe_set(roi_x + int(xmax if xmax > 0 else 0), max_value=self.img_xmax)
        self.ymin = self.safe_set(int((input_ymin + input_ymax) / 2), max_value=self.img_ymax)
        self.len_char = (self.xmax - self.xmin) / len(text)
        self.yheight = self.len_char / self.char_hw_ratio
        self.ymax = self.safe_set(int(self.ymin + self.yheight), max_value=self.img_ymax)
        self.area = (self.xmax - self.xmin) * self.yheight

    @classmethod
    def set_image_dim(cls, x, y, char_hw_ratio=0.7):
        cls.img_xmax = x
        cls.img_ymax = y
        cls.char_hw_ratio = char_hw_ratio

    @classmethod
    def safe_set(cls, value: int, max_value: int):
        if value < 0:
            return 0
        if max_value and value > max_value:
            return max_value
        return value

    def is_valid(self):
        if self.xmax - self.xmin > 0 and self.ymax - self.ymin > 0:
            return True
        return False

    @classmethod
    def calc_intersect(cls, bbox_a, bbox_b) -> float:
        if bbox_a is None or bbox_b is None:
            return False
        area = 0
        dx = min(bbox_a.xmax, bbox_b.xmax) - max(bbox_a.xmin, bbox_b.xmin)
        dy = min(bbox_a.ymax, bbox_b.ymax) - max(bbox_a.ymin, bbox_b.ymin)
        if (dx > 0) and (dy > 0):
            return dx * dy / bbox_a.area
        return 0

    @classmethod
    def intersect_set(cls, bbox_a, bbox_list: List, threshold):
        intersect_list = numpy.zeros(len(bbox_list), dtype=bool)
        for i, bbox in enumerate(bbox_list):
            overlap = cls.calc_intersect(bbox_a, bbox)
            if overlap > threshold:
                intersect_list[i] = True
            else:
                intersect_list[i] = False
        return intersect_list

    @classmethod
    def get_max_area_bbox(cls, bbox_a, bbox_list: List):
        # Union from a list of Chunks
        top_bbox = bbox_a
        for bbox in bbox_list:
            if bbox.area > top_bbox.area:
                top_bbox = bbox
        return top_bbox

class Chunk:
    img_xmax = None
    img_ymax = None

    def __init__(self, boxes, xmin, xmax, ymin, ymax, line_height=10):
        self.boxes = boxes if boxes else []
        self.xmin = xmin
        self.xmax = xmax
        self.ymin = ymin
        self.ymax = ymax
        self.line_height = line_height

    @classmethod
    def set_image_dim(cls, x, y):
        cls.img_xmax = x
        cls.img_ymax = y

    @classmethod
    def from_bbox(cls, bbox: BoundingBox):
        return cls(
            boxes=[bbox],
            xmin=bbox.xmin,
            xmax=bbox.xmax,
            ymin=bbox.ymin,
            ymax=bbox.ymax
        )

    def pad_xy(self, pad_x, pad_y):
        self.xmin = self.safe_set(self.xmin - pad_x, max_value=self.img_xmax)
        self.xmax = self.safe_set(self.xmax + pad_x, max_value=self.img_xmax)
        self.ymin = self.safe_set(self.ymin - pad_y, max_value=self.img_ymax)
        self.ymax = self.safe_set(self.ymax + pad_y, max_value=self.img_ymax)
        self.line_height = pad_y

    def get_distance(self):
        return math.hypot((self.xmax - self.xmin) / 2, (self.ymax - self.ymin) / 2)

    def is_valid(self):
        if self.xmax - self.xmin > 0 and self.ymax - self.ymin > 0:
            return True
        return False

    @classmethod
    def safe_set(cls, value: int, max_value: int):
        if value < 0:
            return 0
        if max_value and value > max_value:
            return max_value
        return value

    @classmethod
    def is_intersect(cls, chunk_a, chunk_b):
        dx = min(chunk_a.xmax, chunk_b.xmax) - max(chunk_a.xmin, chunk_b.xmin)
        dy = min(chunk_a.ymax, chunk_b.ymax) - max(chunk_a.ymin, chunk_b.ymin)
        if (dx > 0) and (dy > 0):
            return True
        return False

    @classmethod
    def intersect_set(cls, chunk_a, chunk_list: List):
        intersect_list = numpy.zeros(len(chunk_list), dtype=bool)
        for i, chunk in enumerate(chunk_list):
            intersect_list[i] = cls.is_intersect(chunk_a, chunk)
        return intersect_list

    @classmethod
    def union(cls, chunk_list: List):
        # Union from a list of Chunks
        boxes = []
        xmin = []
        xmax = []
        ymin = []
        ymax = []
        for chunk in chunk_list:
            boxes = boxes + chunk.boxes
            xmin.append(chunk.xmin)
            xmax.append(chunk.xmax)
            ymin.append(chunk.ymin)
            ymax.append(chunk.ymax)
        return cls(
            boxes=boxes,
            xmin=min(xmin),
            xmax=max(xmax),
            ymin=min(ymin),
            ymax=max(ymax)
        )

    def to_string(self):
        # Sort the bounding boxes on the x-axis
        self.boxes = sorted(self.boxes, key=lambda b: b.xmin)
        queue = self.boxes

        """
        t = ""
        for box in queue:
            t = t + " " + box.text
        return t
        """

        # Iterate through the entire y-axis
        rows = []
        step_size = int(self.line_height)
        for y in range(self.ymin, self.ymax, step_size):
            this_row = []
            for i, bbox in enumerate(queue):
                if bbox.ymin <= y < bbox.ymax:
                    item = queue[0]
                    queue = queue[1:]
                    this_row.append(item.text)
            if len(this_row):
                rows.append(this_row)

        # Now print the rows
        text = ""
        for row in rows:
            for word in row:
                text = text + " " + word
        return text.strip()
