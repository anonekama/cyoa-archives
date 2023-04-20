from collections import OrderedDict
import logging
import math

import deepdanbooru as dd
import tensorflow as tf

PROJECT_PATH = 'deepdanbooru-v3-20211112-sgd-e28'
DD_THRESHOLD = 0.5
DD_REPORT_THRESHOLD = 0.03

logger = logging.getLogger(__name__)

class DeepDanbooru:
    """A wrapper around the DeepDanbooru project.

    The default model uses images of 512x512 size.
    """

    def __init__(self, project_path=PROJECT_PATH, tags_path=None, special_tags=None, threshold=0.5):
        self.model = dd.project.load_model_from_project(project_path, compile_model=False)
        self.special_tags = special_tags
        self.threshold = threshold
        if tags_path:
            self.tags = dd.data.load_tags(tags_path)
        else:
            self.tags = dd.project.load_tags_from_project(PROJECT_PATH)

    def evaluate_from_file(self, filename, threshold):
        tag_dict = {}
        for tag, score in dd.commands.evaluate_image(filename, self.model, self.tags, threshold):
            tag_dict[tag] = score
        return tag_dict

    def evaluate(self, cv):
        # Resize image
        image = tf.image.resize(
            cv,
            size=(self.model.input_shape[1], self.model.input_shape[2]),
            method=tf.image.ResizeMethod.AREA,
            preserve_aspect_ratio=True,
        )

        # Center, warp, and normalize image
        image = image.numpy()
        image = dd.image.transform_and_pad_image(image, self.model.input_shape[2], self.model.input_shape[1])
        image = image / 255.0

        # Run the model
        logger.debug(f'Starting DeepDanbooru...')
        image = image.reshape((1, image.shape[0], image.shape[1], image.shape[2]))
        y = self.model.predict(image)[0]

        # Return results
        result_dict = OrderedDict()
        for i, tag in enumerate(self.tags):
            if y[i] > self.threshold:
                result_dict[tag] = y[i]
            else:
                result_dict[tag] = 0

        # Apply special tags (get the maximum of all related tags)
        # logger.debug(self.special_tags.items())
        for tag, tag_list in self.special_tags.items():
            value_list = []
            for item in tag_list:
                value_list.append(result_dict[item])
            result_dict[tag] = max(value_list)

        return result_dict
