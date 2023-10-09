from typing import List
import subprocess
import sys 
import logging as log
import os, os.path as osp
from aptosconnector.utils import file_sha256
import re
import json 
import math
import uuid
from tqdm import tqdm
import argparse

def normalize_ds_name(name: str):
    return re.sub('[^a-zA-Z0-9_\.-]', '', name)

def get_sha(text):
    ''' 
    Example:
    Validation passed: bc81a84a510d7452bc1798af3a0b4dc93a50f94c79d807fe2f26e53adb3b5790
    '''
    try:
        sha = re.findall('Validation passed: ([0-9a-z]{64})', text)[0]
        return sha
    except:
        return None

def dataset_check(ds_root):
    ds_infos = osp.join(ds_root, 'dataset_infos.json')
    validator_log_path = osp.join(ds_root, 'dataset_validator_log.txt')

    if not osp.exists(ds_infos):
        print(f'Dataset boiler plate not found: {ds_infos}')
        return False
        
    expected_sha = file_sha256(ds_infos)

    with open(validator_log_path) as fp:
        text = fp.read()

    marked_sha = get_sha(text)
    if marked_sha is None:
        print('Dataset validation mark not found. Please run validation script first.')
        return False
    
    if expected_sha != marked_sha:
        print(f'Validation marks mismatch. Expected {expected_sha}, fonud {marked_sha}')
        return False
    
    return True

def check_s3_access(account_id):

    if not is_valid_uuid(account_id):
        print('Provided `account id` does not have a correct format. It should be a valid UUID e.g. "461b1b66-8787-11ed-aff3-07f20767316e" ')

    cmd = ['aws', 's3',  'ls', f's3://aptos-data/account/{account_id}/datasets/']

def upload_s3(account_id: str, ds_root: str, verbose: bool = False):

    if not dataset_check(ds_root):
        exit(1)
    
    if not check_s3_access(account_id):
        exit(1)

    with open(osp.join(ds_root, 'dataset_infos.json')) as fp:
        ds_infos = json.load(fp)
    
    ds_name = normalize_ds_name(list(ds_infos.keys())[0])
    s3_uri = f"s3://aptos-da2ta/account/{account_id}/datasets/{ds_name}"
    print(s3_uri)

    num_files, size = _count_files(ds_root) #len([name for name in os.listdir('.') if os.path.isfile(name)])
    print(f'Found {num_files} files in the dataset: {_convert_size(size)}')

    cmd = ['aws', 's3', 'sync', ds_root, s3_uri]
    if verbose:
        print('Running CLI command:' + ' '.join(cmd))   

    process = subprocess.Popen(
        cmd,
        env=None,
        cwd=ds_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        bufsize=1
    )
    # output = []

    files = 0
    with tqdm(total=num_files, position=1) as pbar:
        pbar2 = tqdm(bar_format='{desc}', position=0)
        while True:
            line = process.stdout.readline()

            if not line:
                break
            elif line.startswith('upload: '):
                files += 1
                pbar.update(1)
                try:
                    file = 'Uploading file: ', line[8:].split(' to ')[0]
                    pbar2.set_description(file)
                except:
                    pass
                
            if verbose:
                sys.stdout.write(line.strip() + "\n")

            # output.append(line.strip())

    process.wait()
    if process.poll() != 0:
        raise CLICommandError("".join(process.stderr.readlines()))

    # return output

def _count_files(folder: str):
    total = 0
    size = 0
    for root, _, files in os.walk(folder):
        total += len(files)
        size += sum((osp.getsize(osp.join(root, f)) for f in files))
    return total, size

def _convert_size(size_bytes):
   if size_bytes == 0:
       return "0B"
   size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
   i = int(math.floor(math.log(size_bytes, 1024)))
   p = math.pow(1024, i)
   s = round(size_bytes / p, 2)
   return "%s %s" % (s, size_name[i])


class CLICommandError(Exception):
    """Exception raised if CLI command produced error."""
    pass


def is_valid_uuid(value):
    try:
        uuid.UUID(str(value))

        return True
    except ValueError:
        return False

# print(is_valid_uuid('461b1b66-8787-11ed-aff3-07f20767316e'))
# upload_s3('461b1b66-8787-11ed-aff2-06f20767316e' ,'/home/jeremi/datasets/tf_test')

def main_cli():

    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--dataset_path", help="Path to the root directory of the dataset.", type=str,
                        required=True)
    parser.add_argument("-id", "--account_id", help="Aptos `account id` in UUID format", type=str,
                        required=True)
    parser.add_argument('--verbose', '-v', action='count', default=0,
                        help="Verbosity level: -v, -vv")

    args = parser.parse_args()
    print(args)

    if args.verbose == 1:
        log.getLogger().setLevel(log.INFO)
        print(f"{' Logging level: INFO ':=^30}")
    elif args.verbose >= 2:
        log.getLogger().setLevel(log.DEBUG)
        print(f"{' Logging level: DEBUG ':=^30}")

    upload_s3(
        account_id = args.account_id,
        ds_root = args.dataset_path,
        verbose = args.verbose
    )

if __name__ == "__main__":
    main_cli()
