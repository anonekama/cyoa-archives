import logging
import math
from collections import namedtuple
from typing import Optional, List

import cv2
import numpy as np
import pytesseract

from ..util.functions import calc_intersect

logger = logging.getLogger(__name__)

BBoxTuple = namedtuple('BBoxTuple', ['xmin', 'xmax', 'ymin', 'ymax'])
ChunkTuple = namedtuple('ChunkTuple', ['start', 'end', 'delta'])


class CvChunk:

    def __init__(self, cv: np.ndarray, x: int, y: int):
        """Construct a Chunk object.

        :param cv: A slice from a loaded CV2 image.
        :param x: The absolute xmin coordinate (left).
        :param y: The absolute ymin coordinate (top).
        """
        self.cv = cv
        self.xmin = x
        self.ymin = y
        self.height = cv.shape[0]
        self.width = cv.shape[1]
        self.xmax = x + cv.shape[1]
        self.ymax = y + cv.shape[0]
        self.text = None
        self.text_bboxes = None
        self.tesseract = None

    def generate_subchunks(
            self,
            min_size: float,
            line_thickness: float,
            axis: int = 1,
            margin: int = 0,
            bboxes: List = None,
            greedy: bool = False
    ) -> List:
        """Divides a Chunk into smaller Chunks.

        Should Chunk should return itself if there are no further subchunks.

        :param min_size:
        :param line_thickness:
        :param axis:
        :param margin:
        :param bboxes:
        :param greedy:
        :return:
        """

        logger.debug('Starting to generate subchunk...')

        # If axis is 1, we make row chunks (horizontal lines)
        img_size = self.height if axis == 1 else self.width
        img_thickness = self.width if axis == 1 else self.height

        # If the Chunk is already too small return an empty list
        if img_size <= min_size:
            return []

        # If margin is set, we modify the image
        # TODO: Do not remove margin if it makes the image too small
        image = self.cv
        if margin:
            new_start = int(margin * img_thickness)
            new_end = int(img_thickness - margin * img_thickness)
            if axis == 1:
                image = image[0:img_size, new_start:new_end]
            else:
                image = image[new_start:new_end, 0:img_size]
            logger.debug(f'Image without margins: {image.shape[0]} {image.shape[1]}')

        # Apply Otsu's automatic thresholding
        threshold_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        (T, thresh) = cv2.threshold(threshold_image, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
        thresh_inv = 255 - thresh

        # Find continuous rows
        black_rows = np.where(~thresh.any(axis=axis))[0]
        white_rows = np.where(~thresh_inv.any(axis=axis))[0]
        all_rows = np.sort(np.append(black_rows, white_rows))
        logger.debug(f'Total Rows: {self.height} - AllBlack: {len(black_rows)} - AllWhite: {len(white_rows)}')

        # Get boundary proposals
        if greedy:
            logger.debug(f'Running greedy boundary proposals')
            boundary_proposals = self.get_boundaries(all_rows, line_thickness, axis=axis)
        else:
            boundary_proposals = self.get_boundaries_hierarchal(all_rows, min_size, line_thickness, axis=axis)

        # If boundary boxes are provided, then remove overlapping boundary proposals
        approved_proposals = []
        if bboxes:
            for i in boundary_proposals:
                good_boundary = True
                for bbox in bboxes:
                    intersection = calc_intersect(bbox.xmin, bbox.xmax, bbox.ymin, bbox.ymax,
                                                  self.xmin, self.xmax, self.ymin, self.ymax)
                    if intersection:
                        start = bbox.ymin - self.ymin if axis == 1 else bbox.xmin - self.xmin
                        end = bbox.ymax - self.ymin if axis == 1 else bbox.xmax - self.xmin
                        if start < i < end:
                            good_boundary = False
                            logger.debug(f'Bad boundary; {start} < {i} < {end}')
                if good_boundary:
                    approved_proposals.append(i)
        else:
            approved_proposals = boundary_proposals

        # Reduce boundaries
        boundaries = reduce_boundary_proposals(approved_proposals, min_size)
        chunks = get_subchunks(boundaries)

        logger.debug(f'Boundaries: {chunks}')
        chunk_list = []
        for i, chunk in enumerate(chunks):
            new_cv = self.cv[chunk.start:chunk.end, 0:self.width] if axis == 1 else self.cv[0:self.height,
                                                                                    chunk.start:chunk.end]
            new_chunk = CvChunk(
                cv=new_cv,
                x=self.xmin if axis == 1 else self.xmin + chunk.start,
                y=self.ymin + chunk.start if axis == 1 else self.ymin,
            )
            if new_chunk.is_valid():
                chunk_list.append(new_chunk)

        return chunk_list

    def get_boundaries(self, sorted_index_list, line_thickness: float, axis: int = 1):
        """We assume that index_list is sorted"""
        # The start of an image is always a boundary
        boundaries = [0]

        # First we add all continuous 1-pixel boundaries to a list
        continuous_row_list = []
        continuous_row = []
        last_item = -1
        for i in sorted_index_list:
            # If rows were adjacent
            if abs(i - last_item) <= 1:
                continuous_row.append(i)
                if i == len(sorted_index_list):
                    # Handle last row
                    continuous_row_list.append(continuous_row)
                    continuous_row = []
            else:
                if len(continuous_row) > 0:
                    continuous_row_list.append(continuous_row)
                    continuous_row = []
            last_item = i

        # Next, we remove boundaries that do not pass the line_thickness threshold
        # We also take the median of any remaining boundaries
        for row in continuous_row_list:
            if len(row) > line_thickness:
                boundaries.append(int(np.average(row)))

        # The end of an image is always a boundary
        img_size = self.height if axis == 1 else self.width
        boundaries.append(img_size - 1)

        return boundaries

    def get_boundaries_hierarchal(self, sorted_index_list, min_size: float, line_thickness: float, axis: int = 1):
        """In this algorithm, we chunk UNTIL the minimum size is reached."""
        # First we add all continuous 1-pixel boundaries to a list
        continuous_row_list = []
        continuous_row = []
        last_item = -1
        for i in sorted_index_list:
            # If rows were adjacent
            if abs(i - last_item) <= 1:
                continuous_row.append(i)
                if i == len(sorted_index_list):
                    # Handle last row
                    continuous_row_list.append(continuous_row)
                    continuous_row = []
            else:
                if len(continuous_row) > 0:
                    continuous_row_list.append(continuous_row)
                    continuous_row = []
            last_item = i

        # Next, we remove rows that do not meet the line_thickness threshold
        thick_boundaries_list = []
        for row in continuous_row_list:
            if len(row) > line_thickness:
                thick_boundaries_list.append(row)

        # Next, we sort the rows by length and add boundaries until the min_size is reached
        img_size = self.height if axis == 1 else self.width
        final_boundaries = [0, img_size]
        sorted_boundaries = sorted(thick_boundaries_list, key=lambda x: len(x), reverse=True)
        for row in sorted_boundaries:
            i = int(np.average(row))
            query_list = final_boundaries.copy()
            query_list.append(i)
            if check_boundary_proposals(sorted(query_list), min_size=min_size):
                # This proposal is okay, so we can attempt another boundary addition
                final_boundaries.append(i)
            else:
                # Query did not pass; break the loop and return the final boundary
                break

        final_boundaries = sorted(final_boundaries)
        return final_boundaries

    def run_tesseract(self, scale: int, blur_kernel: int = 3) -> None:
        """Run tesseract on this Chunk and store the results.

        :param scale: Factor to scale image by before performing tesseract.
        :param blur_kernel: Size of kernel to perform median blur. (e.g. 3)
        """
        # First we transform image for tesseract because it performs better with larger images
        # Tesseract's max dimension size is around 30000
        scale = scale if self.height * scale < 30000 else 30000 / self.height
        resize = cv2.resize(self.cv, (int(self.width * scale), int(self.height * scale)), interpolation=cv2.INTER_CUBIC)
        blur = cv2.medianBlur(resize, blur_kernel)

        # Run tesseract
        logger.debug(f'Starting tesseract on chunk: {self.xmin}-{self.ymin} ({self.width}x{self.height})...')
        data = pytesseract.image_to_data(blur, output_type=pytesseract.Output.DICT)
        logger.debug(f'Finished tesseract. Found {len(data["level"])} words.')

        # Store data
        self.tesseract = data

    def get_text(self, scale: int, blur_kernel: int = 3, minimum_conf: float = 50, recalculate: bool = False) -> str:
        """Get the text in this chunk as a string.

        :param scale: Factor to scale image by before performing tesseract.
        :param blur_kernel: Size of kernel to perform median blur. (e.g. 3)
        :param minimum_conf: Minimum confidence required to report text.
        :param recalculate: Recalculate the string if set to True.
        :return: A string representation of the text in this chunk.
        """
        # We run tesseract if it has not been run
        if self.tesseract is None:
            self.run_tesseract(scale=scale, blur_kernel=blur_kernel)

        # If the text has already been processed, we return it
        if self.text is not None and not recalculate:
            return self.text

        # Loop through tesseract data
        text_list = []
        last_block = 0
        for i in range(len(self.tesseract['level'])):
            block = self.tesseract['block_num'][i]
            conf = self.tesseract['conf'][i]
            text = self.tesseract['text'][i]
            if block != last_block:
                # Newline to indicate paragraph break
                text_list.append('\n')
            if conf > minimum_conf:
                text_list.append(text)
            last_block = block
        # Set the text in this chunk
        self.text = " ".join(text_list).strip()
        return self.text

    def get_text_bboxes(
            self,
            level: int,
            scale: int,
            blur_kernel: int = 3,
            minimum_conf: float = 50,
            absolute_coordinate: bool = True,
            recalculate: bool = False
    ) -> List[BBoxTuple]:
        """Get a list of bounding boxes surrounding the text in this chunk.

        Tesseract provides several different levels of bounding boxes:
        - Level 1: Page
        - Level 2: Block
        - Level 3: Paragraph
        - Level 4: Line
        - Level 5: Word

        Please specify the level for the granularity of bboxes to return. We also calculate the average confidence
        of words within the level. If the confidence does not exceed a threshold, we do not return the parent block.

        :param level: The text level (e.g. paragraph, sentence) as indicated by tesseract.
        :param scale: The scale factor used to resize the image before running tesseract.
        :param blur_kernel: Size of kernel to perform median blur. (e.g. 3).
        :param minimum_conf: Average text confidence required to pass parent bounding box.
        :param absolute_coordinate: Set to True if coordinates should be absolute as opposed to relative.
        :param recalculate: Set to True if the results should be recomputed.
        :return: A list of Bounding Box tuples.
        """
        # We run tesseract if it has not been run
        if self.tesseract is None:
            self.run_tesseract(scale=scale, blur_kernel=blur_kernel)

        # If the text bboxes have already been processed, we return it
        if self.text_bboxes is not None and not recalculate:
            return self.text_bboxes

        # Set scale and absolute coordinates
        scale = scale
        x_offset = self.xmin if absolute_coordinate else 0
        y_offset = self.ymin if absolute_coordinate else 0

        # Next iterate through the results and take the level we're interested in
        bboxes = []
        buffer = None
        conf_list = []
        logger.debug(f'Iterating through {len(self.tesseract["level"])} words...')
        for i in range(len(self.tesseract['level'])):
            this_level = self.tesseract['level'][i]
            text = self.tesseract['text'][i].strip()
            conf = self.tesseract['conf'][i]
            if this_level == level:
                # Flush any old results
                # logger.debug(f'Found level {level}.')
                if buffer is not None:
                    # logger.debug(f'Conf average: {np.average(conf_list)}.')
                    if len(conf_list) and np.average(conf_list) > minimum_conf:
                        bboxes.append(buffer)
                conf_list = []

                # Start a new buffer
                buffer = BBoxTuple(
                    xmin=int(self.tesseract['left'][i] / scale + x_offset),
                    xmax=int((self.tesseract['left'][i] + self.tesseract['width'][i]) / scale + x_offset),
                    ymin=int(self.tesseract['top'][i] / scale + y_offset),
                    ymax=int((self.tesseract['top'][i] + self.tesseract['height'][i]) / scale + y_offset)
                )
            if conf != -1 and text:
                # A conf of -1 means that it is not a word
                # logger.debug(f'Found word: {text}')
                conf_list.append(conf)

            if i == len(self.tesseract['level']):
                # Flush at the end of the loop
                if buffer is not None and len(text.strip()):
                    if len(conf_list) and np.average(conf_list) > minimum_conf:
                        bboxes.append(buffer)

        logger.debug(f'Found {len(bboxes)} results.')
        self.text_bboxes = bboxes
        return bboxes

    def get_text_conf(self):
        conf = np.array(self.tesseract['conf'])
        true_conf = conf[conf != -1]
        return np.average(true_conf)

    def get_image_bboxes(
            self,
            min_size: int = 10,
            line_thickness: int = 2,
            min_image_size: int = 100,
            color_threshold: int = 1000,
            n_recursions: int = 3,
            margin: float = 0,
            axis: int = 1,
            text_bboxes: List[BBoxTuple] = None
    ):
        """Get bounding boxes for images based on recursive chunking.

        :param min_size:
        :param line_thickness:
        :param min_image_size:
        :param color_threshold:
        :param n_recursions:
        :param margin:
        :param axis:
        :param text_bboxes:
        :return:
        """

        # Recursive function
        chunk_list = []
        if n_recursions > 1:
            chunks = self.generate_subchunks(min_size, line_thickness, axis=axis, margin=margin)
            for chunk in chunks:
                # We drop chunks entirely if they are too small
                # For large chunks, we attempt to re-chunk again
                if chunk.width > min_image_size and chunk.height > min_image_size:
                    new_axis = 0 if axis == 1 else 1
                    new_n = n_recursions - 1
                    child_chunks = chunk.get_image_bboxes(
                        min_size,
                        line_thickness,
                        min_image_size,
                        color_threshold,
                        new_n,
                        margin,
                        new_axis,
                        text_bboxes
                    )
                    chunk_list.extend(child_chunks)
            return chunk_list

        # Escape condition for recursion (n_recursions=0)
        else:
            chunks = self.generate_subchunks(min_size, line_thickness, axis=axis, margin=margin)
            for chunk in chunks:
                if chunk.width > min_image_size and chunk.height > min_image_size:

                    # If bboxes are provided, subtract bboxes from chunk
                    if text_bboxes:
                        cropped_chunk = subtract_bboxes_from_chunk(chunk, text_bboxes)
                        if cropped_chunk.width > min_image_size and cropped_chunk.height > min_image_size:
                            chunk_list.append(cropped_chunk)
                    else:
                        chunk_list.append(chunk)

            # Finally, we remove chunks with low color complexity, as this is more likely to be background
            high_diversity_list = []
            for i, chunk in enumerate(chunk_list):
                diversity = chunk.get_color_diversity()
                if diversity > color_threshold:
                    high_diversity_list.append(chunk)

            return high_diversity_list


    def is_valid(self):
        if self.width > 0 and self.height > 0:
            return True
        return False

    def get_color_diversity(self):
        b, g, r = cv2.split(self.cv)
        shiftet_im = b + 1000 * (g + 1) + 1000 * 1000 * (r + 1)
        return len(np.unique(shiftet_im))


def reduce_boundary_proposals(sorted_proposal_list, min_size: float):
    # Recursively reduce proposals until it passes the check
    # There should always be at least 2 items on the proposal list (start-end)
    current_proposals = sorted_proposal_list.copy()
    while not check_boundary_proposals(current_proposals, min_size) and len(current_proposals) > 2:

        # Get the smallest chunk and focus on this first
        subchunks = get_subchunks(current_proposals)
        smallest_i = None
        smallest_delta = math.inf
        for i, chunk in enumerate(subchunks):
            if chunk.delta < smallest_delta:
                smallest_i = i
                smallest_delta = chunk.delta
        smallest_chunk = subchunks[smallest_i]

        # We can't delete the start or end of an image
        if smallest_i == 0:
            current_proposals.remove(smallest_chunk.end)
        elif smallest_i == len(subchunks) - 1:
            current_proposals.remove(smallest_chunk.start)
        else:

            #  We delete the boundary based adjacent to the smaller neighboring chunk
            prev_chunk = subchunks[smallest_i - 1]
            next_chunk = subchunks[smallest_i + 1]
            if prev_chunk.delta < next_chunk.delta:
                current_proposals.remove(smallest_chunk.start)
            else:
                current_proposals.remove(smallest_chunk.end)
    return current_proposals


def get_subchunks(sorted_proposal_list):
    """Convert a list of boundaries to a list of tuple of (start, end, delta)."""
    # We iterate through length-1 because last element has no next_element
    subchunks = []
    for i in range(len(sorted_proposal_list) - 1):
        start = sorted_proposal_list[i]
        end = sorted_proposal_list[i + 1]
        delta = end - start
        subchunks.append(ChunkTuple(
            start=start,
            end=end,
            delta=delta
        ))
    return subchunks


def check_boundary_proposals(sorted_proposal_list, min_size: float):
    """Check if all boundary proposals pass the min_size threshold."""
    # We iterate through length-1 because last element has no next_element
    for i in range(len(sorted_proposal_list) - 1):
        this_proposal = sorted_proposal_list[i]
        next_proposal = sorted_proposal_list[i + 1]
        proposal_size = next_proposal - this_proposal
        if proposal_size < min_size:
            return False
    return True


def subtract_bboxes_from_chunk(chunk, bbox_list):
    """Crop the chunk based on any bboxes that overlap with the chunk.

    Note that we assume that the bboxes are provided as absolute coordinates.

    :param chunk:
    :param bbox_list:
    :return:
    """
    # First, we find all bboxes that overlap with the chunk
    has_intersection = False
    text_bbox_union_list = []
    for bbox in bbox_list:
        if calc_intersect(chunk.xmin, chunk.xmax, chunk.ymin, chunk.ymax,
                          bbox.xmin, bbox.xmax, bbox.ymin, bbox.ymax):
            has_intersection = False
            text_bbox_union_list.append(bbox)

    if has_intersection:
        # Take the union of the bboxes
        text_bbox_union = union_bboxes(text_bbox_union_list)

        # Subtract the union from the chunk
        return subtract_bbox(chunk, text_bbox_union)

    # This chunk has no intersections, so we return the original chunk
    else:
        return chunk


def union_bboxes(bbox_list):
    """Take the union of all bboxes in the list (the outer bbox that contains all the bboxes)."""
    xmin = math.inf
    xmax = 0
    ymin = math.inf
    ymax = 0
    for bbox in bbox_list:
        xmin = bbox.xmin if bbox.xmin < xmin else xmin
        xmax = bbox.xmax if bbox.xmax > xmax else xmax
        ymin = bbox.ymin if bbox.ymin < ymin else ymin
        ymax = bbox.ymax if bbox.ymax > ymax else ymax
    return BBoxTuple(
        xmin=xmin,
        xmax=xmax,
        ymin=ymin,
        ymax=ymax
    )


def subtract_bbox(chunk: CvChunk, bbox: BBoxTuple) -> Optional[CvChunk]:
    """Subtract the bbox from the chunk (the largest chunk that does not contain the bbox).

    We do this by calculating the resulting chunks from all four directions.
    Note that we assume that an intersection is present.

    :param chunk: The Chunk that should be subtracted from.
    :param bbox: The BBoxTuple to subtract from the Chunk.
    :return: A new Chunk that does not contain the BBoxTuple (or None if not possible).
    """
    # Perform subtraction
    north_slice_delta = chunk.ymax - bbox.ymax
    east_slice_delta = chunk.xmax - bbox.xmax
    south_slice_delta = bbox.ymin - chunk.ymin
    west_slice_delta = bbox.xmin - chunk.xmin
    if north_slice_delta >= east_slice_delta and north_slice_delta >= south_slice_delta and north_slice_delta >= west_slice_delta:
        min_delta = bbox.ymax - chunk.ymin
        chunk.cv = chunk.cv[min_delta:chunk.height, 0:chunk.width]
        chunk.ymin = bbox.ymax
        chunk.height = chunk.ymax - chunk.ymin
    elif east_slice_delta >= north_slice_delta and east_slice_delta >= south_slice_delta and east_slice_delta >= west_slice_delta:
        min_delta = bbox.xmax - chunk.xmin
        chunk.cv = chunk.cv[0:chunk.height, min_delta:chunk.width]
        chunk.xmin = bbox.xmax
        chunk.width = chunk.xmax - chunk.xmin
    elif south_slice_delta >= north_slice_delta and south_slice_delta >= east_slice_delta and south_slice_delta >= west_slice_delta:
        max_delta = bbox.ymin - chunk.ymin
        chunk.cv = chunk.cv[0:max_delta, 0:chunk.width]
        chunk.ymax = bbox.ymin
        chunk.height = chunk.ymax - chunk.ymin
    elif west_slice_delta >= north_slice_delta and west_slice_delta >= east_slice_delta and west_slice_delta >= west_slice_delta:
        max_delta = bbox.xmin - chunk.xmin
        chunk.cv = chunk.cv[0:chunk.height, 0:max_delta]
        chunk.xmax = bbox.xmin
        chunk.width = chunk.xmax - chunk.xmin

    # If the resulting chunk is invalid, return None
    if chunk.is_valid():
        return chunk
    else:
        return None
