# iRacing Voice Translator — Windows 11

Lokalne nagrywanie polskiej mowy przyciskiem kierownicy → angielski tekst → standardowy czat iRacing. Kod jest zaimplementowany; integracja z prawdziwą grą i kierownicą wymaga odbioru według [procedury](docs/ACCEPTANCE.md). Nie deklarujemy ukończenia odbioru sprzętowego.

## Uruchomienie

1. Zainstaluj Python 3.12 x64 z python.org, z Tk i opcją PATH.
2. Uruchom dwuklikiem `Install.cmd`, następnie `Start.cmd`.
3. Wybierz mikrofon, `medium`, `auto`, `direct`. Kliknij „Pobierz + załaduj model”. Pobranie wymaga internetu; kolejne uruchomienia: „Załaduj offline”.
4. `auto` wybiera CUDA, a przy błędzie ładowania próbuje CPU. Jeśli błąd wystąpi dopiero podczas dekodowania, wybierz CPU i przeładuj model. Dla GPU zainstaluj sterownik NVIDIA, cuBLAS CUDA 12 i cuDNN 9 z oficjalnych źródeł NVIDIA, dodaj katalogi DLL do PATH. Zgodność RTX 5070 Ti trzeba potwierdzić diagnostyką i próbnym dekodowaniem.
5. Wciśnij „Test mikrofonu i tłumaczenia”, powiedz krótkie zdanie, kliknij ponownie. Test zawsze kończy się podglądem. Poziom mikrofonu działa wyłącznie podczas nagrywania.

Przyciski `Pobierz` i `Załaduj` nie uruchamiają nagrywania. Ustawienia zapisuj przyciskiem „Zapisz ustawienia”. Zmiana modelu/silnika wymaga ponownego ładowania. Domyślnie automatyczne wysyłanie jest wyłączone; po konfiguracji i udanym teście włącz je i zapisz.

## Kierownica i SimHub

Wybierz urządzenie z listy → „Przypisz następny przycisk” → naciśnij fizyczny przycisk. Zapis obejmuje GUID SDL i indeks przycisku. SDL obsługuje joysticki Windows, w tym urządzenia HID/DirectInput; widoczność konkretnej kierownicy wymaga testu. Dwa identyczne urządzenia z tym samym GUID nie są jednoznacznie rozróżniane — użyj wtedy SimHub. Odłączenie kontrolera anuluje nagranie. PTT: przytrzymaj i puść. Toggle: naciśnij dwa razy. Maksymalnie 20 sekund nagrania. F9 działa globalnie, także w tle; Esc anuluje. Skrót możesz zmienić w GUI. Usuń konflikt tego przycisku z voice chat iRacing.

SimHub Keyboard Emulator może mapować kierownicę na wybrany F9/F8/F10/F11/F12. PTT wymaga trzymania klawisza przez cały czas trzymania przycisku, z poprawnym zwolnieniem. Dla mapowania impulsowego użyj toggle.

## Kalibracja czatu i pierwszy test

W prywatnej sesji treningowej zatrzymaj samochód. Ustaw stały HUD i rozdzielczość. W GUI wpisz ekranowy prostokąt `x1,y1,x2,y2` obejmujący stabilny fragment ramki otwartego czatu, poza tekstem/cursorem i ruchomą sceną. Współrzędne są pikselami pulpitu (dla lewego monitora mogą być ujemne).

Kliknij „Zapisz ZAMKNIĘTY za 5 s”, przełącz się do gry z zamkniętym czatem. Następnie „Zapisz OTWARTY za 5 s”, wróć do gry i ręcznie otwórz T. Wzorce muszą być wyraźnie różne; inaczej wysyłanie jest blokowane. Zamknij czat ręcznie. Jeśli trudno znaleźć stabilną ramkę, nie włączaj automatycznego wysyłania — ta konfiguracja wymaga dalszej integracji.

