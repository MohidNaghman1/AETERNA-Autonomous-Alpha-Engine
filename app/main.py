# Application entry point

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from . import settings

from app.shared.presentation.health import router as health_router
from app.modules.identity.presentation.auth import router as auth_router


app = FastAPI(
	title="AETERNA Autonomous Alpha Engine",
	description="API for AETERNA Autonomous Alpha Engine",
	version="0.1.0",
)

# CORS configuration
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],  # Change to specific origins in production
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router, prefix="/auth", tags=["auth"])

@app.get("/")
def read_root():
	return {"message": "Welcome to AETERNA Autonomous Alpha Engine API"}
