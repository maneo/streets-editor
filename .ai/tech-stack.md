Frontend:
- Renderowanie stron przy pomocy wbudowanego we flaska wsparcia dla szablonów jinja
- Dynamiczne elementy stron przy wykorzystaniu czystego javascriptu
- Tailwind 4 pozwala na wygodne stylowanie aplikacji

Backend:
- Jako bazę danych wykorzystamy SQLite
- Jako warstwę dostępową do bazy SQLAlchemy
- Całość logiki implementowana w Pythonie przy wsparciu Flaska
- Rejestracja i autentykacja przy wykorzstaniu modułu Flask-login

AI - Komunikacja z modelami przez usługę Openrouter.ai:
- Dostęp do szerokiej gamy modeli (OpenAI, Anthropic, Google i wiele innych), które pozwolą nam znaleźć rozwiązanie zapewniające wysoką efektywność i niskie koszta
- Pozwala na ustawianie limitów finansowych na klucze API

CI/CD i Hosting:
- Github Actions do tworzenia pipeline’ów CI/CD
- DigitalOcean do hostowania aplikacji za pośrednictwem obrazu docker
