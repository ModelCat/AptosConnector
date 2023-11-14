import hashlib

import json
import glob
import argparse
import logging as log
import os.path as osp
import os
from typing import List, Optional
import numpy as np
from pathlib import Path
from itertools import combinations
from collections import Counter
import shutil
from .utils import hash_dataset
import pkg_resources

class DatasetValidator:

    def __init__(
            self,
            dataset_root_dir: str,
            working_dir: str = None,
            auto_fix: bool = False,
            auto_fix_prompt: bool = True
    ):

        if not osp.exists(dataset_root_dir):
            print(f'Path does not exists: {dataset_root_dir}')
            exit(1)

        self.root_dir = dataset_root_dir
        self.working_dir = working_dir
        self.auto_fix = auto_fix
        self.log_filename = 'dataset_validator_log.txt'
        self.auto_fix_prompt = auto_fix_prompt

        self.messages = None

        if self.working_dir is not None:
            self.log_filepath = osp.join(self.working_dir, self.log_filename)
            os.makedirs(self.working_dir, exist_ok=True)

            # wipe content of eventually existing log file
            with open(self.log_filepath, "w"):
                pass
        else:
            self.log_filepath = None

    def create_validation_mark(self):
        # check if any errors were found
        if self.messages is None:
            print('Please validate dataset first')
            return
        
        erros_count = len([m for m in self.messages if m.get('type') == 'error'])
        if erros_count:
            print(f'Dataset not validated, {erros_count} error(s) found.')
        else:
            print('No critical errors found')
            print('Creating dataset signature ...')
            sha = hash_dataset(self.root_dir)
            msg = f'Validation passed and signed: {sha}'
            with open(self.log_filepath, 'a') as fp:
                fp.write(msg+'\n')
            print(msg)

    def validate_dataset(self, annotations_required: bool = True):
        """
        Validates dataset structure.

        Args:
            annotations_required (bool): Whether the dataset is required to have annotations

        Returns:
            Returns a dictionary of key-value pairs, where key is the unique name of the check
            and value is a dictionary containing the following fields: `passed: bool`, `message`: str.
            Supported check keys are:
             -
        """
        self.messages = []

        dataset_infos_path = osp.join(self.root_dir, "dataset_infos.json")

        if not osp.exists(dataset_infos_path):
            self.messages.append({'type': 'error', 'message': f'"dataset_infos.json" does not exist'})
            self.messages.append({'type': 'critical', 'message': f'^^^^^ Validation stopped due to a critical error'})
            return self.messages

        images_dir = osp.join(self.root_dir, "images")
        annotations_dir = osp.join(self.root_dir, "annotations")

        thumbnail_path = osp.join(self.root_dir, "thumbnail.jpg")
        if not osp.exists(thumbnail_path):
            if not self.auto_fix:
                self.messages.append({'type': 'warning', 'message': f'The dataset is missing the "thumbnail.jpg" file. '
                                                                    f'Pick one image from the dataset, name it as '
                                                                    f'"thumbnail.jpg" and place it inside the '
                                                                    f'dataset root directory.'})
            else:
                first_image = _get_first_image_from_dir(images_dir)
                if first_image is not None:
                    shutil.copy(first_image, thumbnail_path)
                    log.debug(f'Auto-fix: thumbnail generated automatically from image "{first_image}"')
                else:
                    self.messages.append({
                        'type': 'error',
                        'message': 'Couldn\'t find any image to serve as a thumbnail for the dataset.'
                    })

        dataset_info_messages, ann_file_names, split_names, label_names = self.validate_dataset_infos_file(dataset_infos_path)
        self.messages += dataset_info_messages

        annotations_messages = self.validate_annotations_and_images(annotations_required, annotations_dir,
                                                                    ann_file_names, split_names,
                                                                    label_names, images_dir)

        self.messages += annotations_messages

        split_size_messages = self.validate_split_sizes(dataset_infos_path, split_names, annotations_dir, images_dir)

        self.messages += split_size_messages

        return self.messages

    def validate_dataset_infos_file(self, dataset_infos_path: str):

        messages = []
        ann_file_names = []
        split_names = []
        label_names = []

        if not osp.exists(dataset_infos_path):
            return [{'type': 'error', 'message': 'The "dataset_infos.json" file is missing.'}], [], [], []

        try:
            with open(dataset_infos_path, "r") as f:
                dataset_infos_json = json.load(f)
        except Exception as e:
            return [{'type': 'error',
                     'message': f'The "dataset_infos.json" file is not formatted correctly: {e}.'}], [], [], []

        dataset_name = list(dataset_infos_json.keys())[0]
        dataset_info = dataset_infos_json[dataset_name]

        for key in ["splits", "task_templates"]:
            if key not in dataset_info:
                messages.append({'type': 'error', 'message': f'"dataset_infos.json" is missing the "{key}" key.'})

        for key in ["description", "builder_name", "config_name"]:
            if key not in dataset_info:
                if not self.auto_fix:
                    messages.append({'type': 'warning', 'message': f'"dataset_infos.json" is missing the "{key}" key.'})
                else:
                    dataset_info[key] = ""
                    log.debug(f'Auto-fix: "{key}" key added to "dataset_infos.json" file')

        if "splits" in dataset_info:
            for split in ["train", "test", "validation"]:
                if split not in dataset_info["splits"]:
                    messages.append({'type': 'error',
                                     'message': f'Split "{split}" is missing in the splits listed in the '
                                                f'"dataset_infos.json" file.'})
                else:
                    if "dataset_name" not in dataset_info["splits"][split]:
                        messages.append({'type': 'error',
                                         'message': f'Split "{split}" is missing the "dataset_name" key in the '
                                                    f'"dataset_infos.json" file.'})

        if "task_templates" in dataset_info:
            if len(dataset_info["task_templates"]) == 0:
                messages.append({'type': 'error',
                                 'message': f'Task templates in the "dataset_infos.json" file is empty.'})
            else:
                task_template = dataset_info["task_templates"][0]
                if "task" not in task_template:
                    messages.append({'type': 'error',
                                     'message': f'Task templates in the "dataset_infos.json" is missing the "task" key.'})
                else:
                    if task_template["task"] not in ["detection", "classification", "keypoints"]:
                        messages.append({'type': 'error',
                                         'message': f'Found unexpected value of "{task_template["task"]}" '
                                                    f'in the "task_templates/task" field inside the "dataset_infos.json" file. '
                                                    f'Expected either "classification", "detection" or "keypoints".'})
                if "labels" not in task_template:
                    messages.append({'type': 'error',
                                     'message': f'Task templates in the "dataset_infos.json" is missing the "labels" key.'})
                else:
                    label_names = task_template["labels"]

        try:
            for split in dataset_info["splits"]:
                if "dataset_name" in dataset_info["splits"][split]:
                    ann_file_names.append(dataset_info["splits"][split]["dataset_name"])
                    split_names.append(split)
        except:
            pass

        real_img_count = _count_imgs_in_dir(osp.join(self.root_dir, 'images'))
        if "dataset_size" in dataset_info:
            if type(dataset_info["dataset_size"]) is int:
                if real_img_count != dataset_info["dataset_size"]:
                    if not self.auto_fix:
                        messages.append({'type': 'warning', 'message': f'"dataset_infos.json" shows {dataset_info["dataset_size"]} images in dataset, but {real_img_count} were found in the "images" directory.'})
                    else:
                        dataset_infos_json[dataset_name]["dataset_size"] = real_img_count
                        _reload_dataset_infos(dataset_infos_path, dataset_infos_json)
                        log.debug(f"Auto-fix: changed dataset_size to {real_img_count}.")
            else:
                if not self.auto_fix:
                    messages.append({'type': 'warning',
                                     'message': f'"dataset_infos.json" doesn\'t contain a valid entry for "dataset_size", {real_img_count} were found in the "images" directory.'})
                else:
                    dataset_infos_json[dataset_name]["dataset_size"] = real_img_count
                    _reload_dataset_infos(dataset_infos_path, dataset_infos_json)
                    log.debug(f"Auto-fix: added dataset_size ({real_img_count} to dataset_infos.json")
        else:
            if not self.auto_fix:
                messages.append({'type': 'warning',
                                    'message': f'"dataset_infos.json" doesn\'t contain an entry for "dataset_size".'})
            else:
                dataset_infos_json[dataset_name]["dataset_size"] = real_img_count
                _reload_dataset_infos(dataset_infos_path, dataset_infos_json)
                log.debug(f"Auto-fix: added dataset_size ({real_img_count} to dataset_infos.json.") 
        real_size_in_bytes = _calculate_dir_size(self.root_dir)
        if "size_in_bytes" in dataset_info:
            if type(dataset_info["size_in_bytes"]) == int:
                if real_size_in_bytes != dataset_info["size_in_bytes"]:
                    if not self.auto_fix:
                        messages.append({'type': 'warning', 'message': f'"dataset_infos.json" shows {dataset_info["size_in_bytes"]}B as dataset size, but {real_size_in_bytes} B size was calculated using the dataset root directory.'})
                    else:
                        dataset_infos_json[dataset_name]["size_in_bytes"] = real_size_in_bytes
                        _reload_dataset_infos(dataset_infos_path, dataset_infos_json)
                        log.debug(f"Auto-fix: changed size_in_bytes to {real_size_in_bytes}.")
            else:
                if not self.auto_fix:
                    messages.append({'type': 'warning', 'message': f'"dataset_infos.json" doesn\'t contain a valid entry for "size_in_bytes", {real_size_in_bytes} B size was calculated using the dataset root directory.'})
                else:
                    dataset_infos_json[dataset_name]["size_in_bytes"] = real_size_in_bytes
                    _reload_dataset_infos(dataset_infos_path, dataset_infos_json)
                    log.debug(
                        f"Auto-fix: added size_in_bytes {dataset_info['size_in_bytes']} to dataset_infos.json."
                    )
        else:
            if not self.auto_fix:
                messages.append({'type': 'warning', 'message': f'"dataset_infos.json" doesn\'t contain an entry for "size_in_bytes".'})
            else:
                dataset_infos_json[dataset_name]["size_in_bytes"] = real_size_in_bytes
                _reload_dataset_infos(dataset_infos_path, dataset_infos_json)
                log.debug(
                    f"Auto-fix: added size_in_bytes {dataset_info['size_in_bytes']} to dataset_infos.json."
                )

        return messages, ann_file_names, split_names, label_names

    def validate_annotations_and_images(self, annotations_required: bool, annotations_dir: str,
                                        ann_file_names: List[str], split_names: List[str],
                                        label_names: List[str], images_dir: str):

        messages = []

        if not osp.exists(annotations_dir) and annotations_required:
            messages.append({'type': 'error', 'message': 'The "annotations" folder is missing.'})
            if not osp.exists(images_dir):
                messages.append({'type': 'error', 'message': 'The "images" folder is missing.'})
            return messages

        if not osp.exists(images_dir):
            return [{'type': 'error', 'message': 'The "images" folder is missing.'}]

        if not annotations_required:
            return []

        for ann_file in ann_file_names:
            if not osp.exists(osp.join(annotations_dir, ann_file)):
                messages.append({'type': 'error',
                                 'message': f'The annotation file "{ann_file}" listed in "dataset_infos.json" is missing in the "annotations" folder.'})
            else:
                messages += self.validate_coco_file(osp.join(annotations_dir, ann_file), images_dir, label_names)

        messages += self.check_for_duplicate_images(images_dir)
        for ann_file in ann_file_names:
            messages += self.check_split_image_duplicates(osp.join(annotations_dir, ann_file))

        for ((i1, ann_file_1), (i2, ann_file_2)) in combinations(enumerate(ann_file_names), 2):
            messages += self.check_for_split_leakage(osp.join(annotations_dir, ann_file_1),
                                                     osp.join(annotations_dir, ann_file_2), split_names[i1],
                                                     split_names[i2])
        return messages

    def validate_coco_file(self, coco_file_path: str, image_dir: str, label_names: List[str]):

        messages = []
        coco_file_name = osp.basename(coco_file_path)

        try:
            with open(coco_file_path, "r") as f:
                coco = json.load(f)
        except Exception as e:
            return [{'type': 'error',
                     'message': f'The annotation file "{coco_file_name}" is not formatted correctly: {e}.'
                     }]

        try:
            category_names = [cat["name"] for cat in coco["categories"]]
            if not set(category_names) == set(label_names):
                messages.append({'type': 'error',
                                 'message': f'The category names in the annotation file "{coco_file_name}" do not match the label names in the "dataset_infos.json" file.'})

            missing_images = []
            imgs_without_anns = []

            for img in coco["images"]:
                img_path = osp.join(image_dir, img["file_name"])
                if not osp.exists(img_path):
                    missing_images.append(img["file_name"])
                anns_for_img = [ann for ann in coco["annotations"] if ann["image_id"] == img["id"]]
                if len(anns_for_img) == 0:
                    imgs_without_anns.append(img["file_name"])

            if len(missing_images) > 0:
                messages.append({'type': 'error',
                                 'message': f'The annotation file "{coco_file_name}" contains {len(missing_images)} images that are not found in the "images" folder.'})
                if self.log_filepath is not None:
                    try:
                        with open(self.log_filepath, 'a') as file:
                            for img in missing_images:
                                file.write(f'Image "{img}" from the "{coco_file_name}" annotation file is missing.\n')
                    except:
                        print(f"Log file not found or can't be opened: {self.log_filepath}")

            if len(imgs_without_anns) > 0:
                if not self.auto_fix:
                    messages.append({'type': 'warning',
                                     'message': f'The annotation file "{coco_file_name}" contains {len(imgs_without_anns)} images that don\'t have corresponding annotations.'})
                    if self.log_filepath is not None:
                        try:
                            with open(self.log_filepath, 'a') as file:
                                for img in imgs_without_anns:
                                    file.write(f'Image "{img}" from the "{coco_file_name}" annotation file doesn\'t have any annotations.\n')
                        except:
                            print(f"Log file not found or can't be opened: {self.log_filepath}")
                else:
                    for img_filename in imgs_without_anns:
                        img_path = osp.join(image_dir, img_filename)
                        if osp.exists(img_path):
                            os.remove(img_path)
                    coco["images"] = [image for image in coco["images"] if image["file_name"] not in imgs_without_anns]
                    _reload_coco(coco_file_path, coco)
                    imgs_without_anns = [
                        img["file_name"] for img in coco["images"] if not any(ann["image_id"] == img["id"]
                                                                              for ann in coco["annotations"])]
                    if len(imgs_without_anns) > 0:
                        raise Exception("Auto-fix: failure. Failed to remove imgs without anns from the coco file.")
                    log.debug(f"Auto-fix: removed all images without annotations.")
                    # since images were deleted, the validation needs to run again for dataset_size and size_in_bytes
                    return self.validate_dataset()
            category_ids = [cat["id"] for cat in coco["categories"]]
            image_ids = [img["id"] for img in coco["images"]]
            ann_ids = [ann["id"] for ann in coco["annotations"]]
            ann_img_ids = [ann["image_id"] for ann in coco["annotations"]]
            ann_cat_ids = [ann["category_id"] for ann in coco["annotations"]]

            if len(category_ids) != len(set(category_ids)):
                messages.append({'type': 'error',
                                 'message': f'The annotation file "{coco_file_name}" contains duplicate category IDs. '
                                            f'Verify that all categories[N].id are unique.'})

            if len(image_ids) != len(set(image_ids)):
                messages.append({'type': 'error',
                                 'message': f'The annotation file "{coco_file_name}" contains duplicate image IDs. '
                                            f'Verify that all images[N].id are unique.'})

            if len(ann_ids) != len(set(ann_ids)):
                messages.append({'type': 'error',
                                 'message': f'The annotation file "{coco_file_name}" contains duplicate annotation IDs. '
                                            f'Verify that all annotations[N].id are unique.'})

            if not set(ann_img_ids).issubset(set(image_ids)):
                messages.append({'type': 'error',
                                 'message': f'The annotation file "{coco_file_name}" contains annotations with '
                                            f'non-existent image IDs: '
                                            f'{list(set(ann_img_ids).difference(set(image_ids)))}. '
                                            f'Verify all values of annotations[N].image_id are listed under '
                                            f'images[M].id in "{coco_file_name}".'})
            if not set(ann_cat_ids).issubset(set(category_ids)):
                messages.append({'type': 'error',
                                 'message': f'The annotation file "{coco_file_name}" contains annotations with '
                                            f'non-existent category IDs: '
                                            f'{list(set(ann_cat_ids).difference(set(category_ids)))}, '
                                            f'where the allowed values are {category_ids}. Verify all vallues of '
                                            f'annotations[N].category_id are listed under categories[M].id '
                                            f'in "{coco_file_name}".'})

        except Exception as e:
            messages.append({'type': 'error',
                             'message': f'The annotation file "{coco_file_name}" is not formatted correctly: {e}.'})

        return messages

    def check_for_duplicate_images(self, images_dir):
        hashes = dict()
        duplicate_count = 0

        for path in Path(images_dir).rglob('*'):
            if osp.isfile(path):
                with open(path, 'rb') as file:
                    file_hash = hashlib.sha256(file.read()).hexdigest()
                    if file_hash in hashes.keys():
                        duplicate_count += 1
                    if file_hash not in hashes:
                        hashes[file_hash] = []
                    hashes[file_hash].append(path)

        if self.log_filepath is not None:
            try:
                with open(self.log_filepath, 'a') as file:
                    for hash_images in hashes.values():
                        if len(hash_images) > 1:
                            relpaths = [osp.relpath(path, start=images_dir) for path in hash_images]
                            file.write(f'Images {relpaths} are duplicate.\n')
            except:
                print(f"Log file not found or can't be opened: {self.log_filepath}")

        if duplicate_count > 0:
            return [{'type': 'warning',
                     'message': f'There are {duplicate_count} duplicate images (with same content, but different name) in your dataset. Check the '
                                f'"dataset validator log" file in the Dataset Analysis job to see details about those images.'}]
        else:
            return []

    def check_for_split_leakage(self, ann_path_1: str, ann_path_2: str, split_name_1: str, split_name_2: str,
                                duplicate_threshold_for_error: float = 0.03):
        try:
            with open(ann_path_1, "r") as f:
                coco1 = json.load(f)
            with open(ann_path_2, "r") as f:
                coco2 = json.load(f)

            images1 = [img["file_name"] for img in coco1["images"]]
            images2 = [img["file_name"] for img in coco2["images"]]

            leaked_images = set(images1).intersection(set(images2))
            if len(leaked_images) > 0:
                message_type = 'warning'
                smaller_split = split_name_1 if len(images1) < len(images2) else split_name_2
                leaked_percentage_of_smaller = len(leaked_images) / min(len(images1), len(images2))
                if leaked_percentage_of_smaller > duplicate_threshold_for_error and "train" in [split_name_1, split_name_2]:
                    message_type = 'error'

                with open(self.log_filepath, 'a') as file:
                    for img in leaked_images:
                        file.write(
                            f'Image "{img}" is contained in both the "{split_name_1}" and "{split_name_2}" split.\n')
                return [{'type': message_type,
                         'message': f'Leakage was found between the "{split_name_1}" and "{split_name_2}" dataset splits as {len(leaked_images)} images (which represents {round(leaked_percentage_of_smaller * 100, 2)}% of the smaller "{smaller_split}" split) are duplicated between them.'}]
            return []
        except:
            return []

    def check_split_image_duplicates(self, ann_path: str):
        try:
            coco_file_name = osp.basename(ann_path)
            with open(ann_path, "r") as f:
                coco = json.load(f)
            images = [img["file_name"] for img in coco["images"]]
            duplicates = [(item, count) for item, count in Counter(images).items() if count > 1]
            if len(duplicates) > 0:
                with open(self.log_filepath, 'a') as file:
                    for img in duplicates:
                        file.write(
                            f'Image "{img[0]}" is duplicated {img[1]} times in the "{coco_file_name}" annotation file.\n')
                return [{'type': 'warning',
                         'message': f'{len(duplicates)} images are duplicated in the {coco_file_name} annotation file.'}]
            return []
        except:
            return []

    def validate_split_sizes(self, dataset_infos_path: str, split_names: str, annotations_dir: str, images_dir: str):
        split_messages = []
        with open(dataset_infos_path, "r") as f:
            dataset_infos_json: dict = json.load(f)
            dataset_info = dataset_infos_json[list(dataset_infos_json.keys())[0]]

        for split_name in split_names:
            try:
                split_dict = dataset_info["splits"][split_name]
                split_file_path = osp.join(annotations_dir, split_dict["dataset_name"])
                with open(split_file_path) as file:
                    coco_dict = json.load(file)

                real_num_examples = _calculate_split_num_imgs(coco_dict, images_dir)
                if "num_examples" in split_dict:
                    if type(split_dict["num_examples"]) == int:
                        if real_num_examples != split_dict["num_examples"]:
                            if not self.auto_fix:
                                split_messages.append({'type': 'warning',
                                                'message': f'"dataset_infos.json" shows {split_dict["num_examples"]} as number or images in split "{split_name}", but {real_num_examples} images were found in the dataset root directory.'})
                            else:
                                split_dict["num_examples"] = real_num_examples
                                _reload_dataset_infos(dataset_infos_path, dataset_infos_json)
                                log.debug(f"Auto-fix: changed num_examples for split {split_name} to {real_num_examples}")
                    else:
                        if not self.auto_fix:
                            split_messages.append({'type': 'warning',
                                            'message': f'"dataset_infos.json" doesn\'t contain a valid entry for "num_examples" for split "{split_name}", {real_num_examples} images were found in the dataset root directory.'})
                        else:
                            split_dict["num_examples"] = real_num_examples
                            _reload_dataset_infos(dataset_infos_path, dataset_infos_json)
                            log.debug(f"Auto-fix: added num_examples for split {split_name}: {real_num_examples}")
                else:
                    if not self.auto_fix:
                        split_messages.append({'type': 'warning',
                                        'message': f'"dataset_infos.json" doesn\'t contain an entry for "num_examples" for split "{split_name}".'})
                    else:
                        split_dict["num_examples"] = real_num_examples
                        _reload_dataset_infos(dataset_infos_path, dataset_infos_json)
                        log.debug(f"Auto-fix: added num_examples for split {split_name}: {real_num_examples}")

                real_bytes = _calculate_split_size(coco_dict, images_dir)
                if "num_bytes" in split_dict:
                    if type(split_dict["num_bytes"]) == int:
                        if real_bytes != split_dict["num_bytes"]:
                            if not self.auto_fix:
                                split_messages.append({'type': 'warning',
                                                'message': f'"dataset_infos.json" shows {split_dict["num_bytes"]} B as size of split "{split_name}", but real split size was calculated as {real_bytes} B.'})
                            else:
                                split_dict["num_bytes"] = real_bytes
                                _reload_dataset_infos(dataset_infos_path, dataset_infos_json)
                                log.debug(f"Auto-fix: changed num_bytes for split {split_name} to {real_bytes}")
                    else:
                        if not self.auto_fix:
                            split_messages.append({'type': 'warning',
                                            'message': f'"dataset_infos.json" doesn\'t contain a valid entry for "num_bytes" for split "{split_name}", real split size was calculated as {real_bytes} B.'})
                        else:
                            split_dict["num_bytes"] = real_bytes
                            _reload_dataset_infos(dataset_infos_path, dataset_infos_json)
                            log.debug(f"Auto-fix: added num_bytes for split {split_name}: {real_bytes}")
                else:
                    if not self.auto_fix:
                        split_messages.append({'type': 'warning',
                                        'message': f'"dataset_infos.json" doesn\'t contain an entry for "num_bytes" for split "{split_name}".'})
                    else:
                        split_dict["num_bytes"] = real_bytes
                        _reload_dataset_infos(dataset_infos_path, dataset_infos_json)
                        log.debug(f"Auto-fix: added num_bytes for split {split_name}: {real_bytes}")
            except:
                split_messages.append({'type': 'error',
                                     'message': f'Couldn\'t verify size and number of images for split "{split_name}".'})

        return split_messages

