"""
CSV generator — runnable from the command line.

Produces a single CSV file containing project-planning records of every
type required by the data model: projects, calendars, baselines, three
kinds of resources, summary tasks, regular tasks, milestones, dependencies,
and assignments. The output is guaranteed to contain at least 1000 rows.

Usage:
    python -m scripts.generate_csv
    python -m scripts.generate_csv --output data/project_data.csv --projects 30
    python -m scripts.generate_csv --seed 42
"""
from __future__ import annotations

import argparse
import csv
import random
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List


# --------------------------------------------------------------------------- #
# CSV schema                                                                  #
# --------------------------------------------------------------------------- #
COLUMNS: List[str] = [
    # Identity / classification
    "record_type", "ext_id", "name", "description",
    # Cross-references
    "project_ext_id", "summary_ext_id",
    "predecessor_ext_id", "successor_ext_id",
    "task_ext_id", "resource_ext_id",
    # Time/status
    "start_date", "end_date", "status", "saved_date",
    # Task fields
    "duration", "work", "percent_complete", "priority", "is_critical",
    # Dependency fields
    "dep_type", "lag",
    # Resource (common)
    "code", "cost_per_hour", "max_units",
    # Resource (Human)
    "email", "role", "skills",
    # Resource (Material)
    "unit", "consumption_rate",
    # Resource (Cost)
    "fixed_cost",
    # Assignment fields
    "units", "actual_work", "cost",
    # Calendar fields
    "working_days", "working_hours",
]


# --------------------------------------------------------------------------- #
# Domain vocabularies (just for nicer-looking generated data)                 #
# --------------------------------------------------------------------------- #
PROJECT_NAMES = [
    "ERP Migration", "Mobile Banking App", "E-Commerce Platform",
    "Data Warehouse", "Customer Portal", "Inventory System",
    "Ship Tracking", "HR Onboarding", "Marketing Site Redesign",
    "Payment Gateway", "Analytics Dashboard", "Fleet Management",
    "Telemedicine Platform", "Online Learning System", "Booking Engine",
    "Logistics Network", "Compliance Module", "AI Chatbot",
    "Asset Tracker", "Quality Audit", "Field Service App",
    "Loyalty Program", "Fraud Detection", "Real-Time Trading",
    "Supply Chain", "Subscription Billing", "Workflow Automation",
    "Document Management", "Knowledge Base", "Risk Engine",
]
TASK_VERBS = [
    "Design", "Implement", "Test", "Deploy", "Document", "Review",
    "Refactor", "Optimize", "Integrate", "Migrate", "Configure",
    "Validate", "Audit", "Architect", "Prototype",
]
TASK_NOUNS = [
    "API", "frontend", "backend", "database schema", "auth flow",
    "payment module", "user management", "search index", "caching layer",
    "reporting service", "notification system", "analytics pipeline",
    "CI/CD pipeline", "deployment scripts", "monitoring", "data export",
]
MILESTONE_NAMES = [
    "Kickoff Complete", "Design Approved", "MVP Ready",
    "Beta Released", "GA Launch", "Phase 1 Closed",
    "Stakeholder Sign-off", "Compliance Review Passed",
]
ROLES = [
    "Developer", "Senior Developer", "Tech Lead", "QA Engineer",
    "DevOps Engineer", "Product Manager", "Business Analyst",
    "UX Designer", "Architect", "Database Admin",
]
SKILLS_POOL = [
    "Python", "Java", "JavaScript", "SQL", "AWS", "Docker",
    "React", "TypeScript", "Kubernetes", "Linux",
    "Spring", "Django", "FastAPI", "PostgreSQL", "Redis",
]
MATERIAL_NAMES = [
    "Cloud Compute Hours", "Storage", "License Pool",
    "Build Minutes", "Bandwidth", "Test Devices",
]
MATERIAL_UNITS = ["hours", "license", "server-month", "GB-month", "seat"]
COST_NAMES = ["Travel Budget", "Software License", "External Audit",
              "Training Course", "Consulting Fee"]
DEP_TYPES = ["FS", "SS", "FF", "SF"]
STATUSES = ["NOT_STARTED", "IN_PROGRESS", "COMPLETED", "ON_HOLD"]


def _empty_row() -> Dict[str, str]:
    return {c: "" for c in COLUMNS}


def _date_str(d: date) -> str:
    return d.strftime("%Y-%m-%d")


# --------------------------------------------------------------------------- #
# Generation                                                                  #
# --------------------------------------------------------------------------- #
def generate_rows(num_projects: int = 30) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []

    # ---- Resources (organization-wide) -------------------------------------
    resource_ids: List[str] = []

    for i in range(1, 41):  # 40 humans
        ext = f"RH{i:03d}"
        resource_ids.append(ext)
        rows.append({
            **_empty_row(),
            "record_type": "HUMAN_RESOURCE",
            "ext_id": ext,
            "name": f"Engineer #{i}",
            "code": ext,
            "cost_per_hour": f"{round(random.uniform(20, 120), 2)}",
            "max_units": "1.0",
            "email": f"user{i}@company.com",
            "role": random.choice(ROLES),
            "skills": ";".join(random.sample(SKILLS_POOL, k=random.randint(2, 5))),
        })

    for i in range(1, 16):  # 15 materials
        ext = f"RM{i:03d}"
        resource_ids.append(ext)
        rows.append({
            **_empty_row(),
            "record_type": "MATERIAL_RESOURCE",
            "ext_id": ext,
            "name": f"{random.choice(MATERIAL_NAMES)} #{i}",
            "code": ext,
            "cost_per_hour": f"{round(random.uniform(0.1, 10), 2)}",
            "max_units": f"{round(random.uniform(10, 1000), 1)}",
            "unit": random.choice(MATERIAL_UNITS),
            "consumption_rate": f"{round(random.uniform(0.1, 5), 2)}",
        })

    for i in range(1, 11):  # 10 cost resources
        ext = f"RC{i:03d}"
        resource_ids.append(ext)
        rows.append({
            **_empty_row(),
            "record_type": "COST_RESOURCE",
            "ext_id": ext,
            "name": f"{random.choice(COST_NAMES)} #{i}",
            "code": ext,
            "cost_per_hour": "0",
            "max_units": "1.0",
            "fixed_cost": f"{round(random.uniform(1000, 50000), 2)}",
        })

    # ---- Projects + their dependent records --------------------------------
    for p_idx in range(1, num_projects + 1):
        p_ext = f"PR{p_idx:03d}"
        start = date(2024, 1, 1) + timedelta(days=random.randint(0, 365))
        end = start + timedelta(days=random.randint(60, 400))
        proj_name = f"{random.choice(PROJECT_NAMES)} v{p_idx}"

        # 1. Project
        rows.append({
            **_empty_row(),
            "record_type": "PROJECT",
            "ext_id": p_ext,
            "name": proj_name,
            "description": f"Description of {proj_name}",
            "start_date": _date_str(start),
            "end_date": _date_str(end),
            "status": random.choice(STATUSES),
        })

        # 2. Calendar (one per project)
        rows.append({
            **_empty_row(),
            "record_type": "CALENDAR",
            "ext_id": f"CAL{p_idx:03d}",
            "project_ext_id": p_ext,
            "working_days": "MON;TUE;WED;THU;FRI",
            "working_hours": "09:00-18:00",
        })

        # 3. Baselines (1–3 per project)
        for b in range(random.randint(1, 3)):
            rows.append({
                **_empty_row(),
                "record_type": "BASELINE",
                "ext_id": f"BL{p_idx:03d}_{b+1}",
                "project_ext_id": p_ext,
                "saved_date": _date_str(start + timedelta(days=random.randint(7, 60))),
            })

        # 4. Tasks: 2 summary + 8 regular + 2 milestones = 12 per project
        task_records: List[Dict[str, str]] = []  # (ext_id, is_summary)

        for s in range(2):  # summary tasks first — they may parent regular tasks
            t_ext = f"T{p_idx:03d}_S{s+1}"
            task_records.append({"ext_id": t_ext, "is_summary": True})
            rows.append({
                **_empty_row(),
                "record_type": "SUMMARY_TASK",
                "ext_id": t_ext,
                "project_ext_id": p_ext,
                "name": f"Phase {s+1}",
                "duration": "0",
                "priority": "500",
                "status": "IN_PROGRESS",
            })

        for t in range(8):  # regular tasks
            t_ext = f"T{p_idx:03d}_R{t+1}"
            summary_parent = (
                random.choice([tr for tr in task_records if tr["is_summary"]])["ext_id"]
                if random.random() > 0.3
                else ""
            )
            task_records.append({"ext_id": t_ext, "is_summary": False})
            rows.append({
                **_empty_row(),
                "record_type": "TASK",
                "ext_id": t_ext,
                "project_ext_id": p_ext,
                "summary_ext_id": summary_parent,
                "name": f"{random.choice(TASK_VERBS)} {random.choice(TASK_NOUNS)}",
                "duration": f"{random.randint(1, 30)}",
                "work": f"{random.randint(8, 240)}",
                "start_date": _date_str(start + timedelta(days=random.randint(0, 30))),
                "percent_complete": f"{round(random.uniform(0, 1), 2)}",
                "priority": f"{random.choice([100, 300, 500, 700, 900])}",
                "status": random.choice(STATUSES),
                "is_critical": "true" if random.random() < 0.3 else "false",
            })

        for m in range(2):  # milestones
            t_ext = f"T{p_idx:03d}_M{m+1}"
            task_records.append({"ext_id": t_ext, "is_summary": False})
            rows.append({
                **_empty_row(),
                "record_type": "MILESTONE",
                "ext_id": t_ext,
                "project_ext_id": p_ext,
                "name": random.choice(MILESTONE_NAMES),
                "duration": "0",
                "priority": "500",
                "is_critical": "true",
            })

        # 5. Dependencies — between non-summary tasks
        non_summary = [tr for tr in task_records if not tr["is_summary"]]
        for d in range(random.randint(4, 8)):
            if len(non_summary) < 2:
                break
            pred, succ = random.sample(non_summary, 2)
            rows.append({
                **_empty_row(),
                "record_type": "DEPENDENCY",
                "ext_id": f"D{p_idx:03d}_{d+1}",
                "predecessor_ext_id": pred["ext_id"],
                "successor_ext_id": succ["ext_id"],
                "dep_type": random.choice(DEP_TYPES),
                "lag": f"{random.randint(0, 5)}",
            })

        # 6. Assignments — assign random resources to random tasks
        for a in range(random.randint(8, 14)):
            t = random.choice(non_summary)
            r = random.choice(resource_ids)
            rows.append({
                **_empty_row(),
                "record_type": "ASSIGNMENT",
                "ext_id": f"A{p_idx:03d}_{a+1}",
                "task_ext_id": t["ext_id"],
                "resource_ext_id": r,
                "units": f"{round(random.uniform(0.25, 1.0), 2)}",
                "work": f"{random.randint(8, 80)}",
                "actual_work": f"{random.randint(0, 60)}",
                "cost": f"{round(random.uniform(100, 5000), 2)}",
            })

    # Pad to 1000+ rows if a small `--projects` value was used.
    pad = 1
    while len(rows) < 1000:
        ext = f"RC_PAD_{pad:03d}"
        rows.append({
            **_empty_row(),
            "record_type": "COST_RESOURCE",
            "ext_id": ext,
            "name": f"Padding License #{pad}",
            "code": ext,
            "cost_per_hour": "0",
            "max_units": "1.0",
            "fixed_cost": f"{round(random.uniform(500, 30000), 2)}",
        })
        pad += 1

    return rows


def write_csv(output: Path, rows: List[Dict[str, str]]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate a CSV file (1000+ rows) of project-planning data."
    )
    parser.add_argument("--output", type=Path, default=Path("data/project_data.csv"),
                        help="Output CSV file path.")
    parser.add_argument("--projects", type=int, default=30,
                        help="Number of projects to generate.")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducible output.")
    args = parser.parse_args(argv)

    random.seed(args.seed)
    rows = generate_rows(args.projects)
    write_csv(args.output, rows)

    by_type: Dict[str, int] = {}
    for r in rows:
        by_type[r["record_type"]] = by_type.get(r["record_type"], 0) + 1

    print(f"Wrote {len(rows)} rows to {args.output}")
    for t, n in sorted(by_type.items()):
        print(f"  {t:20s} {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
