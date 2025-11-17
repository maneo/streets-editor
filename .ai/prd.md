# Dokument wymagań produktu (PRD) - Streets Dictionary Editor

## 1. Przegląd produktu
Streets Dictionary Editor to aplikacja webowa wspierająca tworzenie i edytowanie słowników nazw ulic dla wybranych miast i dekad historycznych. Aplikacja umożliwia użytkownikom:
- załadowanie skanu historycznego planu miasta (JPG/PNG ≤ 50 MB),
- automatyczną ekstrakcję listy ulic przy użyciu modelu Gemini 2.5 Pro,
- ręczną weryfikację i wzbogacanie listy,
- pobranie wyników w formacie TXT lub JSON.

Produkt adresuje potrzeby historyków, badaczy i twórców narzędzi OCR, którzy wymagają dokładnych słowników nazw ulic, aby zwiększyć skuteczność ekstrakcji danych z archiwalnych gazet.

## 2. Problem użytkownika
Przygotowanie kompletnych list ulic dla danego miasta i dekady jest czasochłonne i wymaga ręcznego przeglądania źródeł historycznych. Brak takich list ogranicza zastosowanie narzędzi do ekstrakcji adresów z gazet. Użytkownicy potrzebują narzędzia, które:
- automatyzuje generowanie wstępnej listy ulic,
- upraszcza weryfikację i korektę danych,
- zapewnia szybki eksport słowników w ustandaryzowanym formacie,
- zachowuje prostotę (brak skomplikowanych ról i uprawnień).

## 3. Wymagania funkcjonalne
* FR-001 - Użytkownik może się zarejestrować i zalogować (prosta autoryzacja).
* FR-002 - Po zalogowaniu użytkownik może załadować jeden plik JPG/PNG ≤ 50 MB.
* FR-003 - Użytkownik definiuje miasto i dekadę, które będą przypisane do sesji ekstrakcji.
* FR-004 - System uruchamia ekstrakcję AI (Gemini 2.5 Pro) i zwraca listę proponowanych ulic w ≤ 5 min.
* FR-006 - Jeśli AI zwróci pustą listę, system informuje użytkownika i umożliwia ręczne dodawanie ulic.
* FR-007 - Użytkownik może edytować każdą pozycję: zmienić nazwę, dodać warianty zapisu, oznaczyć jako odrzuconą.
* FR-008 - Użytkownik może ręcznie dodać nową ulicę z walidacją unikalności (miasto + dekada + main_name).
* FR-009 - Użytkownik może pobrać bieżące wyniki sesji jako plik TXT.
* FR-010 - Użytkownik może wyeksportować zweryfikowany słownik jako plik JSON zgodny z przykładem.
* FR-011 - Pliki eksportu są dostępne tylko dla zalogowanych użytkowników.
* FR-012 - Po zamknięciu przeglądarki lub zakończeniu sesji skan i niezatwierdzone dane są usuwane.
* FR-013 - System obsługuje wiele równoległych zadań ekstrakcji przy niskim poziomie równoczesności (brak twardego limitu).
* FR-014 - System komunikuje błędy (np. niepoprawny format pliku, przekroczenie limitu rozmiaru).

## 4. Granice produktu
- Brak wersjonowania słowników i historii zmian.
- Brak rozbudowanych ról i uprawnień (jedynie prosty login).
- Brak integracji z usługami mapowymi (Google Maps itp.).
- Brak publicznego REST API w MVP.
- Brak backupu danych i mechanizmów przywracania poza sesją.
- Prefiksy ulic ograniczone do zamkniętej listy („ul.”, „pl.”, „al.”, „-”).
- Tune-owanie modeli AI, kolejki z limitem zadań, centralny system logowania – poza zakresem MVP.

