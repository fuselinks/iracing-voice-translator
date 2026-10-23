# Decyzje techniczne i referencje

Aktualizacja: 22.10.2026. Implementacja własna; bez kopiowania kodu projektów referencyjnych.

## Czat: oficjalne iRacing SDK zamiast weryfikacji obrazu

Poprzednia wersja potwierdzała otwarcie czatu porównaniem wycinka ekranu z dwoma wzorcami (kalibracja ROI). Była to heurystyka zależna od HUD, DPI i trybu okna, wymagała ręcznej kalibracji i mogła się mylić. Usunięto ją w całości.

Teraz program używa mechanizmu z iRacing SDK (`irsdk_defines.h`, `irsdk_utils.cpp`):

- **Stan:** mapa pamięci `Local\IRSDKMemMapFileName`, otwierana tylko do odczytu (`FILE_MAP_READ`); nagłówek `int ver; int status; …`, bit `irsdk_stConnected = 1`. Nagłówek zawiera też `sessionInfoLen` (+16) i `sessionInfoOffset` (+20) — YAML sesji, z którego opcjonalnie bierzemy nazwę toru i nicki kierowców do słownika.
- **Polecenia:** `RegisterWindowMessageW("IRSDK_BROADCASTMSG")` i `SendNotifyMessageW(HWND_BROADCAST, msg, MAKELONG(irsdk_BroadcastChatComand=8, tryb), 0)`, tryby `irsdk_ChatCommand_BeginChat = 1`, `irsdk_ChatCommand_Cancel = 3`.
- **Sekwencja:** fokus `iRacingSim64DX11.exe` + SDK połączone → Cancel (czyści pole) → BeginChat → pauza → tekst → pauza → fokus → Enter. Każde przerwanie po pierwszym poleceniu kończy się Cancel.

SDK nie potwierdza doręczenia ani tego, że pole czatu jest otwarte — potwierdzenie pozostaje wzrokowe. Brak zapisu do pamięci gry, hooków w procesie gry i obchodzenia zabezpieczeń.

## Wpisywanie

`SendInput` z `KEYEVENTF_SCANCODE`: gry czytające raw input/DirectInput widzą prawdziwe scan code'y, a Windows wyprowadza z nich znaki w układzie wątku okna gry. Scan code z `VkKeyScanExW` + `MapVirtualKeyExW(MAPVK_VK_TO_VSC_EX)` dla `GetKeyboardLayout(wątek okna iRacing)`; Shift (i ewentualnie Ctrl+Alt dla AltGr) jako osobne scan code'y, w jednym wywołaniu `SendInput` na znak. Brak ścieżki Unicode/`VK_PACKET` — tę część gier ignoruje. Tekst jest najpierw sprowadzany do ASCII. Każdy znak jest sprawdzany przez `ToUnicodeEx` (bez zmiany stanu klawiatury): martwe klawisze (np. `~` w układzie polskim programisty) dostają spację, znaki niemożliwe w układzie blokują wysyłkę przed otwarciem czatu.

UIPI: Windows po cichu odrzuca `SendInput` do okna procesu o wyższej integralności (np. gra uruchomiona jako administrator), a funkcja zwraca sukces. Program sprawdza poziom uprawnień procesu okna i zgłasza ten przypadek.

Między sprawdzeniem fokusu a wstrzyknięciem klawisza zostaje małe okno wyścigu — Windows nie pozwala skierować `SendInput` do konkretnego procesu. Fokus jest sprawdzany przed każdym znakiem.

## Mikrofon

PortAudio pokazuje każde urządzenie raz na host API (MME, DirectSound, WASAPI, WDM-KS), więc wybór po nazwie był niejednoznaczny. Lista pokazuje tylko MME (zwykle przyjmuje 16 kHz mono; MME obcina nazwy do 31 znaków — etykieta jest uzupełniana nazwą z DirectSound). Zapamiętywana jest para nazwa + host API. Gdy 16 kHz jest odrzucone, nagranie idzie w częstotliwości natywnej i jest resamplowane (filtr okienkowany sinc + interpolacja). Flagi statusu callbacku (overflow) są logowane, a nagranie zostaje zachowane.

