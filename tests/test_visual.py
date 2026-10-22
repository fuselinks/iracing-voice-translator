import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from ivt.config import Config
from ivt.windows import WindowsChat

class VisualTests(unittest.TestCase):
    def test_distinct_templates(self):
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder)
            Image.new('L',(40,20),20).save(folder/'closed.png')
            Image.new('L',(40,20),200).save(folder/'open.png')
            chat=WindowsChat(Config())
            chat.capture=lambda:Image.new('L',(40,20),200)
            with patch('ivt.windows.DATA',folder):
                self.assertTrue(chat.opened());self.assertFalse(chat.closed())
                chat.capture=lambda:Image.new('L',(40,20),80)
                self.assertFalse(chat.opened());self.assertFalse(chat.closed())
    def test_identical_templates_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder)
            for state in ['open','closed']:Image.new('L',(40,20),100).save(folder/(state+'.png'))
            chat=WindowsChat(Config());chat.capture=lambda:Image.new('L',(40,20),100)
            with patch('ivt.windows.DATA',folder):
                self.assertFalse(chat.opened());self.assertFalse(chat.closed())

if __name__=='__main__':unittest.main()
