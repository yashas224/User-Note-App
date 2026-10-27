# Technical Specification: Secure Note-Taking Application

**Version:** 1.0
**Date:** October 26, 2026

---

## 1. Project Overview

Build a secure note-taking application that allows registered users to create, edit, delete, restore, and share notes through read-only links.

### Technology Stack

| Component        | Technology                    |
| ---------------- | ----------------------------- |
| Frontend         | Streamlit                     |
| Backend          | FastAPI                       |
| Database         | SQLite                        |
| ORM              | SQLAlchemy 2.x                |
| Migrations       | Alembic                       |
| Validation       | Pydantic                      |
| Password hashing | Argon2id using `pwdlib`       |
| Authentication   | JWT access tokens             |
| Testing          | Pytest and FastAPI TestClient |

---

## 2. Functional Requirements

### 2.1 User Registration

- Users can register with a unique username and password.
- Usernames must be unique, with case-insensitive uniqueness enforced.
- Passwords must be hashed before storage.
- Plaintext passwords must never be stored.
- Password validation must enforce a configurable minimum length, recommended at 12 characters.
- Duplicate usernames must be rejected.

### 2.2 User Authentication

- Users can sign in using their username and password.
- Successful authentication returns a short-lived JWT access token.
- Invalid credentials return a generic authentication error.
- Protected endpoints require valid authentication.
- Users can log out, clearing their local authentication state.
- Every private operation must enforce authorization on the backend.

### 2.3 Note Management

Authenticated users can:

- Create a note.
- View their active notes.
- View an individual note.
- Edit an existing note.
- Soft-delete a note.
- View previously deleted notes.
- Restore a deleted note.
- Search and filter notes by title, status, and importance.
- Sort notes by creation date, modification date, title, or importance.

### 2.4 Note Fields

| Field        | Type               | Required | Description            |
| ------------ | ------------------ | -------- | ---------------------- |
| `id`         | Integer            | Yes      | Unique note identifier |
| `owner_id`   | Integer            | Yes      | ID of the owning user  |
| `title`      | String, max 200    | Yes      | Note title             |
| `status`     | String/Enum        | Yes      | Workflow status        |
| `body`       | Text               | No       | Note content           |
| `importance` | String/Enum        | Yes      | Priority level         |
| `created_at` | Datetime           | Yes      | Creation timestamp     |
| `updated_at` | Datetime           | Yes      | Last modification timestamp |
| `deleted_at` | Datetime, nullable | No       | Soft-deletion timestamp |

**Default values:**

- Status: `draft`
- Importance: `normal`
- Body: empty string
- Deleted timestamp: `NULL`

**Supported statuses:**

- `draft`
- `in_progress`
- `completed`
- `archived`

**Supported importance levels:**

- `low`
- `normal`
- `high`
- `critical`

### 2.5 Delete and Restore

- Deleting a note sets `deleted_at` instead of removing the database record.
- Deleted notes must not appear in the active notes list.
- Deleted notes must appear in the Trash view.
- The owner can restore a deleted note.
- Permanent deletion is optional and must be a separate operation.

### 2.6 Read-Only Note Sharing

- A note owner can generate a unique sharing URL.
- A visitor can view the note without signing in.
- Shared notes are strictly read-only.
- Sharing tokens must be cryptographically random and unpredictable.
- Store a hash of each sharing token rather than the raw token.
- Owners can revoke sharing links.
- Links may have an expiration timestamp.
- Deleted notes must not be accessible through shared links.
- Invalid, revoked, or expired links must not reveal note contents.
- Public responses must not expose internal database fields or owner information.

> **Note:** Anyone possessing an active sharing link can view the shared note. The UI should warn users before creating a public link.

---

## 3. System Architecture

```text
Streamlit Frontend
       |
       | HTTP/HTTPS + JSON
       | Bearer Access Token
       v
FastAPI Backend
       |
       +-- Authentication Service
       +-- User Service
       +-- Note Service
       +-- Sharing Service
       +-- Validation and Authorization
       |
       | SQLAlchemy ORM
       v
SQLite Database
       |
       +-- users
       +-- notes
       +-- note_shares
```

The Streamlit frontend must communicate with FastAPI through REST endpoints. It must never access SQLite directly.

---

## 4. Database Schema

### 4.1 Users Table

Table name: `users`

