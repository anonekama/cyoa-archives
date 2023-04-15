import pathlib

import cv2


class CyoaROI:
    """Represents a region of interest (ROI) in a CYOA image."""

    def __init__(self, cyoa_img, x: int, y: int, size: int, cyoa_filepath: pathlib.Path):
        # Get second dimensions
        y2 = y + size if (y + size < cyoa_img.height) else cyoa_img.height
        x2 = x + size if (x + size < cyoa_img.width) else cyoa_img.width

        # Slice image
        self.roi = cyoa_img.cv2[y:y2, x:x2]
        self.x = x
        self.y = y
        self.size = size

        # Save ROI to file
        self.filename = pathlib.Path(cyoa_filepath.parent, cyoa_filepath.stem, f'_{x}_{y}.jpg')
        cv2.imwrite(self.filename, self.roi)

    def ocr_text(self):
        pass

    def ocr_images(self):
        pass
