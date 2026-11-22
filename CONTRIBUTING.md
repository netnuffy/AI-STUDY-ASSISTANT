# Contributing to AI Study Assistant

Thanks for your interest in contributing! This guide covers how to get set up
and how to submit changes.

## Getting started

1. Fork the repository and clone your fork.
2. Follow the [installation guide](README.md#installation) to get the backend
   and frontend running locally.
3. Create a branch for your change:

```bash
git checkout -b feature/short-description
```

Branch names: `feature/...` for new features, `fix/...` for bug fixes,
`docs/...` for documentation-only changes.

## Development

- **Backend** — Python 3.12, FastAPI, SQLAlchemy. Install dev dependencies
  with `pip install -r backend/requirements-dev.txt`.
- **Frontend** — Next.js 14, TypeScript, Tailwind CSS, shadcn/ui.
  Install with `npm install` in `frontend/`.

### Code style

- Python: follow the existing style — type hints on public functions, small
  focused modules, errors raised as the `AppException` subclasses in
  `backend/core/exceptions.py` (never bare `HTTPException` in services).
- TypeScript: follow the existing patterns — server state via `apiFetch`
  in `frontend/src/lib/api.ts`, shared UI from `src/components/ui/`.
- Keep functions small and name things after what they do, not how they do it.

### Database changes

Never edit an applied Alembic migration. Add a new one:

```bash
cd backend
alembic revision -m "describe the change"
# fill in upgrade() and downgrade(), then:
alembic upgrade head
alembic downgrade -1 && alembic upgrade head   # verify both directions
```

## Tests

Backend changes need tests. The suite uses pytest with an in-memory SQLite
database and mocked Gemini calls (no API key needed to run it):

```bash
cd backend
python -m pytest tests/ -q
```

New endpoints need API tests; new services need unit tests. Run the full
suite before opening a PR — it should be green (130 tests at last count).

Frontend changes need a clean production build (this runs the type-check
and the linter):

```bash
cd frontend
npm run build
```

## Commits

Write short, imperative commit messages, one logical change per commit:

```
Add recent-attempts endpoint for the dashboard
Fix quiz grading for short answers with trailing spaces
```

## Pull requests

1. Push your branch and open a PR against `main`.
2. Describe what the change does and why. Link any related issue.
3. Make sure the backend tests and `npm run build` pass.
4. If your change adds an endpoint or changes a response shape, update
   `docs/API.md` in the same PR.
5. Screenshots are welcome for UI changes — see
   `scripts/screenshot_tour.py` for how the README screenshots are made.

## Reporting issues

Open an issue with:

- What you expected to happen, and what happened instead.
- Steps to reproduce (or the exact request, for API bugs).
- The backend log output if the API returned a 500.

## Questions?

Open an issue with the `question` label — maintainers and other contributors
will help out.
