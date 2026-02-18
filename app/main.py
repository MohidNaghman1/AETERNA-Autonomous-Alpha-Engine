# Application entry point
from fastapi import FastAPI
from . import settings
from app.shared.presentation.health import router as health_router

app = FastAPI(
	title="AETERNA Autonomous Alpha Engine",
	description="API for AETERNA Autonomous Alpha Engine",
	version="0.1.0",
)
app.include_router(health_router)

@app.get("/")
def read_root():
	return {"message": "Welcome to AETERNA Autonomous Alpha Engine API"}
