import os
import time
from .config import DATA

class Engine:
    def __init__(self, config):
        self.config = config
        self.model = None
        self.translator = None
        self.actual_device = ''

    def load(self, download=False):
        from faster_whisper import WhisperModel
        import ctranslate2
        device = self.config.device
        if device == 'auto':
            device = 'cuda' if ctranslate2.get_cuda_device_count() else 'cpu'
        kwargs = dict(download_root=str(DATA / 'models'), local_files_only=not download, cpu_threads=4, num_workers=1)
        try:
            self.model = WhisperModel(self.config.model, device=device, compute_type='int8_float16' if device == 'cuda' else 'int8', **kwargs)
        except Exception:
            if self.config.device != 'auto' or device != 'cuda':
                raise
            device = 'cpu'
            self.model = WhisperModel(self.config.model, device=device, compute_type='int8', **kwargs)
        self.actual_device = device
        if self.config.engine == 'two-stage':
            from transformers import MarianMTModel, MarianTokenizer
            name = 'Helsinki-NLP/opus-mt-pl-en'
            kwargs = dict(cache_dir=str(DATA / 'translation'), local_files_only=not download)
            self.tokenizer = MarianTokenizer.from_pretrained(name, **kwargs)
            self.translator = MarianMTModel.from_pretrained(name, **kwargs).eval()

    def process(self, audio):
        if self.model is None:
            raise RuntimeError('Najpierw załaduj model')
        start = time.perf_counter()
        task = 'translate' if self.config.engine == 'direct' else 'transcribe'
        segments, _ = self.model.transcribe(audio, language='pl', task=task, beam_size=3, vad_filter=True,
            condition_on_previous_text=False, temperature=0, initial_prompt='iRacing, apex, braking point, blue flags, pit entry, inside, outside, rejoin, track limits.')
        text = ' '.join(s.text.strip() for s in segments if s.no_speech_prob < 0.6 and s.avg_logprob > -1.0).strip()
        speech_time = time.perf_counter() - start
        source, output = text, text
        translate_time = 0.0
        if text and self.config.engine == 'two-stage':
            import torch
            start = time.perf_counter()
            with torch.inference_mode():
                inputs = self.tokenizer(text, return_tensors='pt')
                output = self.tokenizer.decode(self.translator.generate(**inputs, max_new_tokens=160)[0], skip_special_tokens=True)
            translate_time = time.perf_counter() - start
        return source, output, {'speech_s': speech_time, 'translation_s': translate_time}
