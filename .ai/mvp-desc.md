### Główny problem
Stworzyłem narzędzie do ekstrakcji danych adresowych ze starych gazet. Aby to narzędzie działało poprawnie potrzebna jest baza danych zawierająca informacje o ulicach istniejących w danym mieście w konkretnej dekadzie (np. Poznań w latach 1920-1929). Przygotowywanie takiej listy ulic jest dość żmudne i czasochłonne, co utrudnia wykorzystanie narzedzia do ekstrakcji dla kolejnych dekad i miast.

### Najmniejszy zestaw funkcjonalności
- Tworzenie listy nazw ulic na podstawie istniejących plików json
- Tworzenie listy nazw ulic przez AI na podstawie starych planów miejskich
- Przeglądanie listy nazwa ulic dla danej dekady
- Przeglądanie listy nazwa ulic dla danegp miasta
- Edycja wpisu poświęconego konkretnej ulicy, możliwość dodania wariantów zapisu
- Manualne dodawanie nowej ulicy do spisu dla danej dekady i miasta
- Dostęp do edycji tylko po zalogowaniu
- Możliwość rejestracji nowego użytkownika
- Możliwośc wyeksportowania słowników dla konkretnej dekady i miasta w formacie json

### Co NIE wchodzi w zakres MVP
- Rozbudowany system uprawnień i ról dla użytkowników
- Integracja z Google Maps czy innymi usługami mapowymi
- Interfejs RESTowy pozwalający na dostęp do stworzonych słowników poprzez API
