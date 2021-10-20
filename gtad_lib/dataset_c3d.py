# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import json
import torch.utils.data as data
import torch
import h5py
from torch.functional import F

base_class = ['Fun sliding down', ' Beer pong', ' Getting a piercing', ' Shoveling snow', ' Kneeling', ' Tumbling', ' Playing water polo', ' Washing dishes', ' Blowing leaves', ' Playing congas', ' Making a lemonade', ' Playing kickball', ' Removing ice from car', ' Playing racquetball', ' Swimming', ' Playing bagpipes', ' Painting', ' Assembling bicycle', ' Playing violin', ' Surfing', ' Making a sandwich', ' Welding', ' Hopscotch', ' Gargling mouthwash', ' Baking cookies', ' Braiding hair', ' Capoeira', ' Slacklining', ' Plastering', ' Changing car wheel', ' Chopping wood', ' Removing curlers', ' Horseback riding', ' Smoking hookah', ' Doing a powerbomb', ' Playing ten pins', ' Getting a haircut', ' Playing beach volleyball', ' Making a cake', ' Clean and jerk', ' Trimming branches or hedges', ' Drum corps', ' Windsurfing', ' Kite flying', ' Using parallel bars', ' Doing kickboxing', ' Cleaning shoes', ' Playing field hockey', ' Playing squash', ' Rollerblading', ' Playing drums', ' Playing rubik cube', ' Sharpening knives', ' Zumba', ' Raking leaves', ' Bathing dog', ' Tug of war', ' Ping-pong', ' Using the balance beam', ' Playing lacrosse', ' Scuba diving', ' Preparing pasta', ' Brushing teeth', ' Playing badminton', ' Mixing drinks', ' Discus throw', ' Playing ice hockey', ' Doing crunches', ' Wrapping presents', ' Hand washing clothes', ' Rock climbing', ' Cutting the grass', ' Wakeboarding', ' Futsal', ' Playing piano', ' Baton twirling', ' Mooping floor', ' Triple jump', ' Longboarding', ' Polishing shoes', ' Doing motocross', ' Arm wrestling', ' Doing fencing', ' Hammer throw', ' Shot put', ' Playing pool', ' Blow-drying hair', ' Cricket', ' Spinning', ' Running a marathon', ' Table soccer', ' Playing flauta', ' Ice fishing', ' Tai chi', ' Archery', ' Shaving', ' Using the monkey bar', ' Layup drill in basketball', ' Spread mulch', ' Skateboarding', ' Canoeing', ' Mowing the lawn', ' Beach soccer', ' Hanging wallpaper', ' Tango', ' Disc dog', ' Powerbocking', ' Getting a tattoo', ' Doing nails', ' Snowboarding', ' Putting on shoes', ' Clipping cat claws', ' Snow tubing', ' River tubing', ' Putting on makeup', ' Decorating the Christmas tree', ' Fixing bicycle', ' Hitting a pinata', ' High jump', ' Doing karate', ' Kayaking', ' Grooming dog', ' Bungee jumping', ' Washing hands', ' Painting fence', ' Doing step aerobics', ' Installing carpet', ' Playing saxophone', ' Long jump', ' Javelin throw', ' Playing accordion', ' Smoking a cigarette', ' Belly dance', ' Playing polo', ' Throwing darts', ' Roof shingle removal', ' Tennis serve with ball bouncing', ' Skiing', ' Peeling potatoes', ' Elliptical trainer', ' Building sandcastles', ' Drinking beer', ' Rock-paper-scissors', ' Using the pommel horse', ' Croquet', ' Laying tile', ' Cleaning windows', ' Fixing the roof', ' Springboard diving', ' Waterskiing', ' Using uneven bars', ' Having an ice cream', ' Sailing', ' Washing face', ' Knitting', ' Bullfighting', ' Applying sunscreen', ' Painting furniture', ' Grooming horse', ' Carving jack-o-lanterns']
val_class = ['Swinging at the playground', ' Dodgeball', ' Ballet', ' Playing harmonica', ' Paintball', ' Cumbia', ' Rafting', ' Hula hoop', ' Cheerleading', ' Vacuuming floor', ' Playing blackjack', ' Waxing skis', ' Curling', ' Using the rowing machine', ' Ironing clothes', ' Playing guitarra', ' Sumo', ' Putting in contact lenses', ' Brushing hair', ' Volleyball']
test_class = ['Hurling', ' Polishing forniture', ' BMX', ' Riding bumper cars', ' Starting a campfire', ' Walking the dog', ' Preparing salad', ' Plataform diving', ' Breakdancing', ' Camel ride', ' Hand car wash', ' Making an omelette', ' Shuffleboard', ' Calf roping', ' Shaving legs', ' Snatch', ' Cleaning sink', ' Rope skipping', ' Drinking coffee', ' Pole vault']




