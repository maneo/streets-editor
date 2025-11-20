# Plan Testów – Streets Dictionary Editor

## 1. Wprowadzenie i cele testowania
Celem procesu testowania jest zapewnienie, że aplikacja **Streets Dictionary Editor** spełnia wymagania funkcjonalne, jest stabilna, bezpieczna i gotowa do użycia przez użytkowników końcowych. Testy mają:

- wykryć defekty na jak najwcześniejszym etapie,
- potwierdzić poprawność implementacji wymagań biznesowych (PRD),
- zagwarantować spełnienie kryteriów jakościowych (użyteczność, bezpieczeństwo, niezawodność),
- zminimalizować ryzyko regresji przy kolejnych iteracjach rozwoju.

## 2. Zakres testów
Zakres obejmuje wszystkie moduły backendu i frontend-u, z naciskiem na kluczowe ścieżki użytkownika opisane w **main-flow-diagram.md** oraz API zdefiniowane w **api-plan.md**.

| Priorytet | Obszar | Uzasadnienie |
|-----------|--------|--------------|
|  P1 | Autoryzacja (rejestracja, logowanie, sesje) | Brama do wszystkich funkcji, krytyczne dla bezpieczeństwa |
|  P1 | Upload plików + walidacja | Kluczowa ścieżka US-003; błędy mogą blokować cały workflow |
|  P1 | Ekstrakcja AI i zapisy do bazy | Serce funkcjonalności – ryzyko błędnych danych |
|  P1 | Edycja, dodawanie, usuwanie ulic (AJAX/API) | Główna wartość biznesowa |
|  P1 | REST API eksportu słowników | Nowa, wysoka wartość dla użytkownika |
|  P2 | UI edytora (renderowanie listy, preview obrazu) | Wpływa na użyteczność |
|  P2 | Migracje DB / schemat | Integralność danych |
|  P3 | Dokumentacja i błędy UX | Wygoda, ale nie blokuje krytycznych procesów |

## 3. Typy testów
1. **Testy jednostkowe (Unit Tests)** – logika w usługach (`services/`), modelach i helperach.
2. **Testy integracyjne** – komunikacja router-serwis-baza, upload + AI extraction flow.
3. **Testy API (HTTP)** – pokrycie wszystkich endpointów REST (statusy, walidacja, autoryzacja).
4. **Testy end-to-end (E2E)** – scenariusze użytkownika w przeglądarce (Playwright/Selenium): upload → edycja → eksport.
6. **Testy regresyjne** – uruchamiane w CI przy każdym mergu.
7. **Testy akceptacyjne (UAT)** – wspólne sesje z Product Ownerem.

*Testy wydajnościowe są pominięte zgodnie z wymaganiami projektu.*

## 4. Scenariusze testowe dla kluczowych funkcjonalności
### 4.1 Autoryzacja
- **TC-AUTH-01**: Rejestracja poprawnych danych → redirect do `/upload`, użytkownik zalogowany.
- **TC-AUTH-02**: Rejestracja z istniejącym e-mailem → komunikat o błędzie, brak konta.
- **TC-AUTH-03**: Logowanie poprawne → dostęp do stron chronionych.
- **TC-AUTH-04**: Logowanie z błędnym hasłem → błąd i brak sesji.
- **TC-AUTH-05**: Dostęp do `/upload` bez sesji → redirect do `/auth/login`.

### 4.2 Upload & Ekstrakcja
- **TC-UPL-01**: Upload PNG <50 MB z prawidłowymi metadanymi → flash success, redirect do editor.
- **TC-UPL-02**: Upload pliku >50 MB → flash error „File too big”.
- **TC-UPL-04**: Pozytywny flow ekstrakcji AI → X rekordów zapisanych w DB.
- **TC-UPL-05**: AI zwraca pusty wynik → flash warning, przejście do edytora w trybie manual.

### 4.3 Edytor ulic
- **TC-ED-01**: Zmiana `main_name` → aktualizacja DB, odświeżona lista.
- **TC-ED-02**: Dodanie nowej ulicy z duplikatem → komunikat o duplikacie.
- **TC-ED-03**: Soft delete (reject) → rekord `is_rejected = true`, brak na liście.

### 4.4 REST API – Streets
- **TC-API-ST-01**: `POST /api/streets` z poprawnym payloadem → 201 + body.
- **TC-API-ST-02**: `GET /api/streets/{id}` innego użytkownika → 403.
- **TC-API-ST-03**: `PUT /api/streets/{id}` z błędnym enumem `prefix` → 400.

### 4.5 REST API – Export
- **TC-API-EXP-01**: `GET /api/dictionaries` → sortowanie zgodnie z planem.
- **TC-API-EXP-02**: `GET /api/export/{city}/{decade}/txt` → poprawny plik TXT.
- **TC-API-EXP-03**: `GET /api/dictionaries/{city}/{decade}/streets/json?page=2` → prawidłowa paginacja.

## 5. Środowisko testowe
- **Język Python 3.14** (virtualenv `.venv/`).
- **Baza danych**: SQLite in-memory na czas testów jednostkowych, osobny plik `.db` w temp dla integracyjnych.
- **Flask config**: `TESTING=True`, CSRF token włączony.
- **Frontend E2E**: Headless Chromium.
- **Mocki**: Zewnętrzne zapytania do OpenRouter AI stubowane (pytest-vcr / responses).

## 6. Narzędzia do testowania
- **pytest** + **pytest-flask** – jednostkowe i integracyjne.
- **coverage.py** – raport pokrycia (>90 % dla usług i modeli).
- **playwright** – testy end-to-end UI.
- **ruff** / **flake8** – statyczna analiza kodu.
- **pre-commit** – automatyczne uruchamianie linterów.
- **GitHub Actions** – CI/CD z matrycą testów.

## 7. Kryteria akceptacji testów
- Wszystkie scenariusze P1 przechodzą bez błędów.


## 9. Procedury raportowania błędów
1. Defekt rejestrowany w **GitHub Issues** z szablonem:
   - Tytuł: `[BUG] Krótki opis`
   - Opis kroku reprodukcji, oczekiwany vs rzeczywisty rezultat.
   - Zrzuty ekranu/logi.
   - Severity (Blocker/Critical/Major/Minor).
2. QA przypisuje do odpowiedniego developera i dodaje label `bug` + `severity`.
3. Statusy work-flow: *Open → In Progress → Code Review → QA Verify → Done*.
4. Po weryfikacji naprawy QA zamyka zgłoszenie.
