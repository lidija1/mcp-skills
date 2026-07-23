# Dashboard database guide

Ovaj projekat trenutno podrzava dve varijante baze za dashboard:

- lokalni SQLite fajl, najjednostavniji za razvoj na svom racunaru
- PostgreSQL preko connection string-a, kao opcija za eksternu bazu

`main` treba da ostane cist i stabilan. Eksperimenti i prosirenja mogu da idu na posebnu granu, na primer `skills`.

## Koja baza se koristi

Backend bira bazu preko environment promenljivih:

1. Ako postoji `DASHBOARD_DATABASE_URL`, koristi se ta baza.
2. Ako ne postoji `DASHBOARD_DATABASE_URL`, ali postoji `DATABASE_URL`, koristi se ta baza.
3. Ako nijedna od te dve promenljive nije podesena, koristi se lokalni SQLite fajl.

Kod koji bira bazu je u:

- `dashboard/backend/dashboard_db.py`
- `dashboard/backend/database.py`

Trenutno je u lokalnom `.env` fajlu podeseno `DASHBOARD_DATABASE_URL`, pa se koristi PostgreSQL. Provera je uspesno prosla komandom:

```powershell
.\venv\Scripts\python.exe dashboard\backend\create_tables.py
```

Rezultat je bio da su dashboard tabele spremne u PostgreSQL bazi.

## Lokalna baza: SQLite

Za sada je ovo najprakticnija opcija za lokalni razvoj. Ne treba poseban database server.

U `.env` ostavi SQLite putanju, a ukloni ili zakomentarisi `DASHBOARD_DATABASE_URL`:

```env
DASHBOARD_DB_PATH=data/dashboard.db
# DASHBOARD_DATABASE_URL=
```

Ako zelis da samo privremeno pokrenes backend sa lokalnom bazom, bez menjanja `.env` fajla, u PowerShell-u pokreni:

```powershell
$env:DASHBOARD_DATABASE_URL=''
$env:DATABASE_URL=''
.\venv\Scripts\python.exe dashboard\backend\create_tables.py
.\venv\Scripts\python.exe dashboard\backend\main.py
```

SQLite fajl se u ovoj konfiguraciji nalazi ovde:

```text
dashboard/backend/data/dashboard.db
```

Backend sam kreira foldere i tabele ako ne postoje.

## Eksterna baza: PostgreSQL

PostgreSQL ostaje opcija kada zelis bazu van SQLite fajla. U `.env` podesi:

```env
DASHBOARD_DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/sendbox_dashboard
```

Ne commituj pravi `.env` fajl. U repo ide samo `.env.example`.

Da bi PostgreSQL radio, mora da postoji database server i baza, na primer:

- server: `localhost`
- port: `5432`
- database name: `sendbox_dashboard`
- user: `postgres`

Ako baza jos ne postoji, napravi je kroz pgAdmin, DBeaver, DataGrip, `psql`, ili neki drugi PostgreSQL klijent.

Kada je connection string podesen, inicijalizuj tabele:

```powershell
.\venv\Scripts\python.exe dashboard\backend\create_tables.py
```

Zatim pokreni backend:

```powershell
.\venv\Scripts\python.exe dashboard\backend\main.py
```

Na startu backend ispisuje aktivnu bazu:

- `ACTIVE DB: PostgreSQL` kada koristi PostgreSQL
- putanju do `dashboard.db` kada koristi SQLite

## Migracija iz SQLite u PostgreSQL

Ako imas podatke u lokalnom SQLite fajlu i zelis da ih prebacis u PostgreSQL:

```powershell
.\venv\Scripts\python.exe dashboard\backend\migrate_sqlite_to_postgres.py
```

Skripta koristi:

- `DASHBOARD_DB_PATH` za SQLite izvor
- `DASHBOARD_DATABASE_URL` za PostgreSQL cilj

Mozes i eksplicitno da prosledis putanje:

```powershell
.\venv\Scripts\python.exe dashboard\backend\migrate_sqlite_to_postgres.py --sqlite-path dashboard\backend\data\dashboard.db --postgres-url postgresql://postgres:YOUR_PASSWORD@localhost:5432/sendbox_dashboard
```

## Brza provera

Za proveru koja baza je aktivna:

```powershell
.\venv\Scripts\python.exe dashboard\backend\create_tables.py
```

Ako zelis lokalni SQLite za sada, najcistije je da u `.env` zakomentarises `DASHBOARD_DATABASE_URL` i ostavis:

```env
DASHBOARD_DB_PATH=data/dashboard.db
```

PostgreSQL moze da ostane dokumentovana opcija u `.env.example`, a pravi connection string cuvaj samo lokalno u `.env`.