## 5. Historyjki użytkowników
| ID | Tytuł | Opis | Kryteria akceptacji |
|----|-------|------|---------------------|
| US-001 | Rejestracja użytkownika | Jako nowy użytkownik chcę utworzyć konto, aby uzyskać dostęp do aplikacji. | • Formularz rejestracji przyjmuje e-mail i hasło.<br>• Po rejestracji użytkownik zostaje automatycznie zalogowany.<br>• Nie można zarejestrować konta na już używany e-mail. |
| US-002 | Logowanie | Jako zarejestrowany użytkownik chcę się zalogować, aby korzystać z funkcji aplikacji. | • Formularz logowania wymaga poprawnych danych uwierzytelniających.<br>• Po zalogowaniu użytkownik widzi panel uploadu.<br>• Przy błędnych danych system wyświetla komunikat. |
| US-003 | Upload skanu | Jako użytkownik chcę załadować plik JPG/PNG ≤ 50 MB, aby rozpocząć ekstrakcję. | • System akceptuje tylko JPG/PNG do 50 MB.<br>• Po wysłaniu pliku użytkownik podaje miasto i dekadę.<br>• Błędny format lub rozmiar powoduje komunikat o błędzie. |
| US-004 | Uruchomienie ekstrakcji | Jako użytkownik chcę uruchomić ekstrakcję AI, aby otrzymać listę ulic. | • Wynik pojawia się w ≤ 5 min.<br>• W przypadku błędu użytkownik otrzymuje komunikat. |
| US-005 | Obsługa pustego wyniku | Jako użytkownik chcę wiedzieć, gdy AI nie wykryje ulic, aby móc dodać je ręcznie. | • System wyświetla komunikat o braku propozycji.<br>• Pole do dodawania ulic jest aktywne. |
| US-006 | Edycja wpisu | Jako redaktor chcę poprawić nazwę ulicy lub dodać warianty, aby uzyskać poprawny słownik. | • Użytkownik może zmienić main_name, prefix, variants, misspellings.<br>• Zmiana zapisuje się lokalnie do czasu eksportu. |
| US-007 | Dodanie nowej ulicy | Jako redaktor chcę dodać brakującą ulicę, aby słownik był kompletny. | • Formularz dodawania sprawdza unikalność (miasto + dekada + main_name).<br>• Przy duplikacie pojawia się komunikat.<br>• Nowa ulica pojawia się na liście. |
| US-008 | Walidacja unikalności | Jako system chcę uniemożliwić duplikaty, aby zachować spójność danych. | • Przy próbie dodania/edycji duplikatu wyświetlany jest błąd i zmiana jest odrzucana. |
| US-009 | Pobranie TXT | Jako użytkownik chcę pobrać listę ulic jako TXT, aby zachować wyniki sesji. | • Przycisk „Pobierz TXT” generuje plik z aktualną listą.<br>• Plik zawiera jedną nazwę ulicy na linię. |
| US-010 | Eksport JSON | Jako użytkownik chcę wyeksportować zweryfikowany słownik jako JSON, aby użyć go w innych narzędziach. | • Eksport dostępny po zakończeniu weryfikacji.<br>• JSON zgodny ze wzorem w dokumentacji.<br>• Plik pobiera się lokalnie. |
| US-011 | Wylogowanie | Jako użytkownik chcę się wylogować, aby zakończyć sesję. | • Po wylogowaniu sesja jest zamykana.<br>• Skan i niezatwierdzone dane są usunięte. |
| US-012 | Pogląd wgranego pliku | Jako użytkownik w trakcie weryfikacji wyekstrahowanych ulic chce mieć pogląd skanu który wgrałem | • Nad listą ulic i edytorem wyświetla się pogląd wgranej mapy.<br> |

## 6. Metryki sukcesu
- MS-001 - ≥ 80 % propozycji AI zaakceptowanych bez edycji (precyzja ekstrakcji).
- MS-002 - Czas ekstrakcji ≤ 5 min dla pliku 50 MB (wydajność).
- MS-003 - 0 % duplikatów w zatwierdzonym słowniku (jakość danych).
- MS-004 - Co najmniej jeden kompletny słownik (Poznań 1940-1949) wyeksportowany jako JSON (adopcja).
- MS-005 - ≥ 90 % udanych uploadów plików < 50 MB (stabilność).
