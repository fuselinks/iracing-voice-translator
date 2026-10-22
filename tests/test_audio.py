import unittest
from unittest.mock import patch
import numpy as np
from ivt.audio import Recorder
from ivt.config import Config

class FakeStream:
    def __init__(self,**kwargs):self.callback=kwargs['callback'];self.started=False;self.closed=False
    def start(self):self.started=True
    def stop(self):self.started=False
    def close(self):self.closed=True

class AudioTests(unittest.TestCase):
    def test_microphone_closed_until_explicit_start_and_after_stop(self):
        with patch('ivt.audio.sd.InputStream',side_effect=FakeStream) as factory:
            recorder=Recorder();factory.assert_not_called()
            recorder.start(Config());stream=recorder.stream
            self.assertTrue(stream.started)
            stream.callback(np.ones((320,1),dtype=np.float32)*0.1,320,None,None)
            audio=recorder.stop()
            self.assertEqual(len(audio),320);self.assertTrue(stream.closed)
            self.assertIsNone(recorder.stream);self.assertFalse(recorder.frames)
    def test_overflow_is_rejected_after_closing_microphone(self):
        with patch('ivt.audio.sd.InputStream',side_effect=FakeStream):
            recorder=Recorder();recorder.start(Config());stream=recorder.stream
            stream.callback(np.ones((320,1),dtype=np.float32),320,None,'overflow')
            with self.assertRaises(RuntimeError):recorder.stop()
            self.assertTrue(stream.closed)

if __name__=='__main__':unittest.main()
