from fastapi import FastAPI

from user_note.backend.api.v1 import auth, notes, shares

app = FastAPI(title="User Notes")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(notes.router, prefix="/api/v1")
app.include_router(shares.router, prefix="/api/v1")
