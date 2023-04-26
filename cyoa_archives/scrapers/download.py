"""Download file from url."""

import logging
import os
import pathlib
import shutil
import subprocess

from typing import Optional, List

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class CyoaDownload:

    def __init__(self, tempdir):
        self.tempdir = pathlib.Path(tempdir)

    def clear_tempdir(self):
        if self.tempdir.exists():
            logger.info(f'Deleting directory: {self.tempdir.resolve()}')
            shutil.rmtree(self.tempdir.resolve())
        os.makedirs(self.tempdir)

    def get_files(self):
        image_paths = []
        for extension in ['*.png', '*.jpg', '*.jpeg', '*.webp']:
            for image_path in self.tempdir.rglob(extension):
                image_paths.append(image_path)
        # TODO: Sort the image paths in order
        return image_paths

    def gallery_dl(self, url: str) -> List[pathlib.Path]:
        # TODO: Find a way to limit downloads from bad urls
        if url:
            self.clear_tempdir()
            subprocess.run(['gallery-dl', url, '-d', self.tempdir.resolve()], universal_newlines=True)
            return self.get_files()
        else:
            return []

    def interactive_dl(self, url):
        pass
