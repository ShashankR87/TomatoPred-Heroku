from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import numpy as np
import pandas as pd
from datetime import datetime
import cv2
import os
import re

from PIL import Image

import albumentations as A
from albumentations.pytorch.transforms import ToTensorV2

import torch
import torchvision

from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.models.detection import FasterRCNN
from torchvision.models.detection.rpn import AnchorGenerator

from torch.utils.data import DataLoader, Dataset
from torch.utils.data.sampler import SequentialSampler

from matplotlib import pyplot as plt
app = Flask(__name__)

app.secret_key = 'dljsaklqk24e21cjn!Ew@@dsa5rcb'

@app.route('/', methods=['GET','POST'])
def home():
    if request.method == 'POST':

        userFile = request.files["userFile"]
        curtime = str(datetime.now())
        filename = 'static/img/usrFile' + curtime + '.jpg'
        test_filename = 'test/usrFile' + curtime + '.jpg'
        htmlfilename = 'static/img/usrFile' + curtime + '.jpg'
        userFile.save(filename)
        userFile.save(test_filename)
        session["fileLoc"] = filename
        processedFileLoc = processFiles(test_filename)
        return render_template('index.html',processed='yes',uploaded=htmlfilename,result=processedFileLoc)

    return render_template('index.html',processed='no',uploaded='',result='')

test_df = pd.read_csv('sample-train.csv')
DIR_TEST = 'test'

WEIGHTS_FILE = 'fasterrcnn_resnet50_fpn.pth'
model = torchvision.models.detection.fasterrcnn_resnet50_fpn(pretrained=True)

class TomatoTestDataset(Dataset):

    def __init__(self, dataframe, image_dir, transforms=None):
        super().__init__()

        self.image_ids = dataframe['image_id'].unique()
        self.df = dataframe
        self.image_dir = image_dir
        self.transforms = transforms

    def __getitem__(self, index: int):

        image_id = self.image_ids[index]
        records = self.df[self.df['image_id'] == image_id]

        image = cv2.imread(f'{self.image_dir}/{image_id}', cv2.IMREAD_COLOR)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB).astype(np.float32)
        image /= 255.0

        if self.transforms:
            sample = {
                'image': image,
            }
            sample = self.transforms(**sample)
            image = sample['image']

        return image, image_id

    def __len__(self) -> int:
        return self.image_ids.shape[0]

def get_test_transform():
    return A.Compose([
        # A.Resize(512, 512),
        ToTensorV2(p=1.0)
    ])

def format_prediction_string(boxes, scores):
    pred_strings = []
    for j in zip(scores, boxes):
        pred_strings.append("{0:.4f} {1} {2} {3} {4}".format(j[0], j[1][0], j[1][1], j[1][2], j[1][3]))

    return " ".join(pred_strings)

def processFiles(filename):

    test_df = test_df.append({'image_id': filename, 'PredictionString': '1.0 0 0 50 50'})
    #do shit
    test_dataset = TomatoTestDataset(test_df, DIR_TEST, get_test_transform())

    test_data_loader = DataLoader(
        test_dataset,
        batch_size=4,
        shuffle=False,
        num_workers=4,
        drop_last=False,
        collate_fn=collate_fn
    )
    detection_threshold = 0.5
    results = []
    images = []
    outputs = []
    for images, image_ids in test_data_loader:

        images = list(image.to(device) for image in images)
        outputs = model(images)

        for i, image in enumerate(images):
            boxes = outputs[i]['boxes'].data.cpu().numpy()
            scores = outputs[i]['scores'].data.cpu().numpy()

            boxes = boxes[scores >= detection_threshold].astype(np.int32)
            scores = scores[scores >= detection_threshold]
            image_id = image_ids[i]

            boxes[:, 2] = boxes[:, 2] - boxes[:, 0]
            boxes[:, 3] = boxes[:, 3] - boxes[:, 1]

            result = {
                'image_id': image_id,
                'PredictionString': format_prediction_string(boxes, scores)
            }

            results.append(result)

    sample = images[-1].permute(1,2,0).cpu().numpy()
    boxes = outputs[-1]['boxes'].data.cpu().numpy()
    scores = outputs[-1]['scores'].data.cpu().numpy()

    boxes = boxes[scores >= detection_threshold].astype(np.int32)

    fig, ax = plt.subplots(1, 1, figsize=(16, 8))

    for box in boxes:
        cv2.rectangle(sample,
                      (box[0], box[1]),
                      (box[2], box[3]),
                      (220, 0, 0), 2)

    ax.set_axis_off()
    #ax.imshow(sample)
    savedfilename = 'static/img/pred_' + filename
    fig.savefig(savedfilename)


    return savedfilename



if __name__ == '__main__':
    app.run(debug=True)