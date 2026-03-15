# Lab 2 - Three-Layer Server Application

A Python implementation of a three-layered project-planning server based on
the class diagram from Lab 1.b. The application reads project data from a
single CSV file and persists it to a relational database through an ORM.

The codebase is structured around two design patterns the lab explicitly
asks for: **Inversion of Control** (high-level modules don't know which
concrete classes implement the abstractions they depend on) and
**Dependency Injection** (the wiring between abstract and concrete is done
in one place — the composition root — and passed in through constructors).

## Structure

```
lab2/
├── requirements.txt
├── data/
│   └── project_data.csv               ← generated, 1000+ rows, all data types
├── scripts/
│   └── generate_csv.py                ← CLI module that creates the CSV
└── src/
    ├── main.py                        ← application entry point
    ├── dal/                           ← Data Access Layer
    │   ├── interfaces.py              ← abstract contracts (IRepository, IUnitOfWork, ICsvDataReader)
    │   ├── models.py                  ← SQLAlchemy ORM mappings
    │   ├── repositories.py            ← concrete repository implementations
    │   ├── unit_of_work.py            ← UoW wrapper around a SQLAlchemy session
    │   ├── csv_reader.py              ← CSV file reader
    │   └── database.py                ← engine + sessionmaker factory
    ├── bll/                           ← Business Logic Layer
    │   ├── interfaces.py              ← service contracts (IDataImportService) + ImportReport
    │   └── services.py                ← DataImportService — orchestrates the import flow
    ├── presentation/                  ← Presentation Layer (interfaces only, per spec)
    │   └── interfaces.py
    └── di/
        └── container.py               ← composition root — the only place concretes meet
```

## How to run it

Install SQLAlchemy:
```bash
pip install -r requirements.txt
```

Generate the CSV (≥ 1000 rows, deterministic with `--seed`):
```bash
python -m scripts.generate_csv --output data/project_data.csv --projects 30
```

Import the CSV into a fresh SQLite database:
```bash
python -m src.main --csv data/project_data.csv --clear
```

You should see a report like:
```
ImportReport(projects=30, tasks=360, resources=65, assignments=341,
             dependencies=182, calendars=30, baselines=69,
             skipped=0, errors=0)
Total entities created: 1077
```

Inspect the database with any SQLite client, or with one-liners like:
```bash
sqlite3 project_planning.db "SELECT task_type, COUNT(*) FROM tasks GROUP BY task_type;"
```

## How the three layers fit together

The three layers form a strict one-way dependency chain. Higher layers
reference lower layers only through abstractions:

```
   Presentation  ──depends on──▶  BLL interfaces
                                       ▲
                                       │ (concretes wired in di/container.py)
                                       │
                          BLL services ┘
                                       │
                                       ▼
                                  DAL interfaces  ◀──depends on──┐
                                       ▲                          │
                                       │                          │
                          DAL repositories + UoW + CSV reader     │
                                                                  │
                                                       composition root
```

The arrows are deliberate: the BLL never imports anything from
`dal/repositories.py`, `dal/csv_reader.py`, or `dal/unit_of_work.py`.
It only ever touches `dal/interfaces.py`. The same goes for the
(currently empty) presentation layer — it would only see `bll/interfaces.py`.

Concrete wiring lives in exactly one place: `src/di/container.py`. Swapping
SQLite for PostgreSQL, or the CSV reader for a JSON reader, would only
require changes there. This is the practical payoff of IoC + DI.

## Data Access Layer (DAL)

The DAL has three responsibilities: define the database schema (via the ORM),
provide CRUD-style access to that schema (repositories under a unit of work),
and read records from the input CSV.

The ORM mappings in `models.py` follow the class diagram from Lab 1 directly.
The `Task` and `Resource` hierarchies use **single-table inheritance**, where
all subclasses share one table and a discriminator column (`task_type`,
`resource_type`) tells SQLAlchemy which Python class to instantiate. The
choice was made for simplicity — joined-table inheritance would scatter
each hierarchy across multiple tables and complicate the demo without
adding clarity. `Assignment` is its own table because it's the
**association class** linking Task and Resource, carrying its own data
(`units`, `work`, `actual_work`, `cost`).

The repositories in `repositories.py` all share one generic base
(`SqlAlchemyRepository[T]`) and only differ in the model they manage.
This avoids hand-written `add` / `get` / `list` methods on every repo
and keeps the codebase compact.

The `SqlAlchemyUnitOfWork` is a context manager that owns one SQLAlchemy
`Session` and exposes one repository per aggregate. It commits on
successful exit and rolls back on exception — a standard pattern that
makes transactional boundaries explicit. The BLL uses it like this:

