import argparse
import os
import pathlib
import re
import tempfile

import cv2
import keybert
import pytesseract
import tensorflow as tf
from tensorflow.keras.applications.resnet50 import preprocess_input
from tensorflow.keras.preprocessing.image import img_to_array
from tensorflow.keras.applications import imagenet_utils

import deepdanbooru as dd

# Configuration
MAX_WIDTH = 1281
INPUT_SIZE = (512, 512)
SLIDING_WINDOW_DIM = (512, 512)
SLIDING_WINDOW_STEP = 256
PROJECT_PATH = '/Users/jyzhou/src/cyoa/cyoa_parser/deepdanbooru-v3-20211112-sgd-e28'
DD_THRESHOLD = 0.9
DD_REPORT_THRESHOLD = 0.03
KB_THRESHOLD = 0.3

def main(args):
	# Process arguments
	cyoa_dir = pathlib.Path(args.cyoa_dir)
	bad_tags_fn = pathlib.Path(args.bad_tags)
	do_ocr = args.textocr
	out_prefix = args.out_prefix
	if not cyoa_dir.exists():
	    print("The CYOA directory doesn't exist")
	    raise SystemExit(1)
	print("Temporary file directory: " + tempfile.gettempdir())

	# Loop through images in directory
	images = []
	for filename in os.listdir(cyoa_dir):
		if re.match('.*\.(jpg|jpeg|png)$', filename):
			images.append(filename)
	print("CYOA pages to analyze: " + str(len(images)))

	# For each page (image)...
	cyoa_text = ""
	seen_tags = {}
	rois = []
	for i, image_fn in enumerate(images):
		print("Now processing page " + str(i) + "...")
		cyoa_page = cv2.imread(os.path.join(cyoa_dir, image_fn))
		
		# OCR entire page for text
		if do_ocr:
			cyoa_text = cyoa_text + pytesseract.image_to_string(cyoa_page)

		# Resize tall pages (height > width)
		(H, W) = cyoa_page.shape[:2]
		if H > W and W > MAX_WIDTH:
			scale_percent = MAX_WIDTH / W
			dim = (int(W * scale_percent), int(H * scale_percent))
			cyoa_page = cv2.resize(cyoa_page, dim, interpolation = cv2.INTER_AREA)
			(H, W) = cyoa_page.shape[:2]

		# Sliding window
		for y in range(0, H - SLIDING_WINDOW_DIM[1], SLIDING_WINDOW_STEP):
			for x in range(0, W - SLIDING_WINDOW_DIM[0], SLIDING_WINDOW_STEP):
				x2 = x + SLIDING_WINDOW_DIM[0]
				y2 = y + SLIDING_WINDOW_DIM[1]
				roi = cv2.resize(cyoa_page[y:y2, x:x2], INPUT_SIZE)
				roi_fn = os.path.join(tempfile.gettempdir(), str(i) + '_' + str(x) + '_' + str(y) + '_' + str(x2) + '_' + str(y2) + '.jpg')
				cv2.imwrite(roi_fn, roi)
				rois.append(roi_fn)

	# Run DeepDanbooru on ROIs
	print("ROIs to analyze: " + str(len(rois)))
	model = dd.project.load_model_from_project(
	    PROJECT_PATH, compile_model=False
	)
	tags = dd.project.load_tags_from_project(PROJECT_PATH)
	for roi_fn in rois:
		for tag, score in dd.commands.evaluate_image(roi_fn, model, tags, DD_THRESHOLD):
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

	# Reprint interesting information
	with open(os.path.join(cyoa_dir, out_prefix + '_log.txt'), 'w') as l:
		l.write("CYOA pages to analyze: " + str(len(images)) + "\n")
		l.write("ROIs to analyze: " + str(len(rois)) + "\n")
		print("CYOA pages to analyze: " + str(len(images)))
		print("ROIs to analyze: " + str(len(rois)))

		# Filter out bad tags
		badtags = {}
		with open(bad_tags_fn) as f:
			for line in f.readlines():
				if line.strip() not in badtags:
					badtags[line.strip()] = True
		print("Unique tags identified: " + str(len(seen_tags)))
		l.write("Unique tags identified: " + str(len(seen_tags)) + "\n")
		with open(os.path.join(cyoa_dir,out_prefix + '_dd.tsv'), 'w') as f:
			for tag, d in sorted(seen_tags.items(), key=lambda kv: kv[1]['score'], reverse=True):
				if tag not in badtags:
					roi_length = len(rois)
					tag_count = d['count']
					tag_freq = tag_count / roi_length
					tag_score = d['score'] / roi_length
					tag_avg = d['score'] / tag_count
					tag_max = d['max']
					f.write(f"{tag}\t{tag_count}\t{roi_length}\t{tag_freq:05.3f}\t{tag_avg:05.3f}\t{tag_max:05.3f}\t{tag_score:05.3f}\t\n")
					if tag_score > DD_REPORT_THRESHOLD:
						l.write(f"{tag}:{tag_score:05.3f} ")
			l.write("\n")

		# Run KeyBERT
		if do_ocr:
			l.write("Total length of text: " + str(len(cyoa_text)) + "\n")
			print("Total length of text: " + str(len(cyoa_text)))
			with open(os.path.join(cyoa_dir, out_prefix + '_tt.txt'), 'w') as f:
				f.write(cyoa_text)
			with open(os.path.join(cyoa_dir,out_prefix + '_kb.tsv'), 'w') as f:
				kw_model = keybert.KeyBERT('all-mpnet-base-v2')
				keywords = kw_model.extract_keywords(cyoa_text, keyphrase_ngram_range=(1, 1), stop_words=None, top_n=10)
				top_keywords = ""
				for keyword in keywords:
					f.write(f"{keyword[0]}\t{keyword[1]}\n")
					if keyword[1] > KB_THRESHOLD:
						top_keywords = top_keywords + keyword[0] + ", "
						l.write(f"{keyword[0]}:{keyword[1]:05.3f} ")
				print("Top keys: " + top_keywords)
				l.write("\n")


if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("cyoa_dir")
	parser.add_argument("-x", "--bad_tags", required=False)
	parser.add_argument("-t", "--textocr", action="store_true", default=True)
	parser.add_argument("-o", "--out_prefix", required=False, default="")
	args = parser.parse_args()
	main(args)