"""Health check endpoint for service status monitoring.

Provides a simple health check endpoint for load balancers and monitoring systems.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Service health check endpoint.

    Returns:
        dict: Status object indicating service is running
    """
    return {"status": "ok"}
