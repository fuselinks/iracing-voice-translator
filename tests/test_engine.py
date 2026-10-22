import unittest
from unittest.mock import Mock,patch
from types import SimpleNamespace
from ivt.config import Config
import tempfile
from pathlib import Path
from ivt.engine import Engine, model_folder

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
    def test_model_folder(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'small';fetched=[]
            def fetch(path):fetched.append(path);Path(path).mkdir(parents=True,exist_ok=True)
            def legacy():raise OSError('not cached')
            with self.assertRaisesRegex(RuntimeError,'nie jest pobrany'):model_folder(target,False,fetch,legacy)
            self.assertEqual(model_folder(target,True,fetch,legacy),str(target))
            self.assertEqual(model_folder(target,False,fetch,legacy),str(target));self.assertEqual(len(fetched),1)
            self.assertEqual(model_folder(Path(folder)/'old',False,fetch,lambda:'cache-path'),'cache-path')
            def symlink_error(path):raise OSError('[WinError 1314] symlink')
            with self.assertRaisesRegex(RuntimeError,'Pobieranie modelu'):model_folder(Path(folder)/'x',True,symlink_error,legacy)
    def test_low_confidence(self):
        engine=Engine(Config());engine.model=Mock()
        segment=self.segment();segment.no_speech_prob=0.99
        engine.model.transcribe.return_value=([segment],None)
        self.assertEqual(engine.process('local.wav')[1],'')
    def load(self,device,cuda_ok,missing=()):
        engine=Engine(Config(device=device))
        def whisper(dev,path):
            if dev=='cuda' and not cuda_ok:raise RuntimeError('cublas64_12.dll is not found')
            return Mock(name=dev)
        engine._whisper=whisper
        with patch('ivt.cuda.setup',return_value={'dirs':[],'missing':list(missing)}),             patch('ctranslate2.get_cuda_device_count',return_value=1):
            engine.load()
        return engine
    def test_gpu_used_without_warning(self):
        engine=self.load('auto',True)
        self.assertEqual(engine.actual_device,'cuda');self.assertEqual(engine.warning,'')
    def test_auto_falls_back_with_visible_warning(self):
        with self.assertLogs('ivt.engine','WARNING'):engine=self.load('auto',False)
        self.assertEqual(engine.actual_device,'cpu');self.assertIn('GPU NIE DZIAŁA',engine.warning)
        self.assertIn('cublas',engine.warning)
    def test_missing_libraries_reported(self):
        with self.assertLogs('ivt.engine','WARNING'):engine=self.load('auto',True,['cudnn64_9.dll'])
        self.assertIn('cudnn64_9.dll',engine.warning)
    def test_explicit_cuda_raises(self):
        with self.assertRaises(RuntimeError):self.load('cuda',False)
    def test_decode_error_is_not_hidden_by_cpu_reload(self):
        engine=Engine(Config(device='auto'));engine.model=Mock();engine.actual_device='cuda'
        def broken():
            raise RuntimeError('CUDA failed')
            yield
        engine.model.transcribe.return_value=(broken(),None)
        with patch('faster_whisper.WhisperModel') as factory:
            with self.assertRaises(RuntimeError):engine.process('local.wav')
            factory.assert_not_called()
        self.assertEqual(engine.actual_device,'cuda')

if __name__=='__main__':unittest.main()
