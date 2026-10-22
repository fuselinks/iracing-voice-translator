# Raport testów — 22.10.2026

Komputer docelowy: Windows 11 (26200), RTX 5070 Ti 16 GB (sterownik 610.88), Python 3.12.3, CTranslate2 4.8.3, cuBLAS 12.9, cuDNN 9.27, układ klawiatury polski (programisty). Mikrofon: Astro A50 z Voice Clarity, „Fokus głosu” i bramką szumów. Kontrolery: Simucube 2 Pro i 7 innych urządzeń SDL.

## Nie sprawdzono (wymaga sesji w iRacing)

Otwarcie czatu przez SDK `BeginChat`/`Cancel`, wpisywanie scan code'ami do okna iRacing, Enter i odbiór wiadomości, odczyt nazw z YAML sesji na żywym symulatorze, PTT kierownicą w trakcie gry, SimHub F13–F20, wpływ na FPS. Procedura: [ACCEPTANCE.md](ACCEPTANCE.md).

## Testy automatyczne

83 testy (`python -m unittest discover -s tests`), wszystkie przechodzą. Obejmują m.in.:

- czat: kolejność Cancel → BeginChat → tekst → Enter na stanowej atrapie, Cancel po każdym przerwaniu (utrata fokusu, Esc, błąd transportu), brak SDK, iRacing jako administrator, resztki tekstu w polu, duplikaty, podział na 3 części, normalizacja do ASCII, prefiksy komend;
- SDK: bit `status & 1` i nazwy z YAML sesji odczytywane z prawdziwej mapy pamięci o unikalnej testowej nazwie (nigdy nazwy iRacing), parametry broadcastu (`MAKELONG(8, 1|3)`);
- klawiatura: struktura `INPUT` (40 B), scan code'y i Shift, round-trip **wszystkich 95 znaków ASCII** przez `ToUnicodeEx` w aktywnym układzie, martwe klawisze;
- audio: lista z jednego host API, rozróżnienie tej samej nazwy w MME/WASAPI, overflow tylko logowany, nagrywanie 48 kHz z resamplingiem i filtrem antyaliasingowym;
- silnik: brak cichego CPU, ostrzeżenie, brak przeładowania w trakcie dekodowania, filtr halucynacji, prompty, słownik, pobieranie bez symlinków;
- GUI na prawdziwym oknie Tk z atrapami kontrolerów: przypisanie tylko z wybranego urządzenia, PTT tylko z przypisanego przycisku, F13, podgląd przycisków, walidacja ustawień; odłączenie innego kontrolera; kontrast motywu ≥ 4,5:1 dla wszystkich stanów widżetów; autostart na tymczasowym kluczu rejestru; uszkodzony `settings.json`.

## Mikrofon

- **Błąd odtworzony:** `Recorder().start(Config(microphone='Mikrofon (USB Sound Device)'))` na starym kodzie → „Mikrofon zniknął lub nazwa jest niejednoznaczna” (ta sama nazwa w MME, DirectSound i WASAPI). WASAPI odrzuca 16 kHz (`PaErrorCode -9997`), MME przyjmuje.
- **Po poprawce:** wszystkie wejścia MME otwierają się przy 16 kHz; przez WASAPI nagrywanie w 48/44,1 kHz z resamplingiem, bez błędów i flag statusu.
- **A50, 9 nagrań** (prywatne, `private/samples`, poza repo; ta sama ścieżka co w aplikacji: MME, 16 kHz): strumień otwiera się w 16–23 ms, pierwsze dane po ok. 57 ms, 0 flag overflow. Bramka A50 zwraca cyfrowe zera w ciszy (34–62% próbek) i otwiera się ok. 0,14 s przed pierwszym blokiem z głosem.
- **Próg ciszy 0,008:** wszystkie 8 wypowiedzi przechodzi (także krótkie „Sorry!”: 24 bloki z głosem przy wymaganych 10); nagranie ciszy odrzucone (szczyt 0,0002).
- **Ucinanie początku:** przycięcie audio dokładnie do początku głosu i 50 ms dalej nie zmienia pierwszego słowa („Przepraszam”, „Nie”, „Dobry”, „Uważaj”) w medium i large-v3. W nagraniu 02 przed „Nie hamuj” wszystkie modele słyszą „Jezu” (0,72 s) — to dźwięk obecny w nagraniu, nie efekt obcięcia.

