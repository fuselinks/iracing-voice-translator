# iRacing Voice Translator — Windows 11

Lokalnie: przycisk na kierownicy → polska mowa → angielski tekst → czat iRacing. Rozpoznawanie działa na Twoim komputerze (GPU NVIDIA lub CPU); audio nie opuszcza RAM.

**Status:** kod i testy przeszły na docelowym PC (RTX 5070 Ti, A50, Simucube 2 Pro) — szczegóły w [raporcie testów](docs/TEST-REPORT.md). Wysyłanie do czatu iRacing sprawdzone w sesji 23.10.2026 (podgląd, automatyczne wysyłanie, przerwania, jazda) — [wyniki](docs/TEST-REPORT.md#test-w-iracing--23102026). Na nowym komputerze zrób najpierw [test w sesji treningowej](docs/ACCEPTANCE.md).

## Instalacja

1. Python 3.12 x64 z python.org (z Tk i opcją PATH).
2. `Install.cmd` (instaluje też biblioteki CUDA: `nvidia-cublas-cu12`, `nvidia-cudnn-cu12` — ok. 1 GB, osobna instalacja CUDA Toolkit nie jest potrzebna), potem `Start.cmd`.
3. Zakładka **Start** → „Pobierz + załaduj model”. Potem wystarczy „Załaduj offline”.

## Okno

Na górze zawsze widać: status (kolorowa kropka + Gotowy / Nagrywanie / Rozpoznawanie / Wysyłanie / Wysłano / Błąd), poziom mikrofonu, ostatnią wiadomość PL → EN, stan iRacing (wykryty/niewykryty) i ostrzeżenia. Zakładki:

- **Start** — ładowanie modelu, test mikrofonu i tłumaczenia bez wysyłania, podgląd z ręcznym wysłaniem („Wyślij podgląd za 5 s” — w tym czasie przełącz się do iRacing).
- **Ustawienia** — mikrofon, model, silnik, przycisk kierownicy, skrót, słownik nazw, pauzy, autostart.
- **Historia** — 10 ostatnich wyników z czasami (tylko w RAM).
- **Diagnostyka** — mikrofony (host API, częstotliwość), kontrolery (nazwa, GUID, liczba przycisków), stan CUDA i iRacing SDK, podgląd wciśnięć przycisków na żywo. Raport zawiera nazwy urządzeń — sprawdź go, zanim komuś wyślesz.

Zamknięcie okna chowa program do zasobnika; „Zakończ” w menu zasobnika go wyłącza.

## Ustawienia — zalecenia

| Ustawienie | Zalecane | Dlaczego |
|---|---|---|
| Mikrofon | Twój headset, np. „Mikrofon zestawu słuchawkowego (A50 Mic)” | Lista pokazuje każde urządzenie raz (host API MME). Zapamiętywana jest nazwa + host API. Gdy sterownik nie przyjmie 16 kHz, nagranie idzie w natywnej częstotliwości z resamplingiem. |
| Silnik | `two-stage` (domyślny) | Polska transkrypcja + tłumacz Marian. Na nagraniach testowych zachował sens wszystkich zdań; `direct` gubił fragmenty. |
| Model | `medium` lub `large-v3` | Na RTX 5070 Ti oba mieszczą się poniżej 1 s (mediana 0,76 / 0,85 s). `small` myli słowa. |
| Obliczenia | `auto` | Gdy GPU nie działa, program **wyraźnie ostrzega** (żółty pasek + okno) i liczy na CPU. `cuda` = błąd zamiast CPU. |
| Słownik | np. `Eau Rouge, Raidillon, Kemmel, Kowalski` | Nazwy torów, zakrętów i nicków. Bez słownika „Eau Rouge” wychodziło jako „Eurosh”, ze słownikiem poprawnie. |
| Nazwy z sesji iRacing | opcjonalnie | Dodaje do słownika nazwę toru i kierowców z bieżącej sesji (odczyt SDK). |

Próg ciszy 0,008 sprawdzono z A50 z włączoną redukcją szumów (Voice Clarity, bramka): mowa przechodzi, cisza jest odrzucana, początek wypowiedzi nie jest ucinany.

## Przycisk kierownicy, SimHub, skróty

**Ustawienia** → wybierz urządzenie → „Przypisz” → naciśnij przycisk. Zapisywany jest GUID urządzenia i indeks przycisku; działa też, gdy aktywne jest inne okno (sprawdzone z Simucube 2 Pro). PTT: przytrzymaj i puść. Toggle: naciśnij dwa razy. Max 20 s nagrania. Esc anuluje. Odłączenie *innego* kontrolera nie przerywa nagrania; odłączenie przypisanego — przerywa.

Zamiast przycisku SDL możesz zmapować przycisk w SimHub (Keyboard Emulator) na **F13–F20** — tych klawiszy iRacing nie używa. PTT wymaga przytrzymania klawisza przez SimHub (key-down/key-up); przy krótkim impulsie wybierz toggle.

## Jak wysyłana jest wiadomość

Przez oficjalne iRacing SDK, bez zrzutów ekranu i bez kalibracji:

1. Sprawdzenie: aktywne okno należy do `iRacingSim64DX11.exe`, SDK jest połączone (mapa pamięci `Local\IRSDKMemMapFileName`, tylko odczyt), iRacing nie działa jako administrator.
2. Tekst jest zamieniany na ASCII (`’` → `'`, `—` → `-`, `…` → `...`, `ł` → `l`, bez ogonków) i — jeśli trzeba — dzielony na maks. 3 wiadomości po zdaniach lub słowach. Każdy znak jest mapowany na scan code w układzie klawiatury okna iRacing **przed** otwarciem czatu.
3. SDK: `Cancel` (czyści pole) → `BeginChat` → pauza → wpisywanie (`SendInput` ze scan code'ami, Shift jako osobny klawisz, domyślnie 10 ms między znakami) → pauza → ponowne sprawdzenie fokusu → Enter.
4. Każde przerwanie po otwarciu czatu (Esc, utrata fokusu, błąd) wysyła `Cancel` przez SDK, więc pole nie zostaje z połową tekstu.

Wiadomość zaczynająca się od `/ # ! @ $` (komendy gry) jest blokowana. Ten sam podgląd można wysłać tylko raz. Gra nie potwierdza doręczenia — sprawdź czat wzrokiem.

## Prywatność

Audio jest tylko w RAM. Historia — tylko w RAM. W `%LOCALAPPDATA%\iRacingVoiceTranslator` są: `settings.json`, `ivt.log` (bez transkrypcji) i modele. Pobieranie modeli łączy się z Hugging Face. Wysłana wiadomość jest widoczna dla innych graczy. Nagrania testowe trzymaj w `private\` (w `.gitignore`).

## Dla zaawansowanych

- Testy: `.venv\Scripts\python -m unittest discover -s tests -v`
- Diagnostyka w konsoli: `.venv\Scripts\python scripts\diagnostics.py`
- Benchmark na własnych nagraniach (WAV 16 kHz mono): `.venv\Scripts\python scripts\benchmark.py private\samples --device cuda` (opcje: `--engine direct|two-stage|both`, `--models`, `--names "Eau Rouge, Raidillon"`). Wypisuje teksty — nie publikuj bez sprawdzenia.
- EXE: `Build.cmd` → `dist\iRacingVoiceTranslator\iRacingVoiceTranslator.exe` (cały katalog, z bibliotekami CUDA). Sprawdzenie: `iRacingVoiceTranslator.exe --self-test --self-test-cuda` (kod 0 = OK).
- Autostart: checkbox w Ustawieniach (wpis w `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`, bez uprawnień administratora).
- Uszkodzony `settings.json` nie blokuje startu: program wczyta domyślne ustawienia, a stary plik zachowa jako `settings.json.bad`.

[Decyzje techniczne](docs/RESEARCH.md) · [Raport testów](docs/TEST-REPORT.md) · [Test w iRacing](docs/ACCEPTANCE.md)