## Rozpoznawanie i tłumaczenie

- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) / CTranslate2: CUDA 12 + cuDNN 9. Biblioteki z kół PyPI `nvidia-cublas-cu12` i `nvidia-cudnn-cu12`; katalogi `nvidia/*/bin` trafiają do `os.add_dll_directory` i `PATH` przed załadowaniem modelu (także w EXE). Rozgrzewka przy ładowaniu ujawnia błędy bibliotek od razu. Brak cichego przejścia na CPU i brak przeładowywania modelu w trakcie dekodowania. Działanie na RTX 5070 Ti potwierdzone pomiarem ([raport](TEST-REPORT.md)).
- Modele pobierane są do zwykłych folderów (`local_dir`), bo cache Hugging Face z symlinkami kończy się `WinError 1314` na Windows bez trybu dewelopera.
- Warianty: **A** `direct` (Whisper translate), **B** `two-stage` (Whisper transcribe PL + [Marian opus-mt-pl-en](https://huggingface.co/Helsinki-NLP/opus-mt-pl-en) na CPU), `polish` (sama transkrypcja). Na nagraniach z A50 wariant B zachował sens wszystkich zdań; A gubił fragmenty — B jest domyślny.
- Prompty: polska lista terminów dla transkrypcji pomaga i nie przecieka do wyniku; angielska lista lub przykładowe zdanie dla `translate` były kopiowane do wyniku, więc `translate` ma neutralny prompt. Słownik użytkownika (tory, zakręty, nicki) jest dopisywany na początku promptu (Whisper zachowuje ok. 220 tokenów od końca). W pomiarach nazwy ze słownika nie były doklejane.
- Filtr halucynacji: typowe wyniki z ciszy (napisy, Amara.org, „Thank you for watching”, „Dziękuję za uwagę”, sam „you”/„bye”/„Thank you”), pętle dekodowania i echo promptu. Reguła segmentów odpowiada regule ciszy Whispera (wysokie `no_speech_prob` **i** niskie `avg_logprob`) — sam próg `avg_logprob > -1.0` odrzucał prawdziwe krótkie „Sorry!”. Kompromis: samo „Dzięki.”/„Thank you.” jest odrzucane — powiedz np. „Dzięki za wyścig”.

## Inne źródła

- [Crew Chief](https://mr_belowski.gitlab.io/CrewChiefV4/VoiceRecognition_FreeDictationChatMessages.html) — idea sekwencji czatu.
- [iRacing: makra i komendy czatu](https://support.iracing.com/support/solutions/articles/31000170165-pit-macros-chat-commands) — prefiksy `/ @ #` uruchamiają funkcje gry, dlatego są blokowane.
- [SimHub Keyboard Emulator](https://github.com/SHWotever/SimHub/wiki/Additional-Plugin--Keyboard-Emulator-Plugin) — mapowanie przycisku na F13–F20 (iRacing ich nie używa); PTT wymaga zdarzeń key-down i key-up.
- [ChatShift](https://github.com/toffenloffen/ChatShift), [STTC-EVO](https://github.com/chopsuey2/sttc-evo) — przejrzane wcześniej; nie wykorzystano kodu (licencje opisane w historii repozytorium).

## Licencje zależności

Własny kod: MIT. faster-whisper/CTranslate2: MIT; Whisper: MIT; SDL/pygame-ce: zlib/LGPL; pynput/pystray: LGPL; sounddevice: MIT; NumPy: BSD; Pillow: HPND; psutil: BSD; Transformers: Apache-2.0; PyTorch: BSD. `nvidia-cublas-cu12`, `nvidia-cudnn-cu12`: własna licencja NVIDIA (tekst w metadanych pakietów; warunki redystrybucji w EXE trzeba sprawdzić przed publikacją paczki — nie zostało to tu zweryfikowane). Model Marian ma własną kartę/licencję. Dystrybucja EXE musi zachować pliki licencyjne bibliotek. Modele nie są dołączane do repozytorium.
