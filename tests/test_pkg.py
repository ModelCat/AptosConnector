import unittest
import aptosconnector
import logging as log


class TestPkg(unittest.TestCase):
    def test_version_attr(self):
        self.assertTrue(hasattr(aptosconnector, "__version__"))
        self.assertIsInstance(aptosconnector.__version__, str)


if __name__ == '__main__':
    log.getLogger().setLevel(log.INFO)
    unittest.main()