## Kierownica

Simucube 2 Pro (GUID `03005349d0160000600d000000000000`, 128 przycisków), przycisk 12 (indeks 11): wciśnięcie i puszczenie wykryte przy aktywnym oknie testu (trzymany 4,7 s) i przy aktywnym innym oknie (5,8 s). Po teście urządzenia odłączono; dalsza logika przycisku — testy z atrapami.

## CUDA i wydajność (RTX 5070 Ti)

CTranslate2 4.8.3 widzi kartę (typy: int8_float16, float16, bfloat16 …). small, medium, large-v3 oraz Marian ładują się z rozgrzewką na CUDA bez ostrzeżeń. Biblioteki z kół `nvidia-*` w `site-packages\nvidia\*\bin`.

Wykryty i naprawiony błąd: pobranie large-v3 kończyło się `WinError 1314` (symlinki w cache Hugging Face bez trybu dewelopera), a stary kod zgłaszał to jako „GPU nie działa”. Modele pobierają się teraz do zwykłych folderów.

Benchmark: 8 nagrań mowy + cisza, 3 powtórzenia po rozgrzewce, `int8_float16`, beam 3, VAD. Czas od końca nagrania do tekstu (bez nagrywania i wpisywania). VRAM = przyrost zajętej pamięci karty po załadowaniu (przybliżony; inne programy też używają GPU).

| Wariant | Model | Mediana | p95 | Whisper (med.) | Marian CPU (med.) | VRAM |
|---|---|---:|---:|---:|---:|---:|
| A direct | small | 0,12 s | 0,22 s | 0,12 s | — | ~0,6 GB |
| A direct | medium | 0,27 s | 0,37 s | 0,27 s | — | ~1,0 GB |
| A direct | large-v3 | 0,36 s | 0,47 s | 0,36 s | — | ~2,0 GB |
| B two-stage | small | 0,62 s | 0,96 s | 0,24 s | 0,39 s | ~0,3–0,6 GB |
| B two-stage | medium | 0,76 s | 1,11 s | 0,36 s | 0,39 s | ~1,0 GB |
| B two-stage | large-v3 | 0,85 s | 1,18 s | 0,46 s | 0,39 s | ~2,0 GB |

Dla porównania: poprzedni raport na CPU — medium 3,9 s, large-v3 6,6 s.

### Jakość (ostateczne prompty, bez słownika)

| Powiedziano | B medium | B large-v3 | A medium | A large-v3 |
|---|---|---|---|---|
| Przepraszam, nie zauważyłem cię po wewnętrznej, mój błąd. | Sorry, I didn't see you on the inside, my mistake. | = B medium | Excuse me, I didn't notice you inside. My mistake. | …on the inside. My mistake. |
| Nie hamuj tak wcześnie przed zakrętem dwa. | Jesus, don't brake so early before corner two. | = | …before the second corner. | …before turn two. |
| Niebieskie flagi, puszczę cię na prostej. | Blue flags, I'll let you go straight. | = | **Blue flags.** (zgubione) | Blue flags. I'll let you go straight. |
| Uważaj, wracam na tor po wyjeździe. | Be careful, I'll be back on track after I leave. | = | Watch out, I'm going back to the track after the exit. | …after the run. |
| Dobry wyścig, dzięki. | Good race, thanks. | = | Good race, thanks. | Have a nice race. Thanks. |
| Zjeżdżam do pitu na następnym okrążeniu, mam uszkodzony przód. | I'm going down to the pit on the next lap, my front's broken. | = | …I have a damaged front. | = A medium |
| Nie, nie chciałem cię wypchnąć, to był mój błąd na Eau Rouge. | No, I didn't mean to push you out… on Eurosh. | …push you… on Eurosh. | …kick you out… on Eurosh. | …knock you out… my **crime** on Eurosh. |
| Sorry! | Sorry. | Sorry. | Sorry. | Sorry. |
| (cisza) | — | — | — | — |

