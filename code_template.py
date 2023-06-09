#!/usr/bin/env python3

"""
Description:
nuScenes dataset loader for nuScenes detection task in nuScenes version v1.0.
This program is nuscenes dataset loader. This program is used for training and validation.
Input pickle file is generated by MMDetection3D "create_data.py" script. Please prepare the pickle file before running this script.

Features:
* feature 1
* feature 2

Issues:
* issue 1
* issue 2

Reference:
* Complex-YOLOv4-Pytorch

"""

__author__ = "Dong HE"
__authors__ = ["Dong HE","Kyungpyo Kim"]
__contact__ = "dhe@sapeon.com"
__copyright__ = "Copyright 2023, SAPEON Inc."
__credits__ = ["Dong HE","Kyungpyo Kim"]
__date__ = "2023/03/08"
__deprecated__ = False
__email__ = "dhe@sapeon.com"
__license__ = "SAPEON Inc."
__maintainer__ = "Dong HE"
__status__ = "Development"  # "Production" "Prototype" "Development"
__version__ = "0.0.1"

import os
import pickle
import random
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from nuscenes.utils import splits
from torch.utils.data import Dataset

import config.nus_config as cnf
from data_process import kitti_bev_utils, kitti_data_utils, transformation


class NusDataset(Dataset):
    def __init__(self, dataset_dir, mode='train', lidar_transforms=None, aug_transforms=None, multiscale=False,
                 num_samples=None, mosaic=False, random_padding=False, version='v1.0-trainval'):
        self.dataset_dir = Path(dataset_dir)
        self.lidar_sample_dir = self.dataset_dir / 'samples/LIDAR_TOP'
        assert mode in {'train', 'val',
                        'test'}, 'Invalid mode: {}'.format(mode)

        if version == 'v1.0-trainval':
            if mode == 'train':
                self.scenes = splits.train
            else:
                self.scenes = splits.val
        elif version == 'v1.0-test':
            assert False, 'Not implemented'
        elif version == 'v1.0-mini':
            assert False, 'Not implemented'
        else:
            raise ValueError('unknown')

        self.is_test = (mode == 'test')
        if mode == "test":
            self.mode = "val"
        else:
            self.mode = mode
        
        if self.mode != "test":
            ann = self.dataset_dir/f"nuscenes_infos_{self.mode}.pkl"
            with open(ann, 'rb') as f:
                self.ann = pickle.load(f)  # dict with metainfo and datalist

            self.metainfo = self.ann["metainfo"]
            if num_samples is not None:
                self.ann["data_list"] = self.ann["data_list"][:num_samples]
            self.num_samples = len(self.ann["data_list"])
    
        self.multiscale = multiscale
        self.lidar_transforms = lidar_transforms
        self.aug_transforms = aug_transforms
        self.img_size = cnf.BEV_WIDTH
        self.min_size = self.img_size - 3 * 32
        self.max_size = self.img_size + 3 * 32
        self.batch_count = 0
        self.mosaic = mosaic
        self.random_padding = random_padding
        self.mosaic_border = [-self.img_size // 2, -self.img_size // 2]
        print('number of samples: {}'.format(self.num_samples))

    def __getitem__(self, index):
        if self.is_test:
            bev, lidar2ego, token = self.load_test_data(index)
            return "dummy file path", bev

        if self.mosaic:
            img_files, bev, targets = self.load_mosaic(index)
            return img_files[0], bev, targets

        return self.load_train_data(index)

    def __len__(self):
        return self.num_samples
