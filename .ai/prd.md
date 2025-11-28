# Dokument wymagań produktu (PRD) - Streets Dictionary Editor

## 1. Przegląd produktu
Streets Dictionary Editor to aplikacja webowa wspierająca tworzenie i edytowanie słowników nazw ulic dla wybranych miast i dekad historycznych. Aplikacja umożliwia użytkownikom:
- załadowanie skanu historycznego planu miasta (JPG/PNG ≤ 50 MB),
- automatyczną ekstrakcję listy ulic przy użyciu modelu Gemini 2.5 Pro,
- ręczną weryfikację i wzbogacanie listy,
- pobranie wyników w formacie TXT lub JSON,
- zarządzanie domyślnym słownikiem ulic współczesnych dla każdego miasta,
- dodawanie rozszerzonych atrybutów do ulic domyślnych (geolokalizacja, linki zewnętrzne, dzielnica, informacje historyczne).

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
* FR-015 - Użytkownik może oznaczyć ulicę jako domyślną (pole `default_street`) - ulice domyślne, w podstawym scenariuszu dotyczą dekady 2020-2029 i pełnią rolę współczesnego słownika referencyjnego.
* FR-016 - Użytkownik może dodawać rozszerzoną treść do ulic domyślnych: geolokalizację (latitude/longitude), linki zewnętrzne (Wikipedia, OpenStreetMap), dzielnicę, kod pocztowy, informacje historyczne.
* FR-017 - System przechowuje treść ulic domyślnych w osobnej tabeli `street_content` powiązanej z ulicą relacją jeden-do-jednego.
* FR-018 - System zapewnia widok zarządzania ulicami domyślnymi dla danego miasta, gdzie użytkownik może przeglądać listę ulic domyślnych i dodawać/edytować ich treść.
* FR-019 - Użytkownik może edytować lub usuwać treść przypisaną do ulicy domyślnej, ale tylko dla ulic oznaczonych jako domyślne.

## 4. Granice produktu
- Brak wersjonowania słowników i historii zmian (z wyjątkiem pola `updated_by` w treści ulic domyślnych).
- Brak rozbudowanych ról i uprawnień (jedynie prosty login; wszyscy użytkownicy mogą zarządzać ulicami domyślnymi).
- Brak integracji z usługami mapowymi (Google Maps itp.) - geolokalizacja przechowywana jako współrzędne, linki do OpenStreetMap są statyczne.
- Brak automatycznego importu danych geolokalizacyjnych - użytkownik musi wprowadzić je ręcznie.
- Brak walidacji poprawności współrzędnych GPS przy wprowadzaniu geolokalizacji.
- Brak automatycznego dopasowywania ulic historycznych do ulic domyślnych - oznaczenie i dodawanie treści jest ręczne.
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
| US-013 | Oznaczenie ulicy jako domyślnej | Jako użytkownik chcę oznaczyć ulicę jako domyślną (współczesną), aby utworzyć bazę referencyjną dla danego miasta. | • W edytorze ulic można oznaczyć ulicę flagą `default_street`.<br>• Oznaczenie można zmienić w każdej chwili. |
| US-014 | Dodanie treści do ulicy domyślnej | Jako użytkownik chcę dodać rozszerzone informacje do ulicy domyślnej (geolokalizacja, linki, dzielnica), aby wzbogacić słownik o dodatkowe dane. | • Dla ulic oznaczonych jako domyślne dostępne jest pole do dodawania treści.<br>• Można podać: współrzędne GPS, linki zewnętrzne, dzielnicę, kod pocztowy, informacje historyczne.<br>• Treść jest opcjonalna - ulica domyślna może istnieć bez treści. |
| US-015 | Zarządzanie ulicami domyślnymi | Jako użytkownik chcę mieć dedykowany widok do zarządzania wszystkimi ulicami domyślnymi dla miasta, aby łatwo dodawać i edytować ich treść. | • Istnieje widok listy ulic domyślnych dla danego miasta.<br>• Widok pokazuje które ulice mają przypisaną treść, a które nie.<br>• Można otworzyć modal do dodawania/edycji treści dla każdej ulicy. |
| US-016 | Edycja treści ulicy domyślnej | Jako użytkownik chcę edytować istniejącą treść ulicy domyślnej, aby aktualizować informacje (np. zmienione linki). | • Można edytować wszystkie atrybuty treści ulicy domyślnej.<br>• Zmiany są zapisywane natychmiast po zapisie.<br>• Można również całkowicie usunąć treść ulicy domyślnej. |

## 6. Metryki sukcesu
- MS-001 - ≥ 80 % propozycji AI zaakceptowanych bez edycji (precyzja ekstrakcji).
- MS-002 - Czas ekstrakcji ≤ 5 min dla pliku 50 MB (wydajność).
- MS-003 - 0 % duplikatów w zatwierdzonym słowniku (jakość danych).
- MS-004 - Co najmniej jeden kompletny słownik (Poznań 1940-1949) wyeksportowany jako JSON (adopcja).
- MS-005 - ≥ 90 % udanych uploadów plików < 50 MB (stabilność).
