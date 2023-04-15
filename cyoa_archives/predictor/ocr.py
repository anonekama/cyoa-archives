import logging
import math
import statistics
from typing import List, Dict

import keras_ocr

from .roi import CyoaROI

logger = logging.getLogger(__name__)

class KerasOCR:
    """Given a list of ROIs, fetch the text"""

    PIPELINE = keras_ocr.pipeline.Pipeline()

    @classmethod
    def read_rois(cls, rois: List[CyoaROI]):
        all_detections = []
        for i, roi in enumerate(rois[0:10]):
            roi_detections = cls.read_roi(roi)
            logger.info(f'Read {len(roi_detections)} detections in {i}/{len(rois)} rois.')
            all_detections.extend(roi_detections)
        logger.info(f'Read a total of {len(all_detections)} detections.')

        # Get char_size
        char_size = statistics.median(map(lambda x: x['char_size'], all_detections))
        logger.info(char_size)

        # Expand rois by ~2 characters in each direction and get chunks
        chunks = cls.chunk_rois(all_detections, char_size * 2)
        logger.info(f'Chunks: {len(chunks)}')

        # Chunk rois
        for chunk in chunks:
            s = []
            for r in chunk['rois']:
                s.append(r['text'])
            # logger.info(f'ChunkText: {s}')
            rows = get_rows(chunk, char_size)
            logger.info(f'Rows: {len(rows)}')
            for row in rows:
                text = []
                for roi in row:
                    text.append(roi['text'])
                logger.info(f'Text: {text}')


        # Overlap rois
        #cls.overlap_rois(all_detections)

        return all_detections



        # Order rois in each chunk

    @classmethod
    def read_roi(cls, roi: CyoaROI):
        # Perform keras ocr inference
        read_image = keras_ocr.tools.read(roi.roi)
        predictions = cls.PIPELINE.recognize([read_image])

        x0, y0 = 0, 0
        detections = []
        for group in predictions[0]:

            # Update coordinates to larger image; also add some fuzz
            top_left_x, top_left_y = group[1][0]
            bottom_right_x, bottom_right_y = group[1][1]
            top_left_x = top_left_x + roi.x
            top_left_y = top_left_y + roi.y
            bottom_right_x = bottom_right_x + roi.x
            bottom_right_y = bottom_right_y + roi.y

            # Append all results
            detections.append({
                'text': group[0],
                'xmin': top_left_x,
                'ymax': top_left_y,
                'xmax': bottom_right_x,
                'ymin': bottom_right_y,
                'char_size': int((bottom_right_x - top_left_x) / len(group[0]))
            })

        return detections

    @classmethod
    def chunk_rois(cls, rois: List[Dict], char_size: int) -> List[List]:
        chunks = []
        for roi in rois:
            found_overlap = False
            for chunk in chunks:
                overlap = calculate_overlap(roi, chunk, char_size, char_size)
                if overlap:
                    chunk['rois'].append(roi)
                    chunk['xmax'] = max(chunk['xmax'], roi['xmax'])
                    chunk['xmin'] = min(chunk['xmin'], roi['xmin'])
                    chunk['ymax'] = max(chunk['ymax'], roi['ymax'])
                    chunk['ymin'] = min(chunk['ymin'], roi['ymin'])
                    found_overlap = True
                    break
            if not found_overlap:
                chunks.append({
                    'rois': [roi],
                    'xmax': roi['xmax'],
                    'xmin': roi['xmin'],
                    'ymax': roi['ymax'],
                    'ymin': roi['ymin']
                })

        # Merge overlapping chunks
        merge_chunks = chunks
        merge_event = True
        while merge_event:
            merge_event = False
            for i in range(len(merge_chunks)):
                for j in range(i+1, len(merge_chunks)):
                    overlap = calculate_overlap(chunks[i], chunks[j])
                    if overlap:
                        merge_chunks[i]['rois'] = merge_chunks[i]['rois'] + merge_chunks[j]['rois']
                        merge_chunks[i]['xmax'] = max(merge_chunks[i]['xmax'], merge_chunks[j]['xmax'])
                        merge_chunks[i]['xmin'] = min(merge_chunks[i]['xmin'], merge_chunks[j]['xmin'])
                        merge_chunks[i]['ymax'] = max(merge_chunks[i]['ymax'], merge_chunks[j]['ymax'])
                        merge_chunks[i]['ymin'] = min(merge_chunks[i]['ymin'], merge_chunks[j]['ymin'])
                        merge_chunks.pop(j)
                        merge_event = True
                        break
                if merge_event:
                    break

        return merge_chunks


    @classmethod
    def overlap_rois(cls, rois: List[Dict], char_size):
        not_overlapping = []
        for i in range(0, len(rois) - 1):
            this_roi = rois[i]
            next_roi = rois[i+1]

            # Calculate overlap
            overlap = calculate_overlap(this_roi, next_roi, expand_y=int(char_size / 2))

            dx_of_this = overlap / (this_roi['xmax'] - this_roi['xmin']) * (this_roi['ymax'] - this_roi['ymin'])
            dy_of_this = overlap / (next_roi['xmax'] - next_roi['xmin']) * (next_roi['ymax'] - next_roi['ymin'])
            if dx_of_this > 0.5 or dy_of_this > 0.5:
                pass
            else:
                not_overlapping.append(this_roi)

def calculate_overlap(object_a, object_b, expand_x=0, expand_y=0):
    overlap = 0
    dx = min(object_a['xmax'] + expand_x, object_b['xmax'] + expand_x) - max(object_a['xmin'] - expand_x, object_b['xmin'] - expand_x)
    dy = min(object_a['ymax'] + expand_y, object_b['ymax'] + expand_y) - max(object_a['ymin'] - expand_y, object_b['ymin'] - expand_y)
    if (dx >= 0) and (dy >= 0):
        overlap = dx * dy
    return overlap

def get_rows(chunk, char_size):
    """Function to help distinguish unique rows"""
    step_size = int(char_size)
    rois = chunk['rois']
    rows = []
    for y in range(int(chunk['ymin']), int(chunk['ymax']), step_size):
        this_row = []
        new_roi_list = []
        for roi in rois:
            if roi['ymin'] - step_size <= y < roi['ymax'] + step_size:
                this_row.append(roi)
            else:
                new_roi_list.append(roi)
        rois = new_roi_list
        this_row = sorted(this_row, key=lambda x: x['xmin'])
        if len(this_row):
            rows.append(this_row)
    return rows
