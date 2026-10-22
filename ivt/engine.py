import os
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
os.environ['HF_HUB_DISABLE_IMPLICIT_TOKEN'] = '1'
import logging
import time
import re
import numpy as np
from .config import DATA
from . import cuda

log = logging.getLogger(__name__)
PROMPT_TRANSLATE = 'iRacing, apex, braking point, blue flags, pit entry, inside, outside, rejoin, track limits.'
PROMPT_TRANSCRIBE = 'Rozmowa kierowców w wyścigu iRacing: wewnętrzna, zewnętrzna, hamowanie, zakręt, niebieskie flagi, pit, prosta, okrążenie.'
# Typical Whisper output for silence/noise (YouTube subtitle credits and sign-offs), Polish and English.
HALLUCINATION_PATTERNS = re.compile('|'.join([
    r'thanks? (you )?for watching', r'thank you for (your )?(attention|listening|viewing)', r'(please )?(like and )?subscribe',
    r'(subtitles?|captions?|transcri\w*|translat\w*|napisy\w*|tłumacz\w*) (by|made by|created by|wykona\w*|stworz\w*|przygotowa\w*|przez|robione)',
    r'amara\s*\.?\s*org', r'\bnapisy\b', r'dzi[eę]kuj[eę] za (uwag[eę]|obejrzenie|ogl[aą]danie|wys[lł]uchanie)', r'dzi[eę]ki za (obejrzenie|ogl[aą]danie)',
    r'zasubskrybuj', r'subskrybuj', r'www\.\S+', r'\bcopyright\b',
]), re.IGNORECASE)
HALLUCINATION_EXACT = {'you', 'bye', 'bye bye', 'thank you', 'thank you very much', 'thanks', 'so', 'oh', 'ah', 'uh', 'um', 'hmm',
                       'mhm', 'the end', 'dziękuję', 'dzięki', 'do widzenia', 'koniec'}

def words(text):
    return re.sub(r"[^\w' ]+", ' ', text.lower()).split()

def is_hallucination(text, prompt=''):
    normalized = ' '.join(words(text))
    if not normalized:
        return True
    if HALLUCINATION_PATTERNS.search(text) or normalized in HALLUCINATION_EXACT:
        return True
    # The decoder sometimes echoes a chunk of the initial prompt when it hears nothing.
    return len(normalized.split()) >= 4 and normalized in ' '.join(words(prompt))

def model_folder(target, download, fetch, legacy):
    """Plain folder download (no symlinks: Windows without Developer Mode refuses them, WinError 1314)."""
    marker = target / '.ivt-complete'
    if marker.exists():
        return str(target)
    if download:
        try:
            fetch(str(target))
        except Exception as exc:
            raise RuntimeError(f'Pobieranie modelu nie powiodło się ({target.name}): {exc}') from exc
        marker.write_text('ok', encoding='utf-8')
        return str(target)
    try:
        return legacy()  # symlinked Hugging Face cache used by earlier versions
    except Exception as exc:
        raise RuntimeError(f'Model {target.name} nie jest pobrany — użyj „Pobierz + załaduj model”') from exc

class Engine:
    def __init__(self, config):
        self.config = config
        self.model = None
        self.translator = None
        self.actual_device = ''
        self.warning = ''

    def _whisper(self, device, path):
        from faster_whisper import WhisperModel
        model = WhisperModel(path, device=device, compute_type='int8_float16' if device == 'cuda' else 'int8',
                             cpu_threads=4, num_workers=1)
        # cuBLAS/cuDNN are loaded lazily on the first decode: warm up now so GPU errors surface at load time.
        noise = (np.random.default_rng(0).standard_normal(16000) * 0.01).astype(np.float32)
        segments, _ = model.transcribe(noise, language='pl', beam_size=1, vad_filter=False, without_timestamps=True)
        list(segments)
        return model

    def load(self, download=False):
        state = cuda.setup()
        self.model, self.warning = None, ''
        from faster_whisper.utils import download_model
        path = model_folder(DATA / 'models' / self.config.model, download,
                            lambda target: download_model(self.config.model, output_dir=target),
                            lambda: download_model(self.config.model, local_files_only=True, cache_dir=str(DATA / 'models')))
        device = self.config.device
        if device in ('auto', 'cuda'):
            try:
                import ctranslate2
                if not ctranslate2.get_cuda_device_count():
                    raise RuntimeError('CTranslate2 nie widzi karty CUDA (sterownik NVIDIA?)')
                if state['missing']:
                    raise RuntimeError('brak bibliotek ' + ', '.join(state['missing']))
                self.model = self._whisper('cuda', path)
                device = 'cuda'
            except Exception as exc:
                if self.config.device == 'cuda':
                    raise RuntimeError(f'GPU nie działa: {exc}') from exc
                log.warning('CUDA unavailable, using CPU: %s', exc)
                self.warning = f'GPU NIE DZIAŁA — model działa na CPU (wolniej). Powód: {exc}'
                device = 'cpu'
        if self.model is None:
            self.model = self._whisper('cpu', path)
        self.actual_device = device
        if self.config.engine == 'two-stage':
            import torch
            torch.set_num_threads(2)
            from transformers import MarianMTModel, MarianTokenizer
            from huggingface_hub import snapshot_download
            name = 'Helsinki-NLP/opus-mt-pl-en'
            path = model_folder(DATA / 'translation' / 'opus-mt-pl-en', download,
                                lambda target: snapshot_download(name, local_dir=target),
                                lambda: snapshot_download(name, cache_dir=str(DATA / 'translation'), local_files_only=True))
            self.tokenizer = MarianTokenizer.from_pretrained(path)
            self.translator = MarianMTModel.from_pretrained(path).eval()

    def process(self, audio):
        if self.model is None:
            raise RuntimeError('Najpierw załaduj model')
        start = time.perf_counter()
        task = 'translate' if self.config.engine == 'direct' else 'transcribe'
        prompt = PROMPT_TRANSLATE if task == 'translate' else PROMPT_TRANSCRIBE
        segments, _ = self.model.transcribe(audio, language='pl', task=task, beam_size=3, vad_filter=True,
            condition_on_previous_text=False, temperature=0, initial_prompt=prompt)
        kept = [s.text.strip() for s in segments if s.no_speech_prob < 0.6 and s.avg_logprob > -1.0]
        kept = [t for t in kept if not is_hallucination(t, prompt)]
        text = ' '.join(kept).strip()
        if text and is_hallucination(text, prompt):
            text = ''
        speech_time = time.perf_counter() - start
        source, output = text, text
        translate_time = 0.0
        if text and self.config.engine == 'two-stage':
            import torch
            start = time.perf_counter()
            with torch.inference_mode():
                sentences = [s for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
                inputs = self.tokenizer(sentences, return_tensors='pt', padding=True)
                translated = self.tokenizer.batch_decode(self.translator.generate(**inputs, max_new_tokens=160), skip_special_tokens=True)
                if len(translated) != len(sentences) or any(not s.strip() for s in translated):
                    raise RuntimeError('Tłumacz nie zwrócił wszystkich zdań')
                output = ' '.join(translated)
            translate_time = time.perf_counter() - start
        return source, output, {'speech_s': speech_time, 'translation_s': translate_time}
