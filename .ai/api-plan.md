# Plan Implementacji REST API - Streets Dictionary Editor

## 1. Wstęp

Ten dokument zawiera plan implementacji REST API dla aplikacji Streets Dictionary Editor. API zostało zaprojektowane zgodnie z wymaganiami funkcjonalnymi zdefiniowanymi w PRD oraz istniejącym codebase'em aplikacji.

**Zakres API**: Na tym etapie rozwoju, REST API skupia się wyłącznie na eksportowaniu słowników ulic. Pozostałe funkcjonalności (rejestracja, logowanie, upload plików, zarządzanie ulicami) pozostają dostępne tylko przez web interface.

### 1.1 Architektura API
- **Typ**: RESTful API z JSON payloads i file downloads
- **Autoryzacja**: Session-based (Flask-Login) - wszystkie endpointy wymagają zalogowanego użytkownika
- **Błędy**: Standardowe HTTP status codes z JSON error messages
- **Wersjonowanie**: Brak w MVP (prefix `/api/v1/` możliwy w przyszłości)

### 1.2 Konwencje
- Wszystkie REST endpointy wymagają autoryzacji
- Response'y w formacie JSON (oprócz eksportu plików)
- Snake_case dla nazw pól
- UTF-8 encoding
- Walidacja unikalności: `user_id + city + decade + main_name`
- RESTful URL pattern: `/api/resource/{id}/subresource`


## 2. Opis API

### 2.1 Authentication Routes 
Te endpointy są implementowane jako tradycyjne web routes z HTML formularzami.

#### POST /auth/register
**Opis**: Rejestracja nowego użytkownika
**Metoda**: POST (form data)
**Payload**:
```json
{
  "email": "string (required)",
  "password": "string (required)"
}
```
**Response**: Redirect do `/upload` lub błąd walidacji

#### POST /auth/login
**Opis**: Logowanie użytkownika
**Metoda**: POST (form data)
**Payload**:
```json
{
  "email": "string (required)",
  "password": "string (required)"
}
```
**Response**: Redirect do strony docelowej lub błąd

#### GET /auth/logout
**Opis**: Wylogowanie użytkownika
**Metoda**: GET
**Response**: Redirect do `/auth/login`


### 2.2 Web Routes (HTML Templates)
Te endpointy są implementowane jako tradycyjne web routes z HTML formularzami.


#### GET /
**Opis**: Strona główna uploadu
**Autoryzacja**: Wymagana
**Response**: HTML template z listą ulic użytkownika

#### POST /upload
**Opis**: Upload pliku i uruchomienie ekstrakcji AI
**Autoryzacja**: Wymagana
**Content-Type**: multipart/form-data
**Payload**:
```
file: File (JPG/PNG, max 50MB)
city: string (required)
decade: string (required)
```
**Response**: Redirect do `/editor/{city}/{decade}`

#### GET /editor/{city}/{decade}
**Opis**: Strona edytora ulic dla konkretnego miasta i dekady
**Autoryzacja**: Wymagana
**Response**: HTML template z edytorem ulic

### 2.3 Streets REST API 

#### POST /api/streets
**Opis**: Dodanie nowej ulicy ręcznie
**Autoryzacja**: Wymagana
**Payload**:
```json
{
  "city": "string (required)",
  "decade": "string (required)",
  "prefix": "string (default: 'ul.')",
  "main_name": "string (required)",
  "variants": "array<string> (optional)",
  "misspellings": "array<string> (optional)"
}
```
**Response (201)**:
```json
{
  "id": "integer",
  "prefix": "string",
  "main_name": "string",
  "variants": "array<string>",
  "misspellings": "array<string>",
  "source": "string"
}
```

