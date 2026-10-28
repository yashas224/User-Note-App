# User Note

A secure note-taking app: FastAPI backend, Streamlit frontend, SQLite storage.

## Features

- **Accounts** – register/login with Argon2id-hashed passwords (min 5 chars), case-insensitive unique usernames, 30-min JWTs, rate-limited auth endpoints.
- **Notes** – create, view, edit and delete your own notes. Each note has a title, body, status (`draft`, `in_progress`, `completed`, `archived`) and importance (`low`, `normal`, `high`, `critical`).
- **Filter, search & sort** – filter by status/importance, search text, sort by field and order, paginate.
- **Trash & restore** – deleting is a soft delete; deleted notes move to Trash and can be restored.
- **Sharing** – generate public, read-only share links (optional expiry), list and revoke them. Only token hashes are stored; invalid links reveal nothing.
- **Privacy** – every query is scoped to the logged-in user; inaccessible notes return 404.

## Quick start

```bash
uv sync
# create .env with the vars below
./run.sh                # runs migrations, API on :8000, UI on :8501
```

Env vars: `DATABASE_URL`, `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `PUBLIC_BASE_URL`, `API_BASE_URL`.

API docs: http://localhost:8000/docs · UI: http://localhost:8501

## API (`/api/v1`)

| Area | Endpoints |
|------|-----------|
| Auth | `POST /auth/register`, `POST /auth/login`, `GET /auth/me` |
| Notes | `GET/POST /notes`, `GET/PATCH/DELETE /notes/{id}`, `GET /notes/trash`, `POST /notes/{id}/restore` |
| Shares | `GET/POST /notes/{id}/shares`, `DELETE /notes/{id}/shares/{share_id}`, `GET /shared/{token}` (public) |

## Tests

```bash
uv run pytest
```
