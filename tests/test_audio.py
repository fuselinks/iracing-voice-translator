import unittest
from unittest.mock import patch
import numpy as np
from ivt import audio
from ivt.audio import Recorder, find_microphone, microphones, resample, RATE
from ivt.config import Config

class FakeStream:
    def __init__(self,**kwargs):
        self.callback=kwargs['callback'];self.rate=kwargs['samplerate'];self.device=kwargs['device']
        self.started=False;self.closed=False
    def start(self):self.started=True
    def stop(self):self.started=False
    def close(self):self.closed=True

APIS=[{'name':'MME'},{'name':'Windows DirectSound'},{'name':'Windows WASAPI'}]
def dev(name,api,inputs=1,rate=44100.0):
    return {'name':name,'hostapi':api,'max_input_channels':inputs,'default_samplerate':rate}
# The same physical microphone exposed by three host APIs, as on the target PC.
DEVICES=[dev('Mapowanie dźwięku Microsoft - Input',0,2),dev('Mikrofon (USB Sound Device)',0,2),
    dev('Mikrofon zestawu słuchawkowego ',0),dev('Głośniki',0,0),
    dev('Mikrofon (USB Sound Device)',1,2),dev('Mikrofon zestawu słuchawkowego (A50 Mic)',1),
    dev('Mikrofon (USB Sound Device)',2,2,48000.0)]

def fake_query(index=None,kind=None):
    return DEVICES if index is None else DEVICES[index]

class DeviceTests(unittest.TestCase):
    def setUp(self):
        patcher=patch.multiple('ivt.audio.sd',query_devices=fake_query,query_hostapis=lambda:APIS)
        patcher.start();self.addCleanup(patcher.stop)
    def test_single_host_api_listing(self):
        mics=microphones()
        self.assertEqual([m.index for m in mics],[1,2])
        self.assertEqual(mics[1].label,'Mikrofon zestawu słuchawkowego (A50 Mic)')
    def test_duplicate_names_across_apis_are_not_ambiguous(self):
        # Regression: name-only lookup matched 3 entries and refused to record.
        self.assertEqual(find_microphone('Mikrofon (USB Sound Device)','MME').index,1)
        self.assertEqual(find_microphone('Mikrofon (USB Sound Device)','Windows WASAPI').index,6)
    def test_missing_microphone(self):
        with self.assertRaises(RuntimeError):find_microphone('Nieistniejący','MME')
    def test_default_microphone(self):self.assertIsNone(find_microphone('','MME'))

class AudioTests(unittest.TestCase):
    def start(self,rate_ok=True,**config):
        def check(**kwargs):
            if not rate_ok:raise RuntimeError('Invalid sample rate')
        patches=[patch('ivt.audio.sd.InputStream',side_effect=FakeStream),
            patch('ivt.audio.sd.check_input_settings',side_effect=check),
            patch('ivt.audio.sd.query_devices',return_value={'default_samplerate':48000.0}),
            patch('ivt.audio.find_microphone',return_value=None)]
        for p in patches:p.start();self.addCleanup(p.stop)
        recorder=Recorder();recorder.start(Config(**config))
        return recorder,recorder.stream
    def test_microphone_closed_until_explicit_start_and_after_stop(self):
        with patch('ivt.audio.sd.InputStream') as factory:
            Recorder();factory.assert_not_called()
        recorder,stream=self.start()
        self.assertTrue(stream.started);self.assertEqual(stream.rate,RATE)
        stream.callback(np.ones((320,1),dtype=np.float32)*0.1,320,None,None)
        audio=recorder.stop()
        self.assertEqual(len(audio),320);self.assertTrue(stream.closed)
        self.assertIsNone(recorder.stream);self.assertFalse(recorder.frames)
    def test_overflow_is_logged_and_recording_kept(self):
        recorder,stream=self.start()
        stream.callback(np.ones((320,1),dtype=np.float32)*0.1,320,None,None)
        with self.assertLogs('ivt.audio','WARNING') as logs:
            stream.callback(np.ones((320,1),dtype=np.float32)*0.1,320,None,'input overflow')
            audio=recorder.stop()
        self.assertEqual(len(audio),640);self.assertTrue(stream.closed)
        self.assertIn('input overflow',logs.output[0])
    def test_native_rate_fallback_is_resampled(self):
        recorder,stream=self.start(rate_ok=False)
        self.assertEqual(stream.rate,48000)
        stream.callback(np.zeros((48000,1),dtype=np.float32),48000,None,None)
        self.assertEqual(len(recorder.stop()),RATE)
    def test_resample_keeps_speech_band(self):
        t=np.arange(48000)/48000
        out=resample(np.sin(2*np.pi*1000*t).astype(np.float32),48000)
        self.assertEqual(out.dtype,np.float32);self.assertEqual(len(out),RATE)
        self.assertAlmostEqual(float(np.sqrt(np.mean(out[500:-500]**2))),0.707,delta=0.03)
        alias=resample(np.sin(2*np.pi*12000*t).astype(np.float32),48000)
        self.assertLess(float(np.sqrt(np.mean(alias[500:-500]**2))),0.05)

if __name__=='__main__':unittest.main()
