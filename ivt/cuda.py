"""Make the pip-installed NVIDIA runtime (nvidia-cublas-cu12, nvidia-cudnn-cu12) visible to CTranslate2."""
import ctypes
import importlib.util
import logging
import os
import sys
from pathlib import Path

REQUIRED = ['cublas64_12.dll', 'cublasLt64_12.dll', 'cudnn64_9.dll']
log = logging.getLogger(__name__)
_handles = []
_state = None

def dll_dirs():
    """nvidia/*/bin directories from site-packages or from the PyInstaller bundle."""
    roots = []
    if getattr(sys, 'frozen', False):
        roots.append(Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent)))
    spec = importlib.util.find_spec('nvidia')
    if spec and spec.submodule_search_locations:
        roots += [Path(p).parent for p in spec.submodule_search_locations]
    found = []
    for root in roots:
        for path in sorted(root.glob('nvidia/*/bin')):
            if path.is_dir() and path not in found:
                found.append(path)
    return found

def setup():
    """Idempotent. Must run before ctranslate2 needs cuBLAS/cuDNN; returns a status dict."""
    global _state
    if _state is not None:
        return _state
    dirs = dll_dirs()
    for path in dirs:
        os.add_dll_directory(str(path))
    if dirs:
        # CTranslate2 loads cuBLAS/cuDNN (and cuDNN its sub-libraries) with plain LoadLibrary, which uses PATH.
        os.environ['PATH'] = os.pathsep.join([str(p) for p in dirs] + [os.environ.get('PATH', '')])
    missing = []
    for name in REQUIRED:
        candidates = [p / name for p in dirs if (p / name).exists()]
        try:
            _handles.append(ctypes.WinDLL(str(candidates[0]) if candidates else name))
        except OSError as exc:
            missing.append(f'{name} ({exc})')
    _state = {'dirs': [str(p) for p in dirs], 'missing': missing}
    if missing:
        log.warning('CUDA libraries not loadable: %s', missing)
    return _state

def describe():
    """Human-readable CUDA state for diagnostics; never raises."""
    state = setup()
    try:
        import ctranslate2
        count = ctranslate2.get_cuda_device_count()
        types = sorted(ctranslate2.get_supported_compute_types('cuda')) if count else []
    except Exception as exc:
        return f'CTranslate2 niedostępne: {exc}'
    lines = [f'Urządzenia CUDA (CTranslate2 {ctranslate2.__version__}): {count}']
    if types:
        lines.append('Typy obliczeń: ' + ', '.join(types))
    lines.append(f'Katalogi DLL NVIDIA: {len(state["dirs"])}')
    lines.append('Brakujące biblioteki: ' + ', '.join(state['missing']) if state['missing'] else 'cuBLAS 12 i cuDNN 9: załadowane')
    return '\n'.join(lines)
