import logging
import numpy
from typing import List, Dict

import cv2
import keras_ocr

from .roi import CyoaROI, BoundingBox, Chunk

logger = logging.getLogger(__name__)

class KerasOCR:
    """Given a list of ROIs, fetch the text"""

    PIPELINE = keras_ocr.pipeline.Pipeline()
    img_xmax = None
    img_ymax = None
    cv = None

    @classmethod
    def set_image_dim(cls, x, y, cv):
        cls.img_xmax = x
        cls.img_ymax = y
        cls.cv =cv
        BoundingBox.set_image_dim(x, y)
        Chunk.set_image_dim(x, y)

    @classmethod
    def read_rois(cls, rois: List[CyoaROI], padding_factor: float = 1):
        """Read a list of ROIs, stitch together, and get text in a natural order.

        :param rois: A list of ROIs (cv images)
        :param padding_factor: How many character units to pad each bounding box
        :return:
        """
        # First, we get a list of all bounding boxes in all ROIs
        all_bounding_boxes = []
        for i, roi in enumerate(rois[0:21]):
            roi_boxes = cls.read_roi(roi)
            logger.info(f'Detected {len(roi_boxes)} words in {i}/{len(rois)} rois.')
            all_bounding_boxes.extend(roi_boxes)
        logger.info(f'Read a total of {len(all_bounding_boxes)} detections.')

        # Sort the bounding boxes on the yaxis
        all_bboxes = sorted(all_bounding_boxes, key=lambda b: b.ymin)

        # Now, we chunk ROIs, after expanding each bounding box by a factor
        chunks = cls.chunk_rois(all_bboxes, 1)

        # Lets print the chunks for debuging purposes
        logger.info(f'Chunks: {len(chunks)}')
        for i, chunk in enumerate(chunks):
            cv = cls.cv[chunk.ymin:chunk.ymax, chunk.xmin:chunk.xmax]
            cv2.imwrite(f'chunk_{i}.jpg', cv)

        # Perform non-maxima suppression to remove overlapping bounding boxes
        # Also print to text
        for chunk in sorted(chunks, key=lambda c: c.get_distance()):
            #logger.info(f'BEFORE: {len(chunk.boxes)}')
            # Perform suppression on bounding boxes
            logger.info(chunk.to_string())
            chunk.boxes = cls.nonmaxima_suppression(chunk.boxes, 0.7)
            # logger.info(f'AFTER: {len(bboxes)}')
            logger.info(chunk.to_string())


    @classmethod
    def read_roi(cls, roi: CyoaROI) -> List[BoundingBox]:
        """Runs Keras OCR on a single ROI image.

        :param roi: A CyoaROI object representing a CV2 ROI image.
        :return: A list of BoundingBox's representing text and coordinates
        """
        # Perform keras ocr inference
        read_image = keras_ocr.tools.read(roi.roi)
        predictions = cls.PIPELINE.recognize([read_image])

        bounding_boxes = []
        for group in predictions[0]:
            text = group[0]
            if len(text):
                top_left_x, top_left_y = group[1][0]
                bottom_right_x, bottom_right_y = group[1][1]
                bbox = BoundingBox(
                    text=text,
                    roi_x=roi.x,
                    roi_y=roi.y,
                    xmin=top_left_x,
                    xmax=bottom_right_x,
                    ymin=bottom_right_y,
                    ymax=top_left_y
                )
                if bbox.is_valid():
                    bounding_boxes.append(bbox)

        return bounding_boxes

    @classmethod
    def chunk_rois(cls, rois: List[BoundingBox], padding_factor: float) -> List[Chunk]:
        """Given a list of bounding boxes, make a union of all intersecting boxes.

        The padding factor is a value to multiply char_length units by.
        Since characters are taller than they are wide, define an arbitrary height-width
        radio (e.g. 0.7) so that the padding is greater on the y-axis.

        """
        chunks = []
        queue = []

        # First, we add all rois to the queue and convert to a chunk datatype
        # We also compute the median char_length
        char_length = []
        for roi in rois:
            char_length.append(roi.len_char)
            chunk = Chunk.from_bbox(roi)
            if chunk.is_valid():
                queue.append(chunk)
        median_char_width = numpy.median(char_length)
        logger.info(f'Char-Len: {median_char_width}')
        logger.info(f'Starting with: {len(queue)} queue')

        # Pad all chunks and transform so that the padding is greater on the y-axis
        pad_x = int(median_char_width * padding_factor)
        pad_y = int(median_char_width * padding_factor / 0.7)
        logger.info(f'Padding: {pad_x} {pad_y}')
        for item in queue:
            item.pad_xy(pad_x, pad_y)

        # We loop through the queue until it is empty
        while len(queue) > 0:
            this_item = queue[0]
            queue_end = queue[1:]
            # logger.info(f'Queue Length: {queue_end}')

            # Break loop on last item
            if len(queue_end) == 0:
                chunks.append(this_item)
                logger.info(f'Chunk: {(this_item.xmax - this_item.xmin)} x {(this_item.ymax - this_item.ymin)}')
                break

            intersect_set = Chunk.intersect_set(this_item, queue_end)
            overlap_list_idx = numpy.where(intersect_set)[0]
            remainder_list_idx = numpy.where(~intersect_set)[0]
            logger.info(f'Chunks: {len(chunks)} - Before: {len(queue_end)} - Overlap: {len(overlap_list_idx)} - Remainder: {len(remainder_list_idx)}')

            # If there are any matches by intersection...
            if len(overlap_list_idx) > 0:

                overlap_list = []
                for i in overlap_list_idx:
                    overlap_list.append(queue_end[i])

                # Create a union of the intersecting chunks
                # logger.info(overlap_list)
                union = Chunk.union(overlap_list)
                logger.info(f'Union: {(union.xmax - union.xmin)} x {(union.ymax - union.ymin)}')

                # Put the chunk back into the remaining queue
                remainder_list = []
                for i in remainder_list_idx:
                    remainder_list.append(queue_end[i])
                remainder_list.append(union)

                # Reset the queue
                queue = remainder_list

            # If there are no matches, we report it as a distinct chunk
            else:
                chunks.append(this_item)
                logger.info(f'Chunk: {(this_item.xmax - this_item.xmin)} x {(this_item.ymax - this_item.ymin)}')
                queue = queue_end

        return chunks

    @classmethod
    def nonmaxima_suppression(cls, rois: List[BoundingBox], threshold=0.3):
        """Suppress all bounding boxes when they overlap, and they're the smaller of the two boxes.

        :param rois:
        :return:
        """
        keep_list = []
        queue = rois

        while len(queue) > 0:
            this_item = queue[0]
            queue_end = queue[1:]
            intersect_set = BoundingBox.intersect_set(this_item, queue_end, threshold)
            overlap_list_idx = numpy.where(intersect_set)[0]
            remainder_list_idx = numpy.where(~intersect_set)[0]

            # If there are any matches by intersection...
            if len(overlap_list_idx) > 0:

                overlap_list = []
                for i in overlap_list_idx:
                    overlap_list.append(queue_end[i])

                # Keep the largest intersecting BoundingBox
                keep = BoundingBox.get_max_area_bbox(this_item, overlap_list)

                # Put the largest back into the remaining queue
                remainder_list = []
                for i in remainder_list_idx:
                    remainder_list.append(queue_end[i])
                remainder_list.append(keep)

                # Reset the queue
                queue = remainder_list

            # If there are no matches, we report it as a distinct chunk
            else:
                keep_list.append(this_item)
                queue = queue_end

        return keep_list

