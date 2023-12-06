# AptosConnector

## Introduction

This package is provides commandline tools that validate and upload User datasets to the Aptos Edge ML patform.

## Installation

AptosConnector is currently supported on:
* Linux
* Windows 10/11
* macOS

### Prerequisites
* `AWS CLI v2`. For more information consult the installation guide: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
* `Python >=3.7` installation (you can use `conda` or virtual environments `venv`)
* `git` (if you intend to clone AptosConnector directly from github)

### Installing by cloning from GitHub

Start your terminal or command line.
```bash
# If using python venv or conda activate your environment e.g.:
conda activate aptos_env
```

Clone and install python package:
```bash
cd ~/ # Will install in user folder
git clone git@github.com:Eta-Compute/AptosConnector.git
cd AptosConnector
pip install -e .
```

### Installing via `pip`

~~~
Note: This modality is not supported yet
~~~

## User Guide

Currently the following functions are supported:
* AptosConnector setup (one-time only)
* Dataset validation
* Dataset upload

### Dataset Prepartion

In order to prepare your dataset, please follow our guide: [Dataset preparation guide](docs/dataset_preparation.md)

### AptosConnector Setup

This one-time only procedure will configure AptosConnector's access to Aptos platform. You will need to provide your `Aptos Group ID`, `Aptos AWS Access Key ID` and `Aptos AWS Secret Access Key`:

```
(aptos_env) user@ubuntu: aptos_setup
Welcome to AptosConnector one-time setup wizzard.
We'll get you started in just a few simple steps!
--------------------------------------------------
AWS CLI installation verified.
--------------------------------------------------
Aptos Group ID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXX
Aptos AWS Access Key ID: XXXXXXXXXXXXXXXXXXXX
Aptos AWS Secret Access Key: XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
--------------------------------------------------
Configuration successful!

Now you can use:
        `aptos_validate` to check your dataset for errors and verify Aptos interoperability
        `aptos_upload` to upload dataset to Aptos platform

```
Once configuration is done, you can proceed with dataset validation and upload

### Dataset Validation
Validates user dataset to endure conformity with Aptos dataset format. Any issues will be displayed to the user so that they can be correted prior to upload. If validation is passed succesfully your dataset will be signed and ready to upload. Note that you cannot upload the dataset without validating it first.
```
aptos_validate
usage: aptos_validate [-h] -d DATASET_PATH [--verbose]
```
Example usage:

```
(aptos_env) user@ubuntu:~$ aptos_validate -d ~/datasets/tf_test
                        AptosConnector (v0.0.1) - dataset validation utility

-------------------------------------------- Messages: ---------------------------------------------
WARNING: The dataset is missing the "thumbnail.jpg" file. Pick one image from the dataset, name it as "thumbnail.jpg" and place it inside the dataset root directory.
WARNING: There are 3 duplicate images (with same content, but different name) in your dataset. Check the "dataset validator log" file in the Dataset Analysis job to see details about those images.
WARNING: "dataset_infos.json" doesn't contain a valid entry for "num_examples" for split "train", 1222 images were found in the dataset root directory.

--------------------------------------------- Summary: ---------------------------------------------
No critical errors found
Creating dataset signature ...
Validation passed and signed: f3322dab7dccb61a66e611ee0dbaff1207b552b647bbb3d4066e6f953fc96ad1
```

### Dataset Upload

This utility will upload your dataset to Aptos.

```
(aptos_env) user@ubuntu:~$ aptos_upload -d ~/datasets/tf_test
                        AptosConnector (v0.0.1) - dataset validation utility

----------------------------------------------------------------------------------------------------
Veryfying dataset signature...
Done!
S3 access verified
Found 3693 files in the dataset: 505.73 MB

Uploading file: tfds/tf_test-validation.tfrecord-00000-of-00001
100%|███████████████████████████████████████████████████████████| 3693/3693 [02:25<00:00, 25.46it/s]
----------------------------------------------------------------------------------------------------
Upload complete. You can view your dataset at: https://aptos.training/datasets/XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXX/tf_test
```

## Running tests

```
# install tox test runner:
python -m pip install --user tox
python -m tox --help

# install developer dependencies of the package
cd [...]/AptosConnector
pip install -e .[dev]

# run tests
tox
```

## Developed by:

<img src="https://etacompute.com/wp-content/uploads/2021/09/eta-logo.svg" width="200">