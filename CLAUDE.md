# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Keep your replies short and consice . No unecessary long codes and information.

Whenever working with any third-party library or something similar, you MUST look up the official documentation to ensure that you're working with up-to-date information.
Use the DocsExplorer subagent for efficient documentation lookup.

## Project state

This is an early-stage `uv` project (Python 3.13, `uv_build` backend, package at `src/user_note/`). The only code so far is a placeholder `main()` in `src/user_note/__init__.py`, exposed as the `user-note` console script. **`SPEC.md` is the source of truth** for what is being built: a secure note-taking app with a FastAPI backend, a Streamlit frontend and SQLite. Read the relevant SPEC section before implementing a feature.

SPEC.md §8 suggests a `notes_app/backend` + `notes_app/frontend` layout, but the repo uses the `src/user_note/` layout. Ask before restructuring.

Many dependencies required by the SPEC aren't installed yet (Streamlit, SQLAlchemy 2.x, Alembic, `pwdlib[argon2]`, a JWT library, pytest). Add them with `uv add` (`uv add --dev` for test tools) rather than editing `pyproject.toml` by hand. `black` and `isort` are currently listed as runtime dependencies.

## Commands

```bash
uv sync                      # install deps into .venv
uv run user-note             # run the console entry point
uv run black . && uv run isort --profile black .   # format
uv run pytest                # tests (after pytest is added)
uv run pytest path/to/test_file.py::test_name      # single test
```

Dev servers once they exist (ports from SPEC §9/§12): FastAPI on `http://localhost:8000` (`uv run fastapi dev <app module path>`, docs at `/docs`) and Streamlit on `http://localhost:8501`.

## Architecture (from SPEC.md)

- **Layering:** Streamlit → REST/JSON with Bearer JWT → FastAPI (`/api/v1`) → services → SQLAlchemy → SQLite. The frontend must never touch the database directly; all authorization lives in the backend.
- **Tables:** `users`, `notes`, `note_shares`. Usernames are unique case-insensitively, enforced in the DB. Turn on SQLite foreign keys (`PRAGMA foreign_keys=ON`) and manage the schema with Alembic migrations.
- **Ownership:** every private note query filters by both `note_id` and the authenticated user's ID taken from the JWT `sub`. Never trust a client-supplied `owner_id`. When a note is inaccessible, return 404 to hide whether it exists.
- **Soft delete:** DELETE sets `deleted_at`. Active lists exclude deleted notes, `/notes/trash` shows them, and `POST /notes/{id}/restore` clears `deleted_at`. Permanent deletion, if added, is a separate operation.
- **Sharing:** tokens are cryptographically random. Store only their hash (`token_hash`, 64 chars, e.g. SHA-256 hex) and return the raw token once, at creation, inside a URL built from `PUBLIC_BASE_URL`. A share is valid only if it isn't revoked, isn't expired and its note isn't deleted. `GET /shared/{token}` is public and returns only title, body, status, importance and updated_at. Invalid links get a generic error that reveals nothing.
- **Enums:** status is one of `draft | in_progress | completed | archived` (default `draft`). Importance is one of `low | normal | high | critical` (default `normal`). Invalid values get a 422.
- **Auth:** passwords are hashed with Argon2id via `pwdlib`, with a configurable minimum length of 12. JWTs last 30 minutes, the signing algorithm comes from an explicit allowlist and the secret comes from env. Tokens never go in URLs. Auth endpoints are rate-limited.
- **Streamlit:** the token is kept in `st.session_state`. The public shared-note route, identified by query params, must be handled *before* the login gate.
- **Config:** env vars are listed in SPEC §9 (`DATABASE_URL`, `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `PUBLIC_BASE_URL`, `API_BASE_URL`). They are loaded from `.env`, which must never be committed (`python-dotenv` is installed as `dotenv`), and validated at startup.

Build in the order given in SPEC §10: setup → auth → note CRUD and soft delete → Streamlit UI → sharing → tests and deployment. SPEC §11 lists the required test cases.
