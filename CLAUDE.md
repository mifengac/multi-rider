# CLAUDE.md

This file gives Claude Code the minimum project context it needs to work safely in this repository.

## Project Summary

This is a Flask-based internal service for image/video detection and related police-work modules. The main areas are detection, face, dispatch, and training. Most business logic lives under `modules/`, shared infrastructure lives under `shared/`, and the UI templates/static assets live under `templates/` and `static/`.

## Project Background

- This project is built for the public security criminal investigation department.
- It is primarily designed for intranet deployment.
- Assume offline or restricted-network operation by default unless the user explicitly says otherwise.

## Environment

- Python runtime: `uv` managed Python 3.12 virtual environment.
- Use the project-specific virtual environment for running tests and the app.
- If the environment is not set up yet, follow the instructions in `README.md` and the repository setup docs before making larger changes.

## How to Work in This Repo

- Read `README.md` first for setup, runtime, and deployment context.
- Prefer small, local changes over broad refactors unless the user explicitly asks for a larger redesign.
- After changing templates or Tailwind classes, rebuild CSS with `npm run build:css`.
- Keep the project compatible with the current offline/internal deployment assumptions.
- Do not assume external network access is available.

## When You Need Deeper Reference Material

Do not copy long domain rules into this file. Instead, read the focused reference docs below when the task touches those topics.

### Business Database Reference

Use this when working on SQL, reporting, analytics, or any code that touches business data tables.

- Reference: `docs/business/business_database.md`
- Covers: database engine choice, SQL compatibility rules, table names, and important usage notes
- Read it before writing new SQL against business tables or unfamiliar fields

### Region and Code Mapping Reference

Use this when working on region grouping, organization codes, police-station grouping, or region-name joins.

- Reference: `docs/region/region_grouping.md`
- Covers: 12-character org codes, county/district vs police-station levels, prefix rules, and dictionary joins
- Read it before adding SQL or code that groups by region or parses organization codes

## Key Rules to Remember

- For business SQL, keep Kingbase V8 compatibility in mind.
- Prefer explicit schema-qualified table names.
- Avoid hardcoding region mappings if the dictionary table can be used instead.
- Be explicit about grouping level: county/district and police-station are different and should not be mixed silently.
- If a task needs more detail than this summary, go to the reference doc instead of expanding CLAUDE.md.

## Common Commands

- Run tests: `pytest`
- Build frontend CSS: `npm run build:css`
- Start the app: `python app.py`
