import cv2
import numpy as np
import deepdanbooru as dd
import tensorflow as tf

PROJECT_PATH = 'deepdanbooru-v3-20211112-sgd-e28'
DD_THRESHOLD = 0.5
DD_REPORT_THRESHOLD = 0.03


def resizeAndPad(img, size, padColor=0):

    h, w = img.shape[:2]
    sh, sw = size

    # interpolation method
    if h > sh or w > sw: # shrinking image
        interp = cv2.INTER_AREA
    else: # stretching image
        interp = cv2.INTER_CUBIC

    # aspect ratio of image
    aspect = w/h  # if on Python 2, you might need to cast as a float: float(w)/h

    # compute scaling and pad sizing
    if aspect > 1: # horizontal image
        new_w = sw
        new_h = np.round(new_w/aspect).astype(int)
        pad_vert = (sh-new_h)/2
        pad_top, pad_bot = np.floor(pad_vert).astype(int), np.ceil(pad_vert).astype(int)
        pad_left, pad_right = 0, 0
    elif aspect < 1: # vertical image
        new_h = sh
        new_w = np.round(new_h*aspect).astype(int)
        pad_horz = (sw-new_w)/2
        pad_left, pad_right = np.floor(pad_horz).astype(int), np.ceil(pad_horz).astype(int)
        pad_top, pad_bot = 0, 0
    else: # square image
        new_h, new_w = sh, sw
        pad_left, pad_right, pad_top, pad_bot = 0, 0, 0, 0

    # set pad color
    if len(img.shape) == 3 and not isinstance(padColor, (list, tuple, np.ndarray)): # color image but only one color provided
        padColor = [padColor]*3

    # scale and pad
    scaled_img = cv2.resize(img, (new_w, new_h), interpolation=interp)
    scaled_img = cv2.copyMakeBorder(scaled_img, pad_top, pad_bot, pad_left, pad_right, borderType=cv2.BORDER_CONSTANT, value=padColor)

    return scaled_img


# Run DeepDanbooru on ROIs
model = dd.project.load_model_from_project(
    PROJECT_PATH, compile_model=False
)
tags = dd.project.load_tags_from_project(PROJECT_PATH)

width = model.input_shape[2]
height = model.input_shape[1]
print(width) # 512
print(height) # 512

roi_fn = 'dd2.jpg'

cv = cv2.imread(roi_fn)
image = tf.image.resize(
            cv,
            size=(height, width),
            method=tf.image.ResizeMethod.AREA,
            preserve_aspect_ratio=True,
)
#resize = resizeAndPad(cv, (512, 512))

image = image.numpy()
image = dd.image.transform_and_pad_image(image, width, height)
image = image / 255.0

image_shape = image.shape
print(image_shape)
image = image.reshape((1, image_shape[0], image_shape[1], image_shape[2]))
y = model.predict(image)[0]

result_dict = {}

for i, tag in enumerate(tags):
    result_dict[tag] = y[i]

for tag in tags:
    if result_dict[tag] >= DD_THRESHOLD:
        print(f'{tag}, {result_dict[tag]}')

print('EMPTY ROWW EMPTY ROWW EMPTY ROWW EMPTY ROWW EMPTY ROWW v EMPTY ROWW EMPTY ROWW')

seen_tags = {}
for tag, score in dd.commands.evaluate_image(roi_fn, model, tags, DD_THRESHOLD):
    print(f'{tag}, {score}')
    if tag in seen_tags:
        seen_tags[tag]['count'] = seen_tags[tag]['count'] + 1
        seen_tags[tag]['score'] = seen_tags[tag]['score'] + score # score
        if score > seen_tags[tag]['max']:
            seen_tags[tag]['max'] = score # max
    else:
        seen_tags[tag] = {
            'count': 1,
            'score': score,
            'max': score
        }

#print(seen_tags)
