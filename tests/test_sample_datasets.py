# the inclusion of the tests module is not meant to offer best practices for
# testing in general, but rather to support the `find_packages` example in
# setup.py that excludes installing the "tests" package

import unittest

import aptosconnector
from aptosconnector.validate import DatasetValidator
import os.path as osp
import tempfile
import logging as log

class TestSimple(unittest.TestCase):

    def test_classification(self):

        pkg_path = osp.dirname(aptosconnector.__file__)
        ds_path = osp.join(pkg_path, '..', '..', 'sample_datasets', 'aptos_classification_sample')

        with tempfile.TemporaryDirectory() as tmp:
            dsv = DatasetValidator(ds_path, tmp)
            msgs, _ = dsv.validate_dataset()
            log.info(msgs)
            # assert that there are not warning/error messages
            self.assertEqual(len(msgs), 0)
            
    def test_object_detection(self):

        pkg_path = osp.dirname(aptosconnector.__file__)
        ds_path = osp.join(pkg_path, '..', '..', 'sample_datasets', 'aptos_objectdetection_sample')

        with tempfile.TemporaryDirectory() as tmp:
            dsv = DatasetValidator(ds_path, tmp)
            msgs, _ = dsv.validate_dataset()
            log.info(msgs)
            # assert that there are not warning/error messages
            self.assertEqual(len(msgs), 0)

    def test_keypoint_detection(self):

        pkg_path = osp.dirname(aptosconnector.__file__)
        ds_path = osp.join(pkg_path, '..', '..', 'sample_datasets', 'aptos_keypoints_sample')

        with tempfile.TemporaryDirectory() as tmp:
            dsv = DatasetValidator(ds_path, tmp)
            msgs, _ = dsv.validate_dataset()
            log.info(msgs)
            # assert that there are not warning/error messages
            self.assertEqual(len(msgs), 0)
if __name__ == '__main__':
    log.getLogger().setLevel(log.INFO)
    unittest.main()
