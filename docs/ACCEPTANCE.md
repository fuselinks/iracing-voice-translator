# Test w iRacing — sesja treningowa (ok. 20 min)

Do zrobienia razem, zanim uznamy czat za działający. Wszystko poniżej było dotąd sprawdzone tylko poza grą.

## Przygotowanie (bez gry)

1. Podłącz A50 i Simucube. Uruchom `Start.cmd` → zakładka **Diagnostyka** → „Odśwież”: A50 Mic na liście, Simucube 2 Pro ze 128 przyciskami, CUDA „cuBLAS 12 i cuDNN 9: załadowane”.
2. **Ustawienia**: mikrofon A50, silnik `two-stage`, model `medium`, obliczenia `auto`, w słowniku nazwy toru (np. `Eau Rouge, Raidillon`). „Przypisz” → przycisk na kierownicy. **Automatyczne wysyłanie: WYŁĄCZONE.** „Zapisz ustawienia”.
3. **Start** → „Pobierz + załaduj model” (lub „Załaduj offline”). W nagłówku: „Gotowy”, bez żółtego ostrzeżenia GPU.
4. Przytrzymaj przycisk, powiedz „Przepraszam, mój błąd”, puść. Podgląd ma pokazać sensowne tłumaczenie.

## W grze — prywatna sesja treningowa, samochód w boksie lub na postoju

5. Nagłówek programu: „● iRacing wykryty”. Jeśli „niewykryty” — zapisz to i przerwij.
6. Okno iRacing aktywne. W programie: nagraj przyciskiem „Sorry, my mistake” w trybie podglądu → „Wyślij podgląd za 5 s” → kliknij w okno iRacing.
   - **Oczekiwane:** czat otwiera się sam, pojawia się dokładnie jedna wiadomość `Sorry, my mistake.` (lub podobna), czat się zamyka.
   - Zapisz: czy czat się otworzył, czy tekst jest kompletny i bez dziwnych znaków, czy Enter wysłał.
7. Pole z resztkami: otwórz czat ręcznie (T), wpisz „abc”, nie wysyłaj, kliknij w iRacing i powtórz wysyłkę z kroku 6. **Oczekiwane:** „abc” znika (Cancel), wysłana jest tylko nowa wiadomość.
8. Przerwanie: wyślij długi podgląd (np. trzy zdania) i w trakcie wpisywania naciśnij Alt+Tab do innego okna. **Oczekiwane:** wpisywanie stoi, po powrocie do iRacing czat jest zamknięty i pusty.
9. Esc: zacznij wysyłanie i naciśnij Esc w trakcie odliczania 5 s. **Oczekiwane:** nic nie zostało wysłane, czat zamknięty.
10. Długa wypowiedź (ok. 20 s): ma przyjść jako 2–3 osobne wiadomości, każda kompletna.
11. Pauzy: jeśli brakuje pierwszych liter, zwiększ „Pauza po otwarciu” (np. 500 ms); jeśli gubione są znaki w środku — „Pauza między znakami” (np. 20 ms).
12. Fullscreen i borderless: powtórz krok 6 w obu trybach.
13. Dopiero gdy 6–10 przeszły: włącz automatyczne wysyłanie, zapisz, wykonaj pełny scenariusz jednym przyciskiem (przytrzymaj, mów, puść → wiadomość w czacie). Potem krótko podczas jazdy.
14. Opcjonalnie: zaznacz „Dodaj do słownika tor i kierowców z bieżącej sesji iRacing” i powiedz zdanie z nickiem kierowcy z sesji.

Nie zgłaszaj testu jako zaliczonego bez zobaczenia wiadomości w czacie. Wyniki (bez nagrań) dopisz do `docs/TEST-REPORT.md`.