def _count_imgs_in_dir(directory: str) -> int:
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']

    image_count = 0
    for root, _, files in os.walk(directory):
        for file in files:
            if os.path.splitext(file)[1].lower() in image_extensions:
                image_count += 1

    return image_count

def _calculate_dir_size(directory: str) -> int:
    total_size = 0
    for dirpath, _, filenames in os.walk(directory):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            total_size += os.path.getsize(filepath)

    return total_size

def _calculate_split_num_imgs(coco_dict: dict, images_dir: str):
    img_count = 0
    for image in coco_dict["images"]:
        if osp.exists(osp.join(images_dir, image["file_name"])):
            img_count = img_count + 1
    return img_count

def _calculate_split_size(coco_dict: dict, images_dir: str):
    size_bytes = 0
    for image in coco_dict["images"]:
        if osp.exists(osp.join(images_dir, image["file_name"])):
            size_bytes = size_bytes + osp.getsize(osp.join(images_dir, image["file_name"]))
    return size_bytes

def _get_first_image_from_dir(image_dir: str) -> Optional[str]:
    for subdir, dirs, files in os.walk(image_dir):
        for file in files:
            # Check for image file extensions. You can add or remove as needed.
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                return os.path.join(subdir, file)

    return None

def _reload_dataset_infos(dataset_infos_path: str, dataset_info_dict: dict) -> None:
    with open(dataset_infos_path, 'w') as file:
        json.dump(dataset_info_dict, file, indent=4)

