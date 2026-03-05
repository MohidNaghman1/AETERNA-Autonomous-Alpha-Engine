from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import pika
import redis
import os
import threading
import time
from dotenv import load_dotenv
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import socketio
from socketio import ASGIApp
from apscheduler.schedulers.background import BackgroundScheduler

from app.shared.utils.auth_utils import decode_token
from app.modules.alerting.infrastructure.alert_consumer import AlertConsumer
from app.modules.identity.infrastructure.models import User, UserPreference
from app.config.db import AsyncSessionLocal as SessionLocal
from app.shared.presentation.health import router as health_router
from app.modules.identity.presentation.auth import router as auth_router
from app.modules.ingestion.presentation.api import router as ingestion_router
from app.modules.alerting.presentation.alerts import router as alerts_router
from app.modules.admin.presentation.dashboard import router as admin_dashboard_router
from app.modules.admin.presentation.user_management import router as admin_user_router
from app.modules.admin.presentation.admin_protected import (
    router as admin_protected_router,
)
from app.modules.admin.presentation.security import RateLimitMiddleware
from app.modules.ingestion.application.price_collector import run_collector as price_run
from app.modules.ingestion.application.rss_collector import run_collector                    
from app.modules.ingestion.application.consumer import run_consumer

load_dotenv()


app = FastAPI(
    title="AETERNA Autonomous Alpha Engine",
    description="AI-powered cryptocurrency alert and analysis engine with multi-channel delivery",
    version="0.1.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
sio_app = ASGIApp(sio, other_asgi_app=app)

REQUEST_COUNT = Counter(
    "aeterna_api_requests_total", "Total API Requests", ["endpoint"]
)


@app.middleware("http")
async def prometheus_middleware(request, call_next):
    response = await call_next(request)
    REQUEST_COUNT.labels(endpoint=request.url.path).inc()
    return response


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RateLimitMiddleware)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(ingestion_router, prefix="/ingestion", tags=["ingestion"])
app.include_router(alerts_router)
app.include_router(admin_dashboard_router)
app.include_router(admin_user_router)
app.include_router(admin_protected_router)


@app.get("/")
def read_root():
    return {"message": "Welcome to AETERNA Autonomous Alpha Engine API"}


# --- DIAGNOSTIC ENDPOINTS ---
@app.get("/health/system")
def system_health():
    """Comprehensive system health check."""
    diagnostics = {}

    # Check RabbitMQ
    rabbitmq_host = os.getenv("RABBITMQ_HOST", "localhost")
    rabbitmq_user = os.getenv("RABBITMQ_USER", "guest")
    rabbitmq_password = os.getenv("RABBITMQ_PASSWORD", "guest")
    try:
        credentials = pika.PlainCredentials(rabbitmq_user, rabbitmq_password)
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=rabbitmq_host, credentials=credentials)
        )
        connection.close()
        diagnostics["rabbitmq"] = "✅ Connected"
    except Exception as e:
        diagnostics["rabbitmq"] = f"❌ Error: {str(e)}"

    # Check Redis
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = os.getenv("REDIS_PORT", 6379)
    try:
        r = redis.Redis(host=redis_host, port=int(redis_port), decode_responses=True)
        r.ping()
        diagnostics["redis"] = "✅ Connected"
    except Exception as e:
        diagnostics["redis"] = f"❌ Error: {str(e)}"

    # Check PostgreSQL
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        diagnostics["postgresql"] = "✅ Connected"
    except Exception as e:
        diagnostics["postgresql"] = f"❌ Error: {str(e)}"

    return diagnostics


alert_consumer = None


@sio.event
async def connect(sid, environ, auth):
    """Handle WebSocket connection with JWT authentication."""
    token = None
    if auth and isinstance(auth, dict):
        token = auth.get("token")
    if not token:
        return False
    try:
        payload = decode_token(token)
        user_id = str(payload.get("sub") or payload.get("user_id") or payload.get("id"))
        if not user_id:
            return False
        await sio.save_session(sid, {"user_id": user_id})
        await sio.enter_room(sid, user_id)
        return True
    except Exception:
        return False


@sio.event
async def disconnect(sid):
    """Handle WebSocket disconnection."""
    session = await sio.get_session(sid)
    user_id = session.get("user_id") if session else None
    if user_id:
        await sio.leave_room(sid, user_id)


@sio.event
async def ping(sid):
    """Heartbeat: respond to ping with pong."""
    await sio.emit("pong", room=sid)


def get_user_prefs(user_id):
    try:
        db = SessionLocal()
        # Try UserPreference table first
        pref = (
            db.query(UserPreference)
            .filter(UserPreference.user_id == int(user_id))
            .first()
        )
        if pref and pref.preferences:
            return pref.preferences
        # Fallback: check User.preferences
        user = db.query(User).filter(User.id == int(user_id)).first()
        if user and user.preferences:
            return user.preferences
        return None
    except Exception as e:
        print(f"[get_user_prefs] DB error: {e}")
        return None
    finally:
        try:
            db.close()
        except Exception:
            pass


# --- Startup: Launch alert consumer thread ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global alert_consumer
    
    # Start Alert Consumer
    if not alert_consumer:
        alert_consumer = AlertConsumer(sio, user_prefs_func=get_user_prefs)
        alert_consumer.start()
        print("[STARTUP] ✅ Alert consumer started")
    
    # Start RabbitMQ Event Consumer (background thread)
    def start_event_consumer():
        print("[STARTUP] Starting RabbitMQ event consumer...")
        try:
            run_consumer()
        except Exception as e:
            print(f"[STARTUP] ❌ Event consumer error: {e}")
    
    consumer_thread = threading.Thread(target=start_event_consumer, daemon=True)
    consumer_thread.start()
    print("[STARTUP] ✅ Event consumer thread spawned")
    
    # Start Scheduled Collectors (RSS, Price, etc.)
    def start_collectors():
        print("[STARTUP] Starting scheduled collectors...")
        try:
            scheduler = BackgroundScheduler()
            
            # RSS Collector - every 60 seconds
            def run_rss_collector():
                try:
                    run_collector()
                except Exception as e:
                    print(f"[COLLECTORS] RSS error: {e}")
            
            # Price Collector - every 120 seconds
            def run_price_collector():
                try:
                    price_run()
                except Exception as e:
                    print(f"[COLLECTORS] Price error: {e}")
            
            scheduler.add_job(run_rss_collector, 'interval', seconds=60, id='rss_collector')
            scheduler.add_job(run_price_collector, 'interval', seconds=120, id='price_collector')
            scheduler.start()
            print("[STARTUP] ✅ Collectors scheduled (RSS: 60s, Price: 120s)")
        except Exception as e:
            print(f"[STARTUP] ❌ Scheduler error: {e}")
    
    collector_thread = threading.Thread(target=start_collectors, daemon=True)
    collector_thread.start()
    print("[STARTUP] ✅ Collector scheduler spawned")
    
    yield
    
    # Cleanup on shutdown
    print("[SHUTDOWN] Stopping background services...")
    if alert_consumer:
        alert_consumer.stop()


app.lifespan = lifespan
