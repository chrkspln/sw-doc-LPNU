# Lab 3 — MVC Web Application for Project Planning

A Flask-based web application that lets a user view, create, edit and delete
project-planning data through a browser. The application is built on top of
the three-layered server from Lab 2 — the DAL and the business-logic services
are reused unchanged, and a new presentation layer (Flask routes + Jinja2
templates) is layered on top.

The domain comes from Lab 1, variant 27: project-plan creation in the style
of Microsoft Project. The class diagram from that lab is what the database
schema is mapped from, and the use-case diagram is what the controllers
implement.

## How to run it

Install both SQLAlchemy and Flask:

```bash
pip install -r requirements.txt
```

Generate the test data (a deterministic CSV with around 1077 rows covering
every entity type), then load it into a fresh SQLite database:

```bash
python -m scripts.generate_csv --output data/project_data.csv
python -m src.main import --csv data/project_data.csv --clear
```

Start the web server:

```bash
python -m src.main web --port 5000
```

Open `http://127.0.0.1:5000/` in a browser. You will land on the dashboard,
which shows aggregate counts of projects, tasks, resources and assignments
broken down by their status or type. From there the sidebar leads to the
projects list (full CRUD), and to the resources catalog (full CRUD).

## Project layout

```
lab3/
├── requirements.txt
├── data/project_data.csv                 ← generated, ~1077 rows
├── scripts/generate_csv.py               ← CLI test-data generator
└── src/
    ├── main.py                           ← `import` + `web` subcommands
    ├── dal/                              ← Data Access Layer (from Lab 2)
    │   ├── interfaces.py                 ← IRepository, IUnitOfWork, ICsvDataReader
    │   ├── models.py                     ← SQLAlchemy ORM mappings
    │   ├── repositories.py               ← concrete repos
    │   ├── unit_of_work.py
    │   ├── csv_reader.py
    │   └── database.py
    ├── bll/                              ← Business Logic Layer
    │   ├── interfaces.py                 ← IDataImportService, IProjectService,
    │   │                                    ITaskService, IResourceService, IStatsService
    │   ├── dto.py                        ← plain dataclasses passed to controllers
    │   └── services.py                   ← concrete services (uow_factory pattern)
    ├── presentation/                     ← Lab 3 — the new layer
    │   ├── app.py                        ← Flask app factory
    │   ├── controllers/                  ← blueprints = the "Controller" of MVC
    │   │   ├── home.py                   ← GET / (dashboard)
    │   │   ├── projects.py               ← full CRUD on the main entity
    │   │   ├── tasks.py                  ← CRUD on Tasks within a Project
    │   │   └── resources.py              ← full CRUD on the resource pool
    │   ├── templates/                    ← Jinja2 = the "View" of MVC
    │   │   ├── base.html, home.html
    │   │   ├── projects/list.html, detail.html, form.html
    │   │   ├── tasks/form.html
    │   │   └── resources/list.html, detail.html, form.html
    │   └── static/style.css
    └── di/container.py                   ← composition root (extended)
```

## Mapping the lab requirements onto the code

The lab text has six numbered requirements. Going through them one by one:

**Requirement 1: choose the main entity.** The main entity is **Project**.
Every other domain object — tasks, milestones, summary tasks, calendars,
baselines, assignments — exists in the context of a project. In the Lab 1
class diagram, Project is the aggregate root that owns all other entities
through composition relationships. Picking it as the main entity for Lab 3
means the URL hierarchy becomes natural (`/projects/`, `/projects/<id>`,
`/projects/<id>/tasks/new`) and the CRUD requirement applies to it
directly. Resources are organisation-wide and don't belong to any single
project, which is why they get a separate top-level menu item with their
own full CRUD flow rather than being nested under a project.

**Requirement 2: controllers and action methods.** Each blueprint in
`src/presentation/controllers/` is a controller in the MVC sense — a
group of action methods (route handlers) that orchestrate the response
to an HTTP request. The projects controller has seven action methods
covering the full lifecycle: `list_projects`, `show_project`,
`new_project_form`, `create_project`, `edit_project_form`,
`update_project`, `delete_project`. The tasks controller mirrors the
same shape for nested task management. The home controller has one
action method that builds a dashboard. Each method takes whatever URL
parameters apply, asks a BLL service for data, and either renders a
template or issues an HTTP redirect.

**Requirement 3: model that interacts with the database, populated with
test data.** The "Model" of MVC is split across the DAL and BLL in this
codebase, which matches the lab text: the lab says "the model describes
the data logic and interacts with the database," which is exactly what
the DAL plus the services do together. The DAL holds the ORM mappings
and the persistence primitives; the BLL holds the use cases and exposes
the model to controllers through service interfaces. The database is
populated by the Lab 2 import pipeline — a CSV with around 1077 rows
covering every record type goes through the same `DataImportService`
that Lab 2 demonstrated.

**Requirement 4: ability to add, edit and delete data.** All three
top-level entities — projects, tasks, and resources — support full CRUD
through the web UI. Creating a project is a two-step flow —
`GET /projects/new` renders the form, `POST /projects/` handles the
submission, validates the inputs, calls `IProjectService.create_project`,
flashes a success message, and redirects to the new project's detail
page. Editing follows the same pattern with `GET/POST /projects/<id>/edit`.
Deletion is a `POST` to `/projects/<id>/delete` guarded by a JavaScript
confirm dialog. SQLAlchemy takes care of cascading the delete to the
project's tasks, calendars, baselines and assignments — that's a
`cascade="all, delete-orphan"` declaration on the Project model from
Lab 2. Tasks have their own CRUD flow nested under a project. Resources
have a parallel CRUD flow at `/resources/`, with one extra wrinkle: the
resource hierarchy is polymorphic (Human / Material / Cost), so the
form switches the visible field group based on the chosen type. On
edit the type dropdown is locked, because changing inheritance type
post-creation would orphan subtype-specific columns.

**Requirement 5: data displayed via Views as HTML pages.** The Jinja2
templates in `templates/` are the "View" of MVC. Each one inherits from
`base.html` (which provides the sidebar layout, flash-message stack and
navigation) and fills the `content` block. Templates only know how to
display DTOs — they never see SQLAlchemy entities, never query the
database, and contain no business logic beyond simple presentational
choices like which CSS class to apply for a given status pill. A handful
of custom Jinja2 filters in `presentation/app.py` (`status_class`,
`task_type_label`, `percent`, `money`) keep the templates tidy.

**Requirement 6: data is read using business-logic-layer classes.** This
is the requirement that drove the most architectural decisions. Every
controller depends only on BLL service interfaces — the projects
controller declares its dependencies as `IProjectService` and
`ITaskService`, never on `ProjectRepository` or any DAL class. You can
verify this by grepping the controllers for any `from ...dal` import:
there are none. The controllers receive their service interfaces through
factory functions (`create_projects_blueprint(project_service, task_service)`)
which act as constructor injection across the closure boundary. The
container in `src/di/container.py` is the only place where concrete
service classes are imported and instantiated.

## How the architecture across all three labs holds together

This is one continuous codebase. Lab 1 produced the diagrams; Lab 2
implemented the DAL and BLL with the IoC and DI patterns; Lab 3 added a
presentation layer on top without changing anything below it.

Three observations are worth making in defence:

The **dependency direction is strictly inward**. Templates depend on
controllers, controllers depend on BLL service interfaces, services
depend on DAL interfaces, and the DAL depends on nothing in the
application — just SQLAlchemy. The arrow always points from concrete
to abstract, from outer to inner. The composition root in
`src/di/container.py` is where the abstractions get bound to concrete
implementations, and it is the only file that imports both an interface
and its implementation.

The **services were refactored from holding a UoW instance to receiving
a UoW factory** when Lab 3 came in. In Lab 2 each service got a single
`IUnitOfWork`; that worked because the import was a one-shot CLI
operation. Web requests are concurrent, so each public method now opens
its own `with self._uow_factory() as uow:` block. This guarantees one
fresh database session per request and avoids the entire class of bugs
where two requests share a session and stomp on each other's
transactions.

The **DTOs in `bll/dto.py` decouple the templates from the ORM**. A
template that renders a project detail page sees a `ProjectDetailDto`
with simple Python-typed fields (`int`, `str`, `date`, `List[TaskDto]`)
— it never holds a live SQLAlchemy entity, so it can't accidentally
trigger a lazy-load query while rendering, and it doesn't need an open
session to work with. This separation is the practical reason Lab 3
templates are so simple.