| Column          | Type         | Constraints               |
| --------------- | ------------ | ------------------------- |
| `id`            | INTEGER      | Primary key               |
| `username`      | VARCHAR(50)  | Unique, not null          |
| `password_hash` | VARCHAR(255) | Not null                  |
| `created_at`    | DATETIME     | Not null                  |
| `is_active`     | BOOLEAN      | Not null, default `true`  |

Enforce case-insensitive username uniqueness at the database level.

### 4.2 Notes Table

Table name: `notes`

| Column       | Type         | Constraints             |
| ------------ | ------------ | ----------------------- |
| `id`         | INTEGER      | Primary key             |
| `owner_id`   | INTEGER      | Foreign key to `users.id` |
| `title`      | VARCHAR(200) | Not null                |
| `status`     | VARCHAR(20)  | Not null                |
| `body`       | TEXT         | Not null                |
| `importance` | VARCHAR(20)  | Not null                |
| `created_at` | DATETIME     | Not null                |
| `updated_at` | DATETIME     | Not null                |
| `deleted_at` | DATETIME     | Nullable                |

**Relationships:**

- One user owns multiple notes.
- Each note belongs to one user.
- Deleting a user must not accidentally orphan notes; define an explicit account-deletion policy.

### 4.3 Note Shares Table

Table name: `note_shares`

| Column       | Type        | Constraints               |
| ------------ | ----------- | ------------------------- |
| `id`         | INTEGER     | Primary key               |
| `note_id`    | INTEGER     | Foreign key to `notes.id` |
| `token_hash` | VARCHAR(64) | Unique, not null          |
| `created_at` | DATETIME    | Not null                  |
| `expires_at` | DATETIME    | Nullable                  |
| `revoked_at` | DATETIME    | Nullable                  |

A share is valid only when it has not been revoked, has not expired, and references a note that has not been deleted.

### 4.4 Database Indexes

Create indexes for:

- `users.username`
- `notes.owner_id`
- `notes.owner_id, notes.deleted_at`
- `notes.owner_id, notes.status`
- `notes.owner_id, notes.importance`
- `note_shares.token_hash`
- `note_shares.note_id`

Enable SQLite foreign key enforcement and use transactions for multi-step operations.

---

## 5. Authentication and Security

### Passwords

- Use Argon2id with a maintained password-hashing library.
- Verify passwords using the library's verification function.
- Never store plaintext passwords or reversible password encryption.
- Never expose password hashes through API responses or logs.

### JWT

- Use short-lived access tokens, initially 30 minutes.
- Include the user ID in the `sub` claim.
- Validate the signature and expiration.
- Use an explicit signing algorithm allowlist.
- Store the signing secret in environment configuration.
- Never put access tokens in URLs.

### Authorization

- All private note operations must constrain database queries by both note ID and authenticated owner ID.
- The backend must not trust an `owner_id` supplied by the frontend.

### Additional Security Requirements

- Use HTTPS in production.
- Apply rate limiting to authentication endpoints.
- Validate all requests with Pydantic.
- Use parameterized database operations through SQLAlchemy.
- Return generic errors for invalid credentials and inaccessible shared links.
- Avoid exposing stack traces or internal database errors.
- Keep secrets out of source control.
- Configure appropriate request-size limits.

---

## 6. REST API Specification

**Base URL:** `/api/v1`

### 6.1 Authentication

| Method | Endpoint         | Description       | Access        |
| ------ | ---------------- | ----------------- | ------------- |
| POST   | `/auth/register` | Register user     | Public        |
| POST   | `/auth/login`    | Authenticate user | Public        |
| GET    | `/auth/me`       | Get current user  | Authenticated |

**Registration request:**

```json
{
  "username": "alex",
  "password": "a-long-example-password"
}
```

**Login request:**

```json
{
  "username": "alex",
  "password": "a-long-example-password"
}
```

**Login response:**