def _reload_coco(coco_file_path: str, coco_dict: dict) -> None:
    with open(coco_file_path, 'w') as file:
        json.dump(coco_dict, file, indent=4)

def validate_cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--dataset_path", help="Path to the root directory of the dataset.", type=str,
                        required=True)
    # parser.add_argument("-w", "--working_dir", help="Working directory for logs.", type=str, required=False,
    #                     default=None)
    parser.add_argument('--auto-fix', '-af', action='store_true', default=False,
                        help='Auto-fix smaller issues about your dataset. Resolves most warnings.')
    parser.add_argument('--verbose', '-v', action='count', default=0,
                        help="Verbosity level: -v, -vv")
    # parser.add_argument("-a", "--annotations_required",
    #                     help="Whether the dataset is required to have annotations. Defaults to True.", type=bool,
    #                     required=False, default=True)

    args, _ = parser.parse_known_args()

    print(f'AptosConnector (v{pkg_resources.get_distribution("aptosconnector").version}) - dataset validation utility'.center(100))

    if args.verbose:
        print(f"Validating dataset with args: {args}.")

    dataset_path = args.dataset_path
    auto_fix = args.auto_fix

    dataset_validator = DatasetValidator(dataset_root_dir=dataset_path, working_dir=dataset_path, auto_fix=auto_fix)
    # messages = dataset_validator.validate_dataset(args.annotations_required)
    messages = dataset_validator.validate_dataset()


    print('\n'+f" Messages: ".center(100, '-'))
    for msg in messages:
        print(f"{msg.get('type', 'UNKNOWN').upper()}: {msg.get('message', 'UNKNOWN')}")

    print('\n'+f" Summary: ".center(100, '-'))
    dataset_validator.create_validation_mark()

if __name__ == "__main__":
    validate_cli()