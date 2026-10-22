import unittest
from unittest.mock import Mock,patch
from types import SimpleNamespace
from ivt.config import Config
from ivt.engine import Engine

class EngineTests(unittest.TestCase):
    def segment(self,text='Sorry, my mistake.'):
        return SimpleNamespace(text=text,no_speech_prob=0.1,avg_logprob=-0.2)
    def test_direct_task(self):
        engine=Engine(Config());engine.model=Mock()
        engine.model.transcribe.return_value=([self.segment()],None)
        source,output,times=engine.process('local.wav')
        self.assertEqual(output,'Sorry, my mistake.')
        self.assertEqual(engine.model.transcribe.call_args.kwargs['language'],'pl')
        self.assertEqual(engine.model.transcribe.call_args.kwargs['task'],'translate')
        self.assertEqual(times['translation_s'],0)
    def test_polish_task(self):
        engine=Engine(Config(engine='polish'));engine.model=Mock()
        engine.model.transcribe.return_value=([self.segment('Mój błąd.')],None)
        self.assertEqual(engine.process('local.wav')[1],'Mój błąd.')
        self.assertEqual(engine.model.transcribe.call_args.kwargs['task'],'transcribe')
    def test_low_confidence(self):
        engine=Engine(Config());engine.model=Mock()
        segment=self.segment();segment.no_speech_prob=0.99
        engine.model.transcribe.return_value=([segment],None)
        self.assertEqual(engine.process('local.wav')[1],'')
    def test_deferred_cuda_error_falls_back(self):
        engine=Engine(Config(device='auto'));engine.model=Mock();engine.actual_device='cuda'
        def broken():
            raise RuntimeError('Missing CUDA library')
            yield
        engine.model.transcribe.return_value=(broken(),None)
        replacement=Mock();replacement.transcribe.return_value=([self.segment()],None)
        with patch('faster_whisper.WhisperModel',return_value=replacement) as factory:
            self.assertEqual(engine.process('local.wav')[1],'Sorry, my mistake.')
            self.assertEqual(factory.call_args.kwargs['device'],'cpu')
            self.assertEqual(engine.actual_device,'cpu')

if __name__=='__main__':unittest.main()