```json
{
  "access_token": "<signed-access-token>",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### 6.2 Notes

| Method | Endpoint                   | Description            |
| ------ | -------------------------- | ---------------------- |
| POST   | `/notes`                   | Create a note          |
| GET    | `/notes`                   | List active notes      |
| GET    | `/notes/{note_id}`         | Get a note             |
| PATCH  | `/notes/{note_id}`         | Update selected fields |
| DELETE | `/notes/{note_id}`         | Soft-delete a note     |
| GET    | `/notes/trash`             | List deleted notes     |
| POST   | `/notes/{note_id}/restore` | Restore a note         |

**Create-note request:**

```json
{
  "title": "Project planning",
  "status": "draft",
  "body": "List project milestones.",
  "importance": "high"
}
```

**List endpoint query parameters:**

- `status`
- `importance`
- `search`
- `sort_by`
- `order`
- `limit`
- `offset`

**Example:**

```http
GET /api/v1/notes?status=draft&importance=high&limit=20&offset=0
```

Update requests must support partial updates. The server must automatically update `updated_at`.

### 6.3 Sharing

| Method | Endpoint                             | Description          | Access |
| ------ | ------------------------------------ | -------------------- | ------ |
| POST   | `/notes/{note_id}/shares`            | Create sharing link  | Owner  |
| GET    | `/notes/{note_id}/shares`            | List sharing links   | Owner  |
| DELETE | `/notes/{note_id}/shares/{share_id}` | Revoke sharing link  | Owner  |
| GET    | `/shared/{token}`                    | Read shared note     | Public |

**Create-share request:**

```json
{
  "expires_in_days": 7
}
```

**Create-share response:**

```json
{
  "share_url": "https://example.com/shared/<random-token>",
  "expires_at": "2026-11-02T12:00:00Z"
}
```

The raw token must be returned only when creating the link. Construct the URL using a configured public base URL.

Public shared-note responses must include only approved fields such as title, body, status, importance, and update timestamp.

### 6.4 HTTP Status Codes

| Code | Meaning                                  |
| ---- | ---------------------------------------- |
| 200  | Successful read or update                |
| 201  | Resource created                         |
| 204  | Successful operation with no response body |
| 400  | Invalid operation                        |
| 401  | Missing or invalid authentication        |
| 403  | Authenticated user lacks permission      |
| 404  | Resource not found or intentionally concealed |
| 409  | Username conflict                        |
| 422  | Request validation error                 |
| 429  | Rate limit exceeded                      |
| 500  | Unexpected server error                  |

---

## 7. Streamlit UI Specification

### 7.1 Initial Authentication Page

Unauthenticated users must see:

- Sign In
- Sign Up

**Sign-in form:**

- Username
- Password
- Sign In button

**Sign-up form:**

- Username
- Password
- Confirm Password
- Create Account button

### 7.2 Dashboard

After login, display:

- All Notes
- Create Note
- Trash
- Manage Sharing
- Logout

The dashboard should support search, filtering, sorting, and note creation.

Each note should display its title, status, importance, last-updated timestamp, and relevant actions.

### 7.3 Note Editor

**Fields:**

| Field      | Widget           |
| ---------- | ---------------- |
| Title      | `st.text_input`  |
| Status     | `st.selectbox`   |
| Body       | `st.text_area`   |
| Importance | `st.selectbox`   |

**Actions:**

- Save
- Cancel

Validate the title and other fields before submission.

### 7.4 Trash

Display deleted notes with a Restore action.

### 7.5 Sharing

Allow the owner to create, copy, inspect, and revoke sharing links.

Public sharing pages must work without authentication and must never expose editing controls or management operations.

### 7.6 Session Management

- Store the access token in `st.session_state`.
- Clear authentication state on logout.
- Use Streamlit query parameters or suitable routing to identify shared-note URLs.
- Handle the public sharing route before enforcing the login gate.
- Do not rely on frontend controls for authorization.

---

## 8. Recommended Project Structure

```text
notes_app/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── dependencies.py
│   │   ├── db/
│   │   │   ├── session.py
│   │   │   └── base.py
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── note.py
│   │   │   └── note_share.py
│   │   ├── schemas/
│   │   │   ├── auth.py
│   │   │   ├── note.py
│   │   │   └── sharing.py
│   │   ├── api/v1/
│   │   │   ├── auth.py
│   │   │   ├── notes.py
│   │   │   └── sharing.py
│   │   ├── services/
│   │   │   ├── auth_service.py
│   │   │   ├── note_service.py
│   │   │   └── sharing_service.py
│   │   └── tests/
│   ├── alembic/
│   ├── alembic.ini
│   └── requirements.txt
├── frontend/
│   ├── app.py
│   ├── api_client.py
│   ├── auth_ui.py
│   ├── notes_ui.py
│   ├── trash_ui.py
│   └── sharing_ui.py
├── .env.example
├── .gitignore
├── README.md
└── pyproject.toml
```

---

## 9. Environment Configuration

Example `.env.example`:

```dotenv
APP_ENV=development
DATABASE_URL=sqlite:///./notes.db
JWT_SECRET_KEY=replace-with-a-secure-random-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
PUBLIC_BASE_URL=http://localhost:8501
API_BASE_URL=http://localhost:8000/api/v1
```

Never commit the actual `.env` file. Validate required settings at application startup.

---

## 10. Implementation Phases

### Phase 1: Setup

- Create the project structure.
- Configure dependencies and environment variables.
- Set up SQLite and SQLAlchemy.
- Configure Alembic migrations.

### Phase 2: Authentication

- Implement the User model.
- Implement registration and login.
- Implement password hashing and JWT verification.
- Test authentication and account uniqueness.

### Phase 3: Note CRUD

- Implement the Note model.
- Implement create, list, retrieve, update, and soft-delete operations.
- Implement Trash and restore.
- Add ownership checks and input validation.

### Phase 4: Streamlit UI

- Build authentication screens.
- Build the dashboard and note editor.
- Add search, filters, and sorting.
- Connect all operations to FastAPI.

### Phase 5: Sharing

- Implement the NoteShare model.
- Generate and hash random tokens.
- Implement share creation, listing, revocation, and public retrieval.
- Add expiration handling and read-only views.

### Phase 6: Testing and Deployment

- Write automated tests.
- Verify ownership restrictions.
- Test link revocation and expiration.
- Configure HTTPS, logging, rate limiting, backups, and deployment.

---

## 11. Testing Requirements

### Authentication

- Registration succeeds with valid input.
- Duplicate usernames are rejected.
- Password hashes do not equal plaintext passwords.
- Invalid credentials are rejected.
- Expired tokens are rejected.
- Disabled users cannot authenticate.

### Notes

- Users can create, edit, delete, and restore their own notes.
- Deleted notes do not appear in the active list.
- Another user cannot read or modify private notes.
- Invalid status and importance values are rejected.
- Filters return the correct results.

### Sharing

- Valid links return shared note content without login.
- Public responses omit private internal fields.
- Shared notes cannot be modified anonymously.
- Revoked and expired links fail.
- Deleted notes cannot be viewed through old links.
- Users cannot revoke another user's sharing links.

### Frontend

- Unauthenticated users see the authentication screen.
- Login and logout work correctly.
- Forms show validation errors.
- Note changes are reflected in the dashboard.
- Public share links work without login.

---

## 12. Deployment Requirements

**Development URLs:**

| Service           | URL                          |
| ----------------- | ---------------------------- |
| FastAPI           | http://localhost:8000        |
| Streamlit         | http://localhost:8501        |
| API documentation | http://localhost:8000/docs   |

**Production requirements:**

- Serve the application over HTTPS.
- Store SQLite on persistent storage.
- Configure automated backups and recovery procedures.
- Keep dependencies updated.
- Store secrets outside source control.
- Configure the public sharing URL to resolve to the Streamlit shared-note view.
- Consider PostgreSQL if multiple instances or high write concurrency are required.

---

## 13. Definition of Done

- [ ] Users can register and sign in.
- [ ] Passwords are securely hashed.
- [ ] Users can create, edit, view, and soft-delete notes.
- [ ] Users can view and restore deleted notes.
- [ ] All four required note fields are supported.
- [ ] Private notes are protected by backend ownership checks.
- [ ] Users can create and revoke read-only sharing links.
- [ ] Shared notes can be viewed without login.
- [ ] Expired, revoked, and deleted-note links are inaccessible.
- [ ] Streamlit uses FastAPI for all database operations.
- [ ] Automated tests cover authentication, note operations, ownership, and sharing.
- [ ] Deployment secrets and backup procedures are configured.

---

## 14. Future Enhancements

Potential future features include:

- Tags
- Markdown editing
- Full-text search
- Note version history
- Password-protected sharing
- Account recovery
- Two-factor authentication
- Export to PDF or Markdown
- Docker deployment
- PostgreSQL support

---

## Final Recommendation

Implement authentication first, followed by note CRUD and soft deletion, then the Streamlit interface, and finally secure read-only sharing.

Keep authorization in FastAPI, use SQLAlchemy for database access, Argon2id for password hashing, and hashed random tokens for sharing links. This architecture provides a maintainable MVP and a clear path for future enhancements.
