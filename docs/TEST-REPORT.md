# Raport testów — 22.10.2026

## Wykonano

- 26 testów automatycznych: atrapa czatu T/tekst/Enter, pusty tekst, prefiksy komend, długość, duplikaty, brak fokusu, utrata fokusu w trakcie wpisywania, anulowanie, niepotwierdzone/już otwarte pole; zapis/odczyt konfiguracji; cisza i krótki sygnał; cykl życia strumienia mikrofonowego na atrapie, odrzucenie przepełnienia; PTT, release, autorepeat, toggle i nakładające się źródła wejścia; wzorce wizualne; parametry modelu i awaryjne przejście na CPU.
- Cykl życia GUI na Windows 11: utworzenie, obsługa zdarzeń, zamknięcie; bez fizycznego nagrywania i wysyłania klawiszy.
- Zbudowany EXE: test GUI oraz prawdziwe dekodowanie próbki syntetycznej w obu wariantach z modelem small na CPU; kod zakończenia 0. Modele pozostają zewnętrzne. Sprawdzono brak lokalnej nazwy konta w plikach paczki; usunięto ścieżkę kompilacji z pomocniczego bytecode biblioteki. Build.cmd powtarza tę sanitację.
- Diagnostyka potwierdziła dostępność bibliotek i enumerację urządzeń; nie potwierdza działania konkretnego sprzętu.
- Pobranie i rzeczywiste dekodowanie small, medium, large-v3; oba warianty, lokalnie na CPU int8. Syntetyczny głos pl-PL z Windows System.Speech, zdanie: „Przepraszam, nie zauważyłem cię po wewnętrznej. Mój błąd.” Audio nie jest publikowane.

| Model | Direct: rozpoznawanie+tłumaczenie | Dwa etapy: rozpoznawanie | Tłumaczenie Marian | Suma dwóch etapów |
|---|---:|---:|---:|---:|
| small | 1,28 s | 1,46 s | 0,61 s | 2,06 s |
| medium | 3,85 s | 4,09 s | 0,65 s | 4,74 s |
| large-v3 | 6,64 s | 7,16 s | 0,63 s | 7,79 s |

Jedna mierzona próba po rozgrzewce, jeden syntetyczny głos i jedno zdanie. To test działania, nie reprezentatywny benchmark ani pomiar na RTX 5070 Ti. Procesy budowania mogły działać równolegle. Nie zmierzono VRAM i FPS. Czasy nie obejmują nagrywania ani wysyłania do gry.

Direct small/medium: „I'm sorry, I didn't notice you on the inside. My mistake.” Direct large-v3: „I'm sorry, I didn't notice you after the inside. My mistake.” Dwa etapy po poprawce dla wszystkich trzech: „Sorry, I didn't see you on the inside. My bad.”

Wykryto i poprawiono: niezgodność PyAV 19 z faster-whisper (blokada do <17, przetestowano 16.1.0), brak cuBLAS w bieżącym środowisku (auto przechodzi na CPU, również przy odroczonym błędzie generatora), pomijanie drugiego zdania przez Marian przy tłumaczeniu całego akapitu (teraz osobne zdania w jednej partii). Zależności instalacyjne zamrożone w requirements-lock.txt.

## Pozostaje do weryfikacji

Prawdziwa polska mowa i hałas wyścigowy, terminologia i nazwiska, fizyczny przycisk kierownicy oraz jego release w tle, SimHub, RTX 5070 Ti/CUDA, jakość i wydajność na dłuższych próbkach, stabilność kalibracji w fullscreen/borderless oraz rzeczywiste T/tekst/Enter i odbiór w iRacing. Nie uznano tych kryteriów za zaliczone. Wykonaj [procedurę odbioru](ACCEPTANCE.md).
