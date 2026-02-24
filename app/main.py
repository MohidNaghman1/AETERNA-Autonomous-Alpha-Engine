# Application entry point


from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from . import settings



from app.shared.presentation.health import router as health_router
from app.modules.identity.presentation.auth import router as auth_router
from app.modules.ingestion.presentation.api import router as ingestion_router
from app.modules.alerting.presentation.alerts import router as alerts_router



app = FastAPI(
	title="AETERNA Autonomous Alpha Engine",
	description="API for AETERNA Autonomous Alpha Engine",
	version="0.1.0",
)

# Prometheus metrics (basic example)
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

# Example metric: count API requests
REQUEST_COUNT = Counter('aeterna_api_requests_total', 'Total API Requests', ['endpoint'])

@app.middleware("http")
async def prometheus_middleware(request, call_next):
	response = await call_next(request)
	REQUEST_COUNT.labels(endpoint=request.url.path).inc()
	return response

@app.get("/metrics")
def metrics():
	return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

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
app.include_router(ingestion_router, prefix="/ingestion", tags=["ingestion"])
app.include_router(alerts_router)

@app.get("/")
def read_root():
	return {"message": "Welcome to AETERNA Autonomous Alpha Engine API"}
