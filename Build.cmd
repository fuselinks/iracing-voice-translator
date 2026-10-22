@echo off
cd /d "%~dp0"
.venv\Scripts\python -m pip install pyinstaller -r requirements-translation.txt
if errorlevel 1 goto fail
.venv\Scripts\python -m PyInstaller --noconfirm --windowed --onedir --name iRacingVoiceTranslator --collect-all faster_whisper --collect-all ctranslate2 --collect-all tokenizers --collect-all onnxruntime --collect-all pygame --collect-submodules pynput --hidden-import pystray._win32 --hidden-import transformers.models.marian.modeling_marian --hidden-import transformers.models.marian.tokenization_marian --collect-data transformers --collect-all sentencepiece --collect-data sacremoses --recursive-copy-metadata transformers --recursive-copy-metadata faster-whisper --copy-metadata sounddevice --copy-metadata pygame-ce --copy-metadata pynput --copy-metadata pystray --copy-metadata Pillow --copy-metadata numpy --copy-metadata psutil run.py
if errorlevel 1 goto fail
echo Build is in dist\iRacingVoiceTranslator. Keep the entire folder.
pause
exit /b
:fail
echo Build failed.
pause
