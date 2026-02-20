"""
Ingestion module API router (placeholder for future endpoints).
"""
from fastapi import APIRouter

router = APIRouter()

# Example endpoint (health check for ingestion)
@router.get("/ingestion/health")
def ingestion_health():
    return {"status": "ok"}