```python
with self._uow as uow:
    uow.projects.add(project)
    uow.tasks.add(task)
    uow.commit()
```

If anything fails between `__enter__` and `commit`, the rollback is
automatic.

The `CsvDataReader` is intentionally minimal — it streams rows out of
the file as `CsvRecord` objects with attribute access. All parsing
(string-to-date, string-to-bool, string-to-int) happens in the BLL,
not the DAL, because parsing is business logic, not data access.

## Business Logic Layer (BLL)

The BLL has one service: `DataImportService`. Its constructor takes two
abstractions:

```python
class DataImportService(IDataImportService):
    def __init__(self, csv_reader: ICsvDataReader, uow: IUnitOfWork): ...
```

It never imports `CsvDataReader` or `SqlAlchemyUnitOfWork`. That's the
operational definition of "depends on interfaces, not implementations."

The import flow is:

1. Read all CSV rows up front (we need multiple passes for foreign-key
   resolution — a Task referencing a SummaryTask might come before its
   parent in the file).
2. Group rows by `record_type`.
3. Insert in an order that respects foreign keys:
   `Project → Calendar/Baseline → Resource → SummaryTask → Task →
   Milestone → Dependency → Assignment`.
4. Maintain in-memory lookup tables (`ext_id → primary_key`) so that
   later rows resolve their parent IDs without re-querying the database.
5. Wrap everything in a single Unit-of-Work transaction so a failure
   anywhere rolls back the whole import.

The CSV uses a single wide schema where each row's columns mean different
things depending on its `record_type`. Cross-references between records
use **external IDs** (`ext_id`) rather than database primary keys — the
CSV doesn't know the auto-incremented IDs SQLAlchemy will assign, so it
uses its own naming scheme (`PR001`, `T012_R3`, `RH024`, etc.) and the
service translates them to real IDs at insert time.

## Presentation Layer

Per the lab specification, the presentation layer contains only
interfaces. They describe what controllers and views *would* look like
in a real UI: methods like `display_project_list`, `import_csv`,
`show_tasks_for_project`. None are instantiated.

A real implementation (a Flask route, a CLI menu, a desktop GUI) would
inject `IDataImportService` and other BLL services through the same
container that wires everything else.

## CSV file format

The file is a single CSV with a wide column set. Each row represents
one entity, and the `record_type` column tells the service which entity
kind to build. Most columns are optional and only filled in when
relevant to that record type.

| record_type        | required columns (besides record_type, ext_id, name)                |
| ------------------ | ------------------------------------------------------------------- |
| `PROJECT`          | start_date                                                          |
| `CALENDAR`         | project_ext_id                                                      |
| `BASELINE`         | project_ext_id, saved_date                                          |
| `HUMAN_RESOURCE`   | code; optionally email, role, skills, cost_per_hour, max_units      |
| `MATERIAL_RESOURCE`| code, unit, consumption_rate                                        |
| `COST_RESOURCE`    | code, fixed_cost                                                    |
| `SUMMARY_TASK`     | project_ext_id                                                      |
| `TASK`             | project_ext_id; optionally summary_ext_id                           |
| `MILESTONE`        | project_ext_id                                                      |
| `DEPENDENCY`       | predecessor_ext_id, successor_ext_id, dep_type ∈ {FS,SS,FF,SF}      |
| `ASSIGNMENT`       | task_ext_id, resource_ext_id                                        |

The generator at `scripts/generate_csv.py` produces a deterministic file
(seed-controlled) with at least 1000 rows distributed across all record
types.

The two patterns the lab asks for are visible in two places.

**Inversion of Control** is shown by the import direction: `bll/services.py`
imports from `dal/interfaces.py` but never from `dal/repositories.py`,
`dal/csv_reader.py`, or `dal/unit_of_work.py`. The high-level module
controls the flow; the low-level modules conform to its interfaces. This
is the opposite of a naive design where the BLL would `from dal.csv_reader
import CsvDataReader` and instantiate it directly.

**Dependency Injection** is shown by the constructors. `DataImportService`
takes its dependencies as constructor arguments, never creates them
itself. The `Container` class in `di/container.py` is where the choice
of which concrete class to inject is finally made — and it's the only
place in the codebase where concrete DAL classes are imported alongside
their abstractions.

The Unit of Work and Repository patterns are bonus-points territory:
they're not strictly required by the lab text but they're standard for
ORM-backed applications and demonstrate mature design thinking.
