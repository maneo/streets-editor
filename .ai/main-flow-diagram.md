# Główny Flow Aplikacji: Upload → Ekstrakcja → Edycja

Diagram przepływu dla historyjek US-003, US-004, US-005, US-006 zaimplementowanych w aplikacji Streets Dictionary Editor.

```mermaid
flowchart TD
    A[User on Upload Page] --> B[Select JPG/PNG File ≤50MB]
    B --> C[Enter City Name]
    C --> D[Enter Decade]
    D --> E[Click Upload]

    E --> F[Validate File]
    F -->|Invalid Format| G[Flash Error: Wrong format]
    G --> B

    F -->|Too Large| H[Flash Error: File too big]
    H --> B

    F -->|Valid| I[Save File to Server]
    I --> J[Extract Streets via AI]

    J --> K{AI Result}
    K -->|Success with Streets| L[Save Streets to Database]
    K -->|Success Empty| M[Flash Warning: No streets found]
    K -->|Error| N[Flash Error: Extraction failed]

    L --> O[Flash Success: X streets extracted]
    O --> P[Redirect to Editor]

    M --> Q[Enable Manual Addition]
    Q --> P

    N --> R[Clean up file]
    R --> S[Redirect to Upload]

    P --> T[Show Editor Page]
    T --> U[Display Extracted Streets List]
    U --> V[Show Uploaded Image Preview]

    V --> W{User Action}
    W -->|Edit Street| X[Change name/prefix/variants]
    W -->|Delete Street| Y[Mark as rejected]
    W -->|Add New Street| Z[Show add form]

    X --> AA[Validate Uniqueness]
    AA -->|Duplicate| BB[Show Error]
    BB --> W

    AA -->|Unique| CC[Update Database]
    CC --> DD[Refresh List]

    Y --> EE[Update Database]
    EE --> DD

    Z --> FF[Enter Street Details]
    FF --> GG[Validate Uniqueness]
    GG -->|Duplicate| HH[Show Error]
    HH --> Z

    GG -->|Unique| II[Create Street Record]
    II --> JJ[Add to Database]
    JJ --> DD
```

## Opis Kluczowych Kroków:

### Walidacja Pliku
- Sprawdzenie formatu (tylko JPG/PNG)
- Sprawdzenie rozmiaru (≤50MB)
- Implementacja w `file_handler.py`

### Ekstrakcja AI
- Wywołanie Gemini 2.5 Pro przez OpenRouter
- Timeout 5 minut
- Obsługa błędów i pustych wyników
- Implementacja w `ai_extraction.py`

### Zapisywanie do Bazy
- Tworzenie obiektów Street dla każdej ulicy
- Transakcyjne zapisywanie (commit/rollback)
- Implementacja w `upload.py`

### Edycja
- AJAX endpoints dla edycji ulic
- Walidacja unikalności nazw
- Implementacja w `upload.py` (API routes)

## Zaimplementowane User Stories:
- **US-003**: Upload skanu
- **US-004**: Uruchomienie ekstrakcji
- **US-005**: Obsługa pustego wyniku
- **US-006**: Edycja wpisu
- **US-007**: Dodanie nowej ulicy
- **US-008**: Walidacja unikalności

## Techniczne Szczegóły:
- **Framework**: Flask z SQLAlchemy
- **Baza**: SQLite z Flask-Migrate
- **Frontend**: Jinja2 templates + Vanilla JS
- **AI**: OpenRouter API + Gemini 2.5 Pro
- **Stylizacja**: Tailwind CSS