Nagraj „Przepraszam, mój błąd” w trybie testu. Sprawdź tłumaczenie. „Wyślij podgląd za 5 s” daje czas na aktywowanie gry. Aplikacja sprawdza proces i wzorce, wciska T, wpisuje tekst i Enter. Dźwięk oznacza zakończenie próby, a nie dowód doręczenia. Sprawdź ręcznie, czy pojawiła się dokładnie jedna wiadomość. Powtórz po zmianie fullscreen/borderless. Przy zmianie HUD/DPI/rozdzielczości wykonaj kalibrację od nowa.

Po błędzie lub utracie fokusu sprawdź pole ręcznie; program nie ponawia próby i nie wciska Esc w innym oknie. Nie otwieraj czatu ręcznie podczas automatycznej operacji. Każda wypowiedź ma osobny identyfikator, a ten sam podgląd można wysłać tylko raz. Za długi tekst jest odrzucany, bez obcinania znaczenia. Domyślny limit 180 znaków jest ostrożnym ustawieniem, wymaga sprawdzenia z grą.

## Prywatność

Audio jest wyłącznie w pamięci RAM; nie jest zapisywane ani wysyłane. Historia ostatnich 10 wyników jest tylko w RAM i znika po zamknięciu programu. To nie jest szyfrowanie przed innymi procesami na komputerze. Konfiguracja, modele i dwa wycinki kalibracji są lokalnie w `%LOCALAPPDATA%\iRacingVoiceTranslator`, poza repo. Wycinek może zawierać dane widoczne w grze — zaznacz wyłącznie ramkę. Pobieranie modeli łączy się z Hugging Face i ujawnia serwisowi typowe dane sieciowe; właściwe rozpoznawanie jest lokalne. Wysłana do czatu wiadomość jest oczywiście widoczna dla gry i odbiorców.

Nie publikuj katalogu AppData, nagrań testowych ani zrzutów ekranu. `.gitignore` dodatkowo blokuje audio, obrazy, JSON, logi, modele i środowisko. Sam `.gitignore` nie chroni sekretów w kodzie lub wcześniej śledzonych plikach; przed każdym push sprawdzaj `git diff --cached`.

## Dodatkowe funkcje

- Zamknięcie okna minimalizuje aplikację do zasobnika. Z menu zasobnika wybierz „Zakończ”, aby ją wyłączyć.
- Silnik `polish` wysyła polską transkrypcję. `direct` zwraca bezpośredni angielski wynik, bez osobnego polskiego tekstu.
- Wariant `two-stage`: zainstaluj `.venv\Scripts\python -m pip install -r requirements-translation.txt`, wybierz silnik i pobierz modele. Tłumacz Marian działa na CPU.
- Autostart opcjonalny: Win+R → `shell:startup` → utwórz skrót do `Start.cmd` (lub zbudowanego EXE). Program nie zmienia rejestru samodzielnie.
- Testy: `.venv\Scripts\python -m unittest discover -s tests -v`.
- Diagnostyka bez nazw urządzeń i transkrypcji: `.venv\Scripts\python scripts\diagnostics.py`.
- Porównanie modeli na własnym lokalnym WAV: `.venv\Scripts\python scripts\benchmark.py private\sample.wav --download --device cuda`, potem z `--engine two-stage`. Wyniki w terminalu zawierają tekst — nie publikuj ich bez sprawdzenia.
- Budowanie: `Build.cmd`. Uruchamiaj `dist\iRacingVoiceTranslator\iRacingVoiceTranslator.exe`; zachowaj cały katalog. To wydanie przenośne, bez instalatora. Modele pobiera się osobno.

Rzeczywiste opóźnienia są w historii GUI. Dla direct czas `speech_s` obejmuje rozpoznawanie i tłumaczenie; nie można ich uczciwie rozdzielić. Błąd tłumaczenia, nazw, negacji i liczb jest możliwy. Nie gwarantujemy 1–2 s, braku spadków FPS ani niezawodnej detekcji obrazu. [Badania i kompromisy](docs/RESEARCH.md).
