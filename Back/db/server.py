from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .auth.auth import router as auth_router

app = FastAPI(title="Stock Analysis System")

app.include_router(auth_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Server is running"}

@app.get("/health")
def health():
    return {"status": "ok", "service": "auth-server"}

if __name__ == "__main__":
    uvicorn.run("db.server:app", host="0.0.0.0", port=8000, reload=True)