import logging
import math
from collections import namedtuple
from typing import List

import cv2
import numpy as np

from ..util.functions import calc_intersect

logger = logging.getLogger(__name__)

ChunkTuple = namedtuple('ChunkTuple', ['start', 'end', 'delta'])


class CvChunk:

    def __init__(self, cv, x: int, y: int):
        """Construct a Chunk object.

        We assume that the image passed in has preprocessed (e.g. grayscale and blurred)

        :param cv:
        :param x:
        :param y:
        """
        self.cv = cv
        self.x = x
        self.y = y
        self.height = cv.shape[0]
        self.width = cv.shape[1]
        self.xmax = x + cv.shape[1]
        self.ymax = y + cv.shape[0]
        self.text = None
        self.text_boxes = None

    def generate_subchunks(self, min_size: float, line_thickness: float, bboxes: List = None, axis: int = 1,
                           margin: int = 0) -> List:
        """Divides a chunk into smaller chunks."""

        logger.debug('Starting to generate subchunk...')

        # If axis is 1, we make row chunks (horizontal lines)
        img_size = self.height if axis == 1 else self.width
        img_thickness = self.width if axis == 1 else self.height

        # If the Chunk is already too small return an empty list
        if img_size <= min_size:
            return []

        # If margin is set, we modify the image
        threshold_image = self.cv
        if margin:
            new_start = int(margin)
            new_end = int(img_thickness - margin)
            if axis == 1:
                threshold_image = threshold_image[0:img_size, new_start:new_end]
            else:
                threshold_image = threshold_image[new_start:new_end, 0:img_size]
            logger.debug(f'Image without margins: {threshold_image.shape[0]} {threshold_image.shape[1]}')

        # Apply Otsu's automatic thresholding
        threshold_image = cv2.cvtColor(threshold_image, cv2.COLOR_BGR2GRAY)
        (T, thresh) = cv2.threshold(threshold_image, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
        thresh_inv = 255 - thresh

        # Find continuous rows
        black_rows = np.where(~thresh.any(axis=axis))[0]
        white_rows = np.where(~thresh_inv.any(axis=axis))[0]
        all_rows = np.sort(np.append(black_rows, white_rows))
        logger.debug(f'Total Rows: {self.height} - AllBlack: {len(black_rows)} - AllWhite: {len(white_rows)}')

        # Get boundary proposals
        # boundary_proposals = self.get_boundaries(all_rows, line_thickness, axis=axis)
        boundary_proposals = self.get_boundaries_hierarchal(all_rows, min_size, line_thickness, axis=axis)

        # If boundary boxes are provided, then remove overlapping boundary proposals
        approved_proposals = []
        if bboxes:
            for i in boundary_proposals:
                good_boundary = True
                for bbox in bboxes:
                    intersection = calc_intersect(bbox.xmin, bbox.xmax, bbox.ymin, bbox.ymax, self.x, self.xmax, self.y, self.ymax)
                    logger.debug(f'{bbox.xmin} {bbox.xmax} {bbox.ymin} {bbox.ymax} | {self.x} {self.xmax} {self.y} {self.ymax} | {intersection}')
                    if intersection:
                        start = bbox.ymin if axis == 1 else bbox.xmin
                        end = bbox.ymax if axis == 1 else bbox.xmax
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
            new_cv = self.cv[chunk.start:chunk.end, 0:self.width] if axis == 1 else self.cv[0:self.height, chunk.start:chunk.end]
            new_chunk = CvChunk(
                cv=new_cv,
                x=self.x if axis == 1 else self.x + chunk.start,
                y=self.y + chunk.start if axis == 1 else self.y,
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


    def is_valid(self):
        if self.width > 0 and self.height > 0:
            return True
        return False

    def get_color_diversity(self):
        b, g, r = cv2.split(self.cv)
        shiftet_im = b + 1000 * (g + 1) + 1000 * 1000 * (r + 1)
        return len(np.unique(shiftet_im))


def reduce_boundary_proposals(sorted_proposal_list, min_size: float):
    # TODO: Implement a reduction algorithm that reduces based on width
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
            prev_chunk = subchunks[smallest_i-1]
            next_chunk = subchunks[smallest_i+1]
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
