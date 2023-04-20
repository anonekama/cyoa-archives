import logging
import pathlib
import random
from typing import Dict, List, Any
from collections import namedtuple, OrderedDict

import cv2
import numpy as np
import pandas as pd

from .cv import CvChunk
from ..util.functions import calc_intersect

logger = logging.getLogger(__name__)

BBoxTuple = namedtuple('BBoxTuple', ['xmin', 'xmax', 'ymin', 'ymax'])


class CyoaImage:
    """Represents a CYOA image; loaded from disk."""

    def __init__(self, file_path: pathlib.Path):

        # Check if file exists
        logger.debug(f'File path: {file_path.resolve()}')

        self.file_path = file_path
        self.cv = cv2.imread(str(file_path.resolve()))
        self.height = self.cv.shape[0]
        self.width = self.cv.shape[1]
        self.area = self.height * self.width
        self.chunks = None


        logger.debug(f'Image Dimensions: {self.height} x {self.width}')

    def as_chunk(self):
        """Return the CYOA Image as a CvChunk object for processing."""
        return CvChunk(
            cv=self.cv,
            x=0,
            y=0
        )

    def make_chunks(self):
        # 1. Divide CYOA into large row sections
        min_size = self.width * 0.10  # Start with a 1:10 aspect ratio minimum
        line_thickness = self.width * 0.004  # For a 1200px image, this is 5px
        margin = 0.025  # For a 1200px image, this is a 30px margin
        section_chunks = self.as_chunk().generate_subchunks(
            min_size=min_size,
            line_thickness=line_thickness,
            margin=margin
        )

        # 2. Get bbox coordinates for text blocks.
        prelim_bbox_list = []
        for chunk in section_chunks:
            text_bboxes = chunk.get_text_bboxes(level=2, scale=2, minimum_conf=30)  # Text blocks
            prelim_bbox_list.extend(text_bboxes)

        # 3. Perform more aggressive horizontal chunks and use this for ocr
        row_chunks = []
        for chunk in section_chunks:
            chunks = chunk.generate_subchunks(
                min_size=25,
                line_thickness=10,
                margin=0.025,
                bboxes=prelim_bbox_list,
                greedy=False
            )
            row_chunks.extend(chunks)
        self.chunks = row_chunks

    def get_text(self):
        text = ""
        for chunk in self.chunks:
            row_text = chunk.get_text(scale=2, minimum_conf=70)
            text = text + " " + row_text
        return text

    def run_deepdanbooru(self, dd):
        bbox_list = []
        img_bbox_list = []
        for chunk in self.chunks:
            row_bboxes = chunk.get_text_bboxes(scale=2, level=4, minimum_conf=70)  # Line blocks
            bbox_list.extend(row_bboxes)

            # Next also generate image bboxes
            img_bboxes = chunk.get_image_bboxes(
                min_size=10,
                line_thickness=2,
                min_image_size=100,
                color_threshold=10000,
                n_recursions=4
            )
            img_bbox_list.extend(img_bboxes)

        # Run deepdanbooru
        result_dict = {}
        result_dict2 = {}
        for i, ibox in enumerate(img_bbox_list):
            img_crop = self.cv[ibox.ymin:ibox.ymax, ibox.xmin:ibox.xmax]
            img_dict = dd.evaluate(img_crop)

            iname = f'img_{i}'
            result_dict[iname] = img_dict
            result_dict2[iname] = img_dict.values()
            cv2.imwrite(f'img_{self.file_path.stem}_{i}.jpg', img_crop)

        # Loop through results once more
        tag_average = []
        for i, tag in enumerate(dd.tags):
            sum = 0
            for result in result_dict.values():
                sum = sum + result[tag]
            tag_average.append(sum / len(result_dict))

        result_dict2['keys'] = dd.tags
        result_dict2['avg'] = tag_average

        data = pd.DataFrame(result_dict2)
        data = data.sort_values(by=['avg'], ascending=False)
        data.to_csv(f'img_{self.file_path.stem}.csv')

    def run_deepdanbooru_random(self, dd, coverage=1):
        # Resize wide images to a standard width for comparability
        max_width = 1200
        if self.height > self.width > max_width:
            scale_percent = max_width / self.width
            dim = (int(self.width * scale_percent), int(self.height * scale_percent))
            cyoa_page = cv2.resize(self.cv, dim, interpolation=cv2.INTER_AREA)
        else:
            cyoa_page = self.cv

        (new_height, new_width) = cyoa_page.shape[:2]
        new_area = new_height * new_width

        # DD size is 512^2 = 262144
        iterations = coverage * new_area // 262144 + 1
        result_dict = OrderedDict()
        if new_width > 512 and new_height > 512:
            for i in range(iterations):
                # Make a random number
                xmax = new_width - 512
                ymax = new_height - 512
                randomx = random.randint(0, xmax)
                randomy = random.randint(0, ymax)

                # Slice the image by the random window
                random_slice = cyoa_page[randomy:randomy+512, randomx:randomx+512]

                # Run deepdanbooru
                img_dict = dd.evaluate(random_slice)
                for tag in img_dict:
                    if tag not in result_dict:
                        result_dict[tag] = [img_dict[tag]]
                    else:
                        result_dict[tag].append(img_dict[tag])

        return result_dict