Ze słownikiem `Eau Rouge, Raidillon, Kemmel` nazwa wychodzi poprawnie we wszystkich czterech konfiguracjach. small: m.in. „Welcome to my channel.” z prawdziwej mowy (A) i „tort” zamiast „tor” (B) — niezalecany.

Wnioski: domyślny silnik zmieniono na `two-stage` (B), model `medium` — najlepsze zachowanie sensu przy ok. 0,8 s. large-v3 w B daje praktycznie to samo przy 2× VRAM.

### Prompty i słownik (eksperyment)

- Angielski prompt w formie listy terminów był przy tłumaczeniu **kopiowany do wyniku** (large-v3: „Blue flags, let you by, rejoining the track, pit lane, straight, lap.”), zdanie-przykład — słowo w słowo. Dla `translate` zostawiono neutralne „Race chat in iRacing.”.
- Polski prompt-lista (transkrypcja) w 48 przebiegach niczego nie dokleił i poprawił „tort” → „tor”, „puszczeć” → „puszczę cię”.
- Słownik z 8 nazwami ze Spa i 20 fikcyjnymi nickami: w 96 przebiegach (medium/large-v3, A/B) **żadna nazwa nie została doklejona** do wypowiedzi, która jej nie zawierała.
- Cisza bez VAD daje echo promptu i pętle („pit entry, pit entry, …”), „Dziękuje za oglądanie.”, „Dzień dobry.” — filtr je odrzuca; w aplikacji ciszę zatrzymuje wcześniej próg i VAD.

## Wpisywanie

- Plan scan code'ów dla 95 znaków ASCII odkodowany przez `ToUnicodeEx` w układzie polskim (programisty): wszystkie poprawne, **`~` jest martwym klawiszem** — dodawana jest spacja. W innych układach martwe są `^`, `` ` ``, a w polskim 214 `[ ] |` nie istnieją (taki znak blokuje wysyłkę przed otwarciem czatu). Do sprawdzenia użyto tymczasowo załadowanych układów — usunięto je po teście.
- Pełnego testu wstrzykiwania nie dało się wykonać bez użytkownika: aktywnym oknem był `remoting_desktop.exe` (proces systemowy) i Windows (UIPI) po cichu odrzuca `SendInput` do okna o wyższych uprawnieniach — `SendInput` zwraca przy tym sukces. Stąd dodane wykrywanie iRacing uruchomionego jako administrator (iRacingUI na tym PC działa bez podniesionych uprawnień).

## GUI

Zrzuty ekranu okna (600×700, ciemny motyw) ze stanami: brak modelu, nagrywanie z poziomem mikrofonu i ostrzeżeniem GPU, błąd, wysłano; zakładki Ustawienia (z rozwiniętą listą mikrofonów), Diagnostyka, Historia. Ocena: wszystkie teksty czytelne, kontrast par tekst/tło od 4,8:1 (biały na niebieskim przycisku po najechaniu) do 16,6:1, wyłączone przyciski odróżnialne, lista rozwijana ciemna z czytelnym zaznaczeniem. Poprawiono po pierwszym przeglądzie: niebieska ramka wyłączonego przycisku, ucięte podpowiedzi, brak przewijania w Diagnostyce.

## EXE

PyInstaller (polecenie z `Build.cmd`, potem `sanitize_build.py`): katalog 2,8 GB, w nim `_internal/nvidia/{cublas,cudnn,cuda_nvrtc}/bin` z `cublas64_12.dll` i `cudnn64_9.dll`. `iRacingVoiceTranslator.exe --self-test --self-test-cuda` → kod 0 (GUI + model small załadowany i rozgrzany na CUDA z bibliotek z paczki); `--self-test --self-test-audio private\samples_dobry.wav` → kod 0 (dekodowanie w wariantach A i B). Brak nazwy lokalnego konta w EXE i bytecode.
