<conversation_summary>
<decisions>
1. `city` (i.e. miasto) and `decade` będą zwykłymi kolumnami w tabeli `streets`; nie powstaną osobne tabele referencyjne.  
2. Przesłane pliki (skany) nie będą przechowywane w bazie ani modelowane w schemacie.  
3. Nie modelujemy sesji ekstrakcji ani ich statusu w bazie danych.  
4. Nie będzie wersjonowania ulic; zapisywane są wszystkie rekordy ze statusem w polu rejected
5. Unikalność ulicy wymusza złożony klucz (`city`, `decade`, `main_name`).  
6. Informacje o alternatywnych zapisach nazw (`variants` i `misspellings`) będą przechowywane w polach w tabeli `streets`
7. RLS i rozbudowane bezpieczeństwo wieloużytkownikowe nie są wymagane.  
8. Klucze główne w tabelach będą integer PK.  
9. Kolumny czasowe: `created_at` (default `now()`), `updated_at`.  
10. Uzytkownicy będą przechowywani w tabeli users, wykorzystywane będą mechanizmy flask-login
</decisions>

<matched_recommendations>
1. Dodanie kolumn `created_at` i `updated_at`  
2. Unikalny indeks (`city`, `decade`, `main_name`)
3. Brak widoków, brak `pg_trgm`, brak dodatkowych indeksów.
</matched_recommendations>

<database_planning_summary>
• Główna tabela `streets`  
 – `id int4 PK default gen_random_uuid()`  
 – `city varchar NOT NULL`  
 – `decade varchar NOT NULL`  
 – `prefix varchar NOT NULL default '-'`  
 – `main_name varchar NOT NULL`  
 – `main_name_cs varchar`  
 – `variants text`  
 – `misspellings text`  
 – `created_at timestamptz default now()`  
 – `updated_at timestamptz`  

• Tabela `users`
 – `id int4 PK default gen_random_uuid()`  
 – `email varchar NOT NULL`  
 – `password_hash varchar NOT NULL`  
 – `created_at timestamptz default now()`  

• Bez tabel sesji, plików, historii czy eksportów; brak soft-delete i RLS.

• Bezpieczeństwo ogranicza się do standardowych uprawnień bazy; brak izolacji użytkowników (single-user scenario).

• Skalowalność i audyt uznane za niewymagane w MVP; architektura pozostaje prosta, umożliwiając późniejsze rozszerzenia (np. dodanie RLS, nowych indeksów lub widoków) bez łamania obecnego schematu.

</database_planning_summary>

<unresolved_issues>
Brak nierozwiązanych kwestii – wszystkie rekomendacje zostały zaakceptowane lub odrzucone jednoznacznie.
</unresolved_issues>
</conversation_summary>
