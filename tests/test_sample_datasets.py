# the inclusion of the tests module is not meant to offer best practices for
# testing in general, but rather to support the `find_packages` example in
# setup.py that excludes installing the "tests" package

import unittest
import aptosconnector
from aptosconnector.validate import DatasetValidator
import os.path as osp
import tempfile
import logging as log
import os


def _get_dataset_path() -> str:
    datasets_folder = 'sample_datasets'

    # first try where package is installed
    # this will work for local call of unittests
    ds_path = osp.abspath(osp.join(osp.dirname(aptosconnector.__file__), "..", "..", datasets_folder))
    if osp.exists(ds_path):
        print(ds_path)
        return ds_path

    # otherwise check current directory (this will work for tox)

    ds_path = osp.abspath(osp.join(os.getcwd(), datasets_folder))
    if osp.exists(ds_path):
        print(ds_path)
        return ds_path

    raise FileExistsError(f'`{datasets_folder}` cannot be located')


class TestSimple(unittest.TestCase):
    def test_classification(self):
        ds_path = osp.join(
            _get_dataset_path(), "aptos_classification_sample"
        )

        with tempfile.TemporaryDirectory() as tmp:
            dsv = DatasetValidator(ds_path, tmp)
            msgs = dsv.validate_dataset()
            log.info(msgs)
            # assert that there are not warning/error messages
            self.assertEqual(len(msgs), 0)

    def test_object_detection(self):
        ds_path = osp.join(
            _get_dataset_path(), "aptos_objectdetection_sample"
        )

        with tempfile.TemporaryDirectory() as tmp:
            dsv = DatasetValidator(ds_path, tmp)
            msgs = dsv.validate_dataset()
            log.info(msgs)
            # assert that there are not warning/error messages
            self.assertEqual(len(msgs), 0)

    def test_keypoint_detection(self):
        ds_path = osp.join(
            _get_dataset_path(), "aptos_keypoints_sample"
        )

        with tempfile.TemporaryDirectory() as tmp:
            dsv = DatasetValidator(ds_path, tmp)
            msgs = dsv.validate_dataset()
            log.info(msgs)
            # assert that there are not warning/error messages
            self.assertEqual(len(msgs), 0)


if __name__ == "__main__":
    log.getLogger().setLevel(log.INFO)
    unittest.main()
