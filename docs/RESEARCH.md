# Decyzje techniczne i referencje

Sprawdzenie dokumentacji: 22.10.2026. Implementacja własna; bez kopiowania kodu projektów referencyjnych.

- [ChatShift](https://github.com/toffenloffen/ChatShift): rozdzielenie wejścia głosowego, tłumaczenia i adaptera gry. Dokument TECHNICAL_DETAILS wymaga wcześniejszego otwarcia edytowalnego pola, opisuje Ctrl+A/C/V i ograniczenia schowka. Nasz adapter otwiera czat i nie używa schowka. Aktualny plik LICENSE to „ChatShift Free Use and Attribution License 1.0”, z ograniczeniem niezależnych produktów pochodnych, mimo etykiety MIT w widoku repozytorium. Nie wykorzystano kodu.
- [STTC-EVO](https://github.com/chopsuey2/sttc-evo): opis wskazuje Python, Deepgram i Gemini. W aktualnym widoku main dostępny był plik LICENSE (AGPL-3.0), bez kodu programu; nie dało się zweryfikować implementacji przycisków i klawiatury. Nie przyjęto jej działania w iRacing ani lokalnego przetwarzania.
- [Crew Chief](https://mr_belowski.gitlab.io/CrewChiefV4/VoiceRecognition_FreeDictationChatMessages.html): start chat macro → znaki → end chat macro. Dokumentuje T/C, następnie Enter. Wykorzystano ideę sekwencji, nie kod.
- [iRacing](https://support.iracing.com/support/solutions/articles/31000170165-pit-macros-chat-commands): T otwiera czat podczas jazdy; R odpowiada prywatnie. Prefiksy /, @, # mogą uruchamiać funkcje gry. Aplikacja blokuje początkowe prefiksy komend; nie ucina automatycznie długich wypowiedzi, aby nie zmienić znaczenia. Limit 180 jest konserwatywną wartością konfiguracyjną, a nie potwierdzonym limitem protokołu.
- [SimHub Keyboard Emulator](https://github.com/SHWotever/SimHub/wiki/Additional-Plugin--Keyboard-Emulator-Plugin): alternatywne mapowanie przycisku do F9; konieczne zdarzenia key-down i key-up, nie krótki impuls w trybie PTT.
- [Whisper](https://github.com/openai/whisper): multilingual translate do angielskiego; turbo nie jest przeznaczony do tłumaczenia.
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper): CTranslate2, int8 CPU / int8_float16 CUDA, VAD i model pozostający w RAM/VRAM. Dokumentowane CUDA 12 i cuDNN 9; zgodność konkretnego sterownika i RTX 5070 Ti wymaga pomiaru na docelowym komputerze.

## Warianty

| Wariant | Zalety | Koszt / ryzyko |
|---|---|---|
| A: Whisper translate | Jeden model i jedno dekodowanie; domyślny medium | Brak osobnej polskiej transkrypcji; błędy nazw/negacji nadal możliwe |
| B: Whisper transcribe + Marian opus-mt-pl-en | Polski tekst dostępny osobno; wymienne tłumaczenie | Drugie dekodowanie, dodatkowy RAM i zależności Torch; Marian działa na CPU |
| Polish | Sama transkrypcja | Wiadomość pozostaje po polsku |

Medium wybrano jako punkt startowy, nie zwycięzcę pomiarów jakości. Test działania wszystkich trzech modeli w wariantach A/B na syntetycznej mowie i CPU opisano w [raporcie](TEST-REPORT.md); direct był szybszy. Nie wykonano pomiarów jakości, VRAM, FPS ani latencji na RTX 5070 Ti. Skrypt benchmark.py uruchamia small, medium i large-v3 z rozgrzewką oraz powtórzeniami, osobno dla A i B. Porównuj te same nagrania, ręcznie sprawdzając negacje, liczby, nazwiska i słownictwo wyścigowe. VRAM/FPS obserwuj zewnętrznie podczas sesji. Nie ma podstaw do obietnicy 1–2 sekund.

## Ograniczenie potwierdzania czatu

Gra nie udostępnia tu potwierdzenia odbioru. Lokalna weryfikacja obrazu ramki jest heurystyką; może odrzucić prawidłowy czat albo pomylić podobny obraz. Wymaga dwóch różnych wzorców przy tym samym HUD, DPI i rozdzielczości. Każde T/znak/Enter jest poprzedzone sprawdzeniem fokusu. Pomiędzy sprawdzeniem a wstrzyknięciem klawisza istnieje małe okno wyścigu systemowego; Windows nie zapewnia atomowego skierowania SendInput do konkretnego procesu. Nie jest to gwarancja bezbłędnego działania. Bez zgodności wzorca aplikacja odmawia wpisywania. Brak ingerencji w pamięć gry, hooków gry lub obchodzenia antycheat.

## Licencje zależności

Własny kod: MIT. faster-whisper/CTranslate2: MIT; Whisper: MIT; SDL/pygame-ce: zlib/LGPL (sprawdź notices konkretnego wydania); pynput/pystray: LGPL; sounddevice: MIT; NumPy: BSD; Pillow: HPND; psutil: BSD; Transformers: Apache-2.0; PyTorch: BSD. Model Marian ma własną kartę/licencję: https://huggingface.co/Helsinki-NLP/opus-mt-pl-en. Dystrybucja EXE musi zachować pliki licencyjne bibliotek (PyInstaller zbiera metadane w skrypcie budowania). Modele nie są dołączane do repozytorium.