#### GET /api/streets/{street_id}
**Opis**: Pobranie pojedynczej ulicy
**Autoryzacja**: Wymagana (własność ulicy)
**Response (200)**:
```json
{
  "id": "integer",
  "user_id": "integer",
  "city": "string",
  "decade": "string",
  "prefix": "string",
  "main_name": "string",
  "main_name_cs": "string",
  "variants": "array<string>",
  "misspellings": "array<string>",
  "is_rejected": "boolean",
  "source": "string",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

#### PUT /api/streets/{street_id}
**Opis**: Aktualizacja istniejącej ulicy
**Autoryzacja**: Wymagana (własność ulicy)
**Payload**:
```json
{
  "prefix": "string (optional)",
  "main_name": "string (optional)",
  "variants": "array<string> (optional)",
  "misspellings": "array<string> (optional)"
}
```
**Response (200)**:
```json
{
  "message": "Street updated successfully."
}
```

#### DELETE /api/streets/{street_id}
**Opis**: Oznaczenie ulicy jako odrzuconej (soft delete)
**Autoryzacja**: Wymagana (własność ulicy)
**Response (200)**:
```json
{
  "message": "Street marked as rejected."
}
```

### 2.4 Export REST API

#### GET /api/dictionaries
**Status**: ❌ Wymaga implementacji
**Opis**: Lista wszystkich słowników (miast + dekad) dostępnych dla zalogowanego użytkownika
**Autoryzacja**: Wymagana
**Response (200)**:
```json
{
  "dictionaries": [
    {
      "city": "Warszawa",
      "decade": "1940-1949",
      "street_count": 150,
      "ai_generated": 120,
      "manually_added": 30,
      "last_modified": "2024-01-15T10:30:00Z"
    },
    {
      "city": "Kraków",
      "decade": "1930-1939",
      "street_count": 89,
      "ai_generated": 89,
      "manually_added": 0,
      "last_modified": "2024-01-10T14:20:00Z"
    }
  ],
  "total_dictionaries": 2,
  "total_streets": 239
}
```

**Sortowanie**: Alfabetycznie po mieście, następnie po dekadzie (malejąco)

#### GET /api/dictionaries/{city}/{decade}/streets
**Status**: ❌ Wymaga implementacji
**Opis**: Lista ulic dla konkretnego słownika z paginacją
**Autoryzacja**: Wymagana
**Path Parameters**:
- `city`: string (required) - nazwa miasta
- `decade`: string (required) - zakres dekady
**Query Parameters**:
- `page`: integer (optional, default: 1) - strona 
- `per_page`: integer (optional, default: 50) - elementów na stronę
- `source`: string (optional) - filtr po źródle ("ai" lub "manual")
**Response (200)**:
```json
{
  "dictionary": {
    "city": "Warszawa",
    "decade": "1940-1949",
    "total_streets": 150
  },
  "streets": [
    {
      "id": "integer",
      "prefix": "string",
      "main_name": "string",
      "main_name_cs": "string",
      "variants": "array<string>",
      "misspellings": "array<string>",
      "source": "string",
      "created_at": "datetime"
    }
  ],
  "pagination": {
    "page": "integer",
    "per_page": "integer",
    "total": "integer",
    "total_pages": "integer"
  }
}
```


## 4. Mapowanie Endpointów na User Stories

### US-001: Rejestracja użytkownika
- **Istniejące**: POST /auth/register (web form)
- **REST API**: Nie wymagane (tylko web interface)

### US-002: Logowanie
- **Istniejące**: POST /auth/login (web form)
- **REST API**: Nie wymagane (tylko web interface)

### US-003: Upload skanu
- **Istniejące**: POST /upload (web form)
- **REST API**: Nie wymagane (tylko web interface)

### US-004: Uruchomienie ekstrakcji
- **Istniejące**: POST /upload zawiera ekstrakcję (synchroniczna)
- **REST API**: Nie wymagane (tylko web interface)

### US-005: Obsługa pustego wyniku
- **Istniejące**: Logika w POST /upload (flash message)
- **REST API**: Nie dotyczy

### US-006: Edycja wpisu
- **Istniejące**: PUT /api/streets/{id}

### US-007: Dodanie nowej ulicy
- **Istniejące**: POST /api/streets

### US-008: Walidacja unikalności
- **Istniejące**: Implementacja w POST/PUT /api/streets

### US-009: Pobranie TXT
- **Obecne**: GET /export/txt?city=X&decade=Y
- **Proponowane**: GET /api/export/{city}/{decade}/txt (RESTful)

### US-010: Eksport JSON
- **Obecne**: GET /export/json?city=X&decade=Y
- **Proponowane**: GET /api/export/{city}/{decade}/json (RESTful)

### US-011: Wylogowanie
- **Istniejące**: GET /auth/logout (web)
- **REST API**: Nie wymagane (tylko web interface)

### US-012: Pogląd wgranego pliku
- **Brakujące**: Brak endpointu API dla podglądu plików (tylko w template'ach)

### Dodatkowe funkcjonalności (nie zmapowane na US):
- **Lista słowników**: GET /api/dictionaries - przegląd dostępnych słowników
- **Lista ulic**: GET /api/dictionaries/{city}/{decade}/streets - szczegóły słownika


## 5. Schematy Danych

### 5.1 Street Schema
```json
{
  "type": "object",
  "properties": {
    "id": {"type": "integer"},
    "user_id": {"type": "integer"},
    "city": {"type": "string", "maxLength": 100},
    "decade": {"type": "string", "maxLength": 20},
    "prefix": {"type": "string", "enum": ["ul.", "pl.", "al.", "-"], "default": "ul."},
    "main_name": {"type": "string", "maxLength": 200},
    "main_name_cs": {"type": "string", "maxLength": 200},
    "variants": {"type": "array", "items": {"type": "string"}},
    "misspellings": {"type": "array", "items": {"type": "string"}},
    "is_rejected": {"type": "boolean", "default": false},
    "source": {"type": "string", "enum": ["ai", "manual"], "default": "ai"},
    "created_at": {"type": "string", "format": "date-time"},
    "updated_at": {"type": "string", "format": "date-time"}
  },
  "required": ["user_id", "city", "decade", "main_name", "main_name_cs"]
}
```

### 5.2 Error Response Schema
```json
{
  "type": "object",
  "properties": {
    "error": {"type": "string"},
    "details": {"type": "object", "additionalProperties": true}
  },
  "required": ["error"]
}
```

### 5.3 Pagination Schema
```json
{
  "type": "object",
  "properties": {
    "page": {"type": "integer", "minimum": 1},
    "per_page": {"type": "integer", "minimum": 1, "maximum": 100},
    "total": {"type": "integer", "minimum": 0},
    "total_pages": {"type": "integer", "minimum": 0}
  },
  "required": ["page", "per_page", "total", "total_pages"]
}
```

## 6. Priorytety Implementacji

### Faza 1 (Podstawowe REST API dla eksportu)
1. GET /api/dictionaries - lista dostępnych słowników
2. GET /api/export/{city}/{decade}/txt - RESTful eksport TXT
3. GET /api/export/{city}/{decade}/json - RESTful eksport JSON
4. GET /api/dictionaries/{city}/{decade}/streets - lista ulic dla słownika

### Faza 2 (Rozszerzenia Streets API)
1. Dodanie paginacji do GET /api/dictionaries/{city}/{decade}/streets
2. Dodanie filtrowania (search, source) do listy ulic
3. Optymalizacja zapytań SQL dla lepszej wydajności

### Faza 3 (Optymalizacje - jeśli potrzebne)
1. Cache dla często używanych słowników
2. API versioning (/api/v1/)
3. Rate limiting dla eksportu
4. Kompresja odpowiedzi JSON


## 7. Bezpieczeństwo i Walidacja

### 7.1 Autoryzacja
- Wszystkie REST endpointy wymagają uwierzytelnionego użytkownika (Flask-Login session)
- Sprawdzanie własności zasobów (user_id dla ulic i słowników)
- Rate limiting dla eksportu i zapytań API

### 7.2 Walidacja
- File type i size validation dla uploadów
- Unikalność ulic: user_id + city + decade + main_name
- Prefix validation (zamknięta lista)
- JSON schema validation dla request payloads

### 7.3 Error Handling
- Standardowe HTTP status codes
- Szczegółowe error messages w JSON
- Brak wycieku wrażliwych danych w errorach