def ioa_with_anchors(anchors_min, anchors_max, box_min, box_max):
    # calculate the overlap proportion between the anchor and all bbox for supervise signal,
    # the length of the anchor is 0.01
    len_anchors = anchors_max - anchors_min
    int_xmin = np.maximum(anchors_min, box_min)
    int_xmax = np.minimum(anchors_max, box_max)
    inter_len = np.maximum(int_xmax - int_xmin, 0.)
    scores = np.divide(inter_len, len_anchors)
    return scores


def iou_with_anchors(anchors_min, anchors_max, box_min, box_max):
    """Compute jaccard score between a box and the anchors.
    """
    len_anchors = anchors_max - anchors_min
    int_xmin = np.maximum(anchors_min, box_min)
    int_xmax = np.minimum(anchors_max, box_max)
    inter_len = np.maximum(int_xmax - int_xmin, 0.)
    union_len = len_anchors - inter_len + box_max - box_min
    # print inter_len,union_len
    jaccard = np.divide(inter_len, union_len)
    return jaccard


def load_json(file):
    with open(file) as json_file:
        json_data = json.load(json_file)
        return json_data


class VideoDataSet(data.Dataset):
    def __init__(self, opt, subset="train", mode="train"):
        self.temporal_scale = opt["temporal_scale"]  # 100
        self.temporal_gap = 1. / self.temporal_scale
        self.subset = subset
        self.mode = mode
        self.feature_path = opt["feature_path"]
        self.video_info_path = opt["video_info"]
        self.video_anno_path = opt["video_anno"]
        self._getDatasetDict()
        self._get_match_map()

    def _getDatasetDict(self):
        anno_df = pd.read_csv(self.video_info_path)
        anno_database = load_json(self.video_anno_path)
        self.video_dict = {}
        for i in range(len(anno_df)):
            video_name = anno_df.video.values[i]
            video_info = anno_database[video_name]
            video_subset = anno_df.subset.values[i]
            if self.subset in video_subset:
                self.video_dict[video_name] = video_info
                if len(video_info["annotations"]) > 0:
                    labels = video_info["annotations"][0]["label"]
                    if labels in base_class:
                        
                        self.video_list = list(self.video_dict.keys())
        print("%s subset video numbers: %d" % (self.subset, len(self.video_list)))

    def __getitem__(self, index):
        video_data = self._load_file(index)
        if self.mode == "train":
            match_score_start, match_score_end, confidence_score = self._get_train_label(index, self.anchor_xmin,
                                                                                         self.anchor_xmax)
            return video_data,confidence_score, match_score_start, match_score_end
        else:
            return index, video_data

    def _get_match_map(self):
        match_map = []
        for idx in range(self.temporal_scale):
            tmp_match_window = []
            xmin = self.temporal_gap * idx
            for jdx in range(1, self.temporal_scale + 1):
                xmax = xmin + self.temporal_gap * jdx
                tmp_match_window.append([xmin, xmax])
            match_map.append(tmp_match_window)
        match_map = np.array(match_map)  # 100x100x2
        match_map = np.transpose(match_map, [1, 0, 2])  # [0,1] [1,2] [2,3].....[99,100]
        match_map = np.reshape(match_map, [-1, 2])  # [0,2] [1,3] [2,4].....[99,101]   # duration x start
        self.match_map = match_map  # duration is same in row, start is same in col
        self.anchor_xmin = [self.temporal_gap * (i-0.5) for i in range(self.temporal_scale)]
        self.anchor_xmax = [self.temporal_gap * (i+0.5) for i in range(1, self.temporal_scale + 1)]

    def _load_file(self, index):
        video_name = self.video_list[index]
        # print("vid_name", video_name)
        # if self.feature_path[-1]=='/':  # h5 files are in seperated files
        #     if ',' in self.feature_path: # concatenation of two
        #         feat = []
        #         for feature_path in self.feature_path.split(','):
        #             with h5py.File(feature_path+video_name+'.h5', 'r') as f:
        #                 feat.append(f[video_name][:])
        #         feat = np.concatenate(feat,axis=1)
        #     else:
        #         # print(video_name, 'not found!!!!!!!!!!!')
        #         # feat = torch.randn((100,512))
        #         with h5py.File(self.feature_path+video_name+'.h5', 'r') as f:
        #             feat = f[video_name][:]
        # else:
        #     with h5py.File(self.feature_path, 'r') as features_h5:
        #         feat = features_h5[video_name][()]
        with h5py.File("/media/phd/SAURADIP5TB/dataset/C3D/sub_activitynet_v1-3.c3d.hdf5", 'r') as features_h5:
            feat = features_h5[video_name]["c3d_features"][:]
        # print("feat", feat.size())
        # video_data = torch.randn((100,400))
        video_data = torch.Tensor(feat)
        video_data = torch.transpose(video_data, 0, 1)
        if video_data.shape[0]!=self.temporal_scale: # rescale to fixed shape
            video_data = F.interpolate(video_data.unsqueeze(0), size=self.temporal_scale, mode='linear',align_corners=False)[0,...]
        video_data.float()
        return video_data

    def _get_train_label(self, index, anchor_xmin, anchor_xmax):
        video_name = self.video_list[index]
        video_info = self.video_dict[video_name]
        video_frame = video_info['duration_frame']
        video_second = video_info['duration_second']
        feature_frame = video_info['feature_frame']
        corrected_second = float(feature_frame) / video_frame * video_second  # there are some frames not used
        video_labels = video_info['annotations']  # the measurement is second, not frame

        ##############################################################################################
        # change the measurement from second to percentage
        gt_bbox = []
        gt_iou_map = []
        for j in range(len(video_labels)):
            tmp_info = video_labels[j]
            tmp_start = max(min(1, tmp_info['segment'][0] / corrected_second), 0)
            tmp_end = max(min(1, tmp_info['segment'][1] / corrected_second), 0)
            gt_bbox.append([tmp_start, tmp_end])
            tmp_gt_iou_map = iou_with_anchors(
                self.match_map[:, 0], self.match_map[:, 1], tmp_start, tmp_end)
            tmp_gt_iou_map = np.reshape(tmp_gt_iou_map,
                                        [self.temporal_scale, self.temporal_scale])
            gt_iou_map.append(tmp_gt_iou_map)
        gt_iou_map = np.array(gt_iou_map)
        gt_iou_map = np.max(gt_iou_map, axis=0)
        gt_iou_map = torch.Tensor(gt_iou_map)
        ##############################################################################################

        ####################################################################################################
        # generate R_s and R_e
        gt_bbox = np.array(gt_bbox)
        gt_xmins = gt_bbox[:, 0]
        gt_xmaxs = gt_bbox[:, 1]
        gt_lens = gt_xmaxs - gt_xmins
        gt_len_small = 3 * self.temporal_gap  # np.maximum(self.temporal_gap, self.boundary_ratio * gt_lens)
        gt_start_bboxs = np.stack((gt_xmins - gt_len_small / 2, gt_xmins + gt_len_small / 2), axis=1)
        gt_end_bboxs = np.stack((gt_xmaxs - gt_len_small / 2, gt_xmaxs + gt_len_small / 2), axis=1)
        #####################################################################################################

        ##########################################################################################################
        # calculate the ioa for all timestamp
        match_score_start = []
        for jdx in range(len(anchor_xmin)):
            match_score_start.append(np.max(
                ioa_with_anchors(anchor_xmin[jdx], anchor_xmax[jdx], gt_start_bboxs[:, 0], gt_start_bboxs[:, 1])))
        match_score_end = []
        for jdx in range(len(anchor_xmin)):
            match_score_end.append(np.max(
                ioa_with_anchors(anchor_xmin[jdx], anchor_xmax[jdx], gt_end_bboxs[:, 0], gt_end_bboxs[:, 1])))
        match_score_start = torch.Tensor(match_score_start)
        match_score_end = torch.Tensor(match_score_end)
        ############################################################################################################

        return match_score_start, match_score_end, gt_iou_map

    def __len__(self):
        return len(self.video_list)


if __name__ == '__main__':
    from gtad_lib import opts

    opt = opts.parse_opt()
    opt = vars(opt)
    train_loader = torch.utils.data.DataLoader(VideoDataSet(opt, subset="train"),
                                               batch_size=opt["batch_size"], shuffle=True,
                                               num_workers=8, pin_memory=True)
    for a,b,c,d in train_loader:
        print(a.shape,b.shape,c.shape,d.shape)
        break