## A few decisions that are worth being able to defend

**Single-table inheritance for Task and Resource.** Both hierarchies
share one table with a discriminator column (`task_type`,
`resource_type`). It keeps the schema readable and the queries simple.
The trade-off — that subclass-specific columns are nullable on the
shared table — is acceptable here because the subtype set is small and
fixed. A Microsoft-Project-style domain doesn't need a Resource subtype
explosion. In the task form the type selector is disabled when editing
an existing task, because changing inheritance type after creation
would leave subclass fields in an inconsistent state.

**Manual DI without a framework.** I picked plain constructor injection
through closures because the lab is grading the *patterns* — IoC and DI
— and a third-party DI library would hide them behind decorators. Every
"service depends on an abstraction" wiring decision is visible in
`container.py` in plain Python.

**Why a separate dashboard.** The lab text says the application
visualises data on user request. A dashboard with aggregate counts
(`StatsService` calls `IUnitOfWork.list_all` on every aggregate and
groups by status/type) shows the data layer is wired up correctly and
gives the user a single entry point that summarises the whole system.

**How the resource form handles polymorphism.** Resources are
single-table-inherited into Human / Material / Cost, each with its own
small set of subtype-specific columns. The form template hides
irrelevant fields based on the chosen type — pick "Material" and you
see Unit + Consumption rate; pick "Cost" and you see Fixed cost. The
type selector is disabled on edit because changing inheritance type
post-creation would orphan subtype-specific columns. The BLL service's
`create_resource` routes to the right SQLAlchemy subclass based on the
type string, and `update_resource` only touches the fields that belong
to the existing subtype.

## Possible questions and how to answer them

*"Where is the Model?"* — Distributed across DAL and BLL. The DAL holds
ORM mappings and persistence; the BLL holds use cases and exposes the
model through `IProjectService`, `ITaskService`, etc. Together they
form what MVC calls the Model.

*"Why is the controller dependent on a service interface and not on a
repository?"* — Lab requirement 6 explicitly says data is read via
business-logic-layer classes. Letting controllers reach into the DAL
directly would skip the BLL and break that rule. Service interfaces
also let me put cross-entity concerns (computing assignment counts for
each project in the list, building a `ProjectDetailDto` that bundles
tasks and assignments together) inside one method instead of duplicating
the logic in every controller.

*"What happens when you delete a project with tasks?"* — SQLAlchemy
cascades the delete. The Project model in Lab 2 declares
`cascade="all, delete-orphan"` on its `tasks`, `calendars` and
`baselines` relationships. Deleting a project removes its tasks, which
in turn cascade into removing assignments and dependencies attached to
those tasks. The browser sees a single `POST /projects/<id>/delete` and
ends up on the empty projects list with a success flash message.

*"How does the resource form handle the three subtypes?"* — The form
template renders three `<fieldset>` blocks, one per subtype, and
toggles their visibility with a tiny `onchange` handler on the type
selector. Submitting the form sends *all* the subtype fields, but the
BLL's `create_resource` only consults the ones that belong to the
chosen type — so picking "Material" but accidentally typing into
the Email field (before switching) doesn't pollute the resulting row.
On edit, the type dropdown is disabled and a hidden `<input>` carries
the original type forward, because changing the polymorphic identity
of an existing row is not a safe operation.

*"How would you add a new entity to the system, say Risk?"* — Add the
ORM model in `dal/models.py`, add an `IRiskRepository` interface and
implementation, expose it on the UoW, write `IRiskService` and
`RiskService` in the BLL, expose them on the container, write the
controller blueprint and the templates, register the blueprint in
`presentation/app.py`. The change touches every layer but each change
is local — no other layer needs to know.

*"Where exactly does inversion of control live in this code?"* — In
the imports. Open `bll/services.py`: it imports from `dal/interfaces.py`
but never from `dal/repositories.py`, `dal/csv_reader.py` or
`dal/unit_of_work.py`. Open any controller in `presentation/controllers/`:
it imports from `bll/interfaces.py` but never from `bll/services.py`.
The only file in the codebase that imports both an interface and its
implementation is `di/container.py`, and that's exactly the
composition-root pattern.
