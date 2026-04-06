from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import pika
import redis
import os
import asyncio
import traceback
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
from app.modules.admin.presentation.role_management import router as admin_role_router
from app.modules.admin.presentation.bootstrap import router as bootstrap_router
from app.modules.admin.presentation.admin_protected import (
    router as admin_protected_router,
)
from app.modules.ingestion.application.consumer import run_consumer_poll
from app.modules.intelligence.application.consumer import run_intelligence_poll
from app.modules.intelligence.application.agent_b_polling import (
    process_batch as process_agent_b_batch,
)
from app.modules.admin.presentation.security import RateLimitMiddleware
from app.modules.ingestion.application.price_collector import run_collector as price_run
from app.modules.ingestion.application.rss_collector import run_collector

load_dotenv()


# Global scheduler and alert consumer
background_scheduler = None
alert_consumer = None


# Startup and Shutdown Events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager: starts scheduler and alert consumer on startup."""
    global alert_consumer, background_scheduler

    # Start Alert Consumer
    if not alert_consumer:
        alert_consumer = AlertConsumer(sio, user_prefs_func=get_user_prefs)
        alert_consumer.start()
        print("[STARTUP] Alert consumer started")

    # Start Scheduled Collectors
    print("[STARTUP] Starting automatic collectors...")
    try:
        background_scheduler = BackgroundScheduler()

        def run_rss_collector():
            try:
                print(f"[RSS] Running at {time.strftime('%H:%M:%S')}")
                run_collector()
            except Exception as e:
                print(f"[RSS] Error: {e}")

        def run_price_collector():
            try:
                print(f"[PRICE] Running at {time.strftime('%H:%M:%S')}")
                price_run()
            except Exception as e:
                print(f"[PRICE] Error: {e}")

        def run_consumer_polling():
            try:
                # Increased to 5000 to drain massive backlog faster
                count = run_consumer_poll(batch_size=5000)
                if count > 0:
                    print(
                        f"[CONSUMER] ✅ Processed {count} messages (queue draining...)"
                    )
                else:
                    print(f"[CONSUMER] Queue empty or no more messages this cycle")
            except Exception as e:
                print(f"[CONSUMER] Error: {e}")

        def run_intelligence_scoring():

            try:
                count = run_intelligence_poll(batch_size=50)
                if count > 0:
                    print(f"[INTELLIGENCE] Scored {count} events")
            except Exception as e:
                print(f"[INTELLIGENCE] Error: {e}")

        def run_agent_b_profiling():
            try:
                count = process_agent_b_batch()
                if count > 0:
                    print(f"[AGENT B] Profiled {count} wallets")
            except Exception as e:
                print(f"[AGENT B] Error: {e}")

        background_scheduler.add_job(
            run_rss_collector, "interval", seconds=60, id="rss_collector"
        )
        background_scheduler.add_job(
            run_price_collector, "interval", seconds=120, id="price_collector"
        )
        background_scheduler.add_job(
            run_consumer_polling,
            "interval",
            seconds=0.5,
            id="consumer_poller",
            coalesce=True,  # Skip missed executions if previous job still running
            max_instances=1,  # Prevent overlapping executions
        )
        background_scheduler.add_job(
            run_intelligence_scoring, "interval", seconds=5, id="intelligence_scorer"
        )
        background_scheduler.add_job(
            run_agent_b_profiling, "interval", seconds=5, id="agent_b_profiler"
        )
        background_scheduler.start()
        print(
            "[STARTUP] Scheduler started: RSS(60s), Price(120s), Consumer(0.5s, coalesced), Intelligence(50events/5s), AgentB(50wallets/5s)"
        )
        print(
            "[STARTUP] Note: On-chain collector runs as separate worker process (onchain_worker.py)"
        )
    except Exception as e:
        print(f"[STARTUP] Scheduler failed: {e}")

    yield

    # Cleanup on shutdown
    if background_scheduler and background_scheduler.running:
        background_scheduler.shutdown()


app = FastAPI(
    title="AETERNA Autonomous Alpha Engine",
    description="AI-powered cryptocurrency alert and analysis engine with multi-channel delivery",
    version="0.1.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RateLimitMiddleware)

app.include_router(health_router)
app.include_router(bootstrap_router)
app.include_router(auth_router)
app.include_router(ingestion_router, prefix="/ingestion", tags=["ingestion"])
app.include_router(alerts_router)
app.include_router(admin_dashboard_router)
app.include_router(admin_user_router)
app.include_router(admin_role_router)
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
    rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost/")
    try:
        connection = pika.BlockingConnection(pika.URLParameters(rabbitmq_url))
        connection.close()
        diagnostics["rabbitmq"] = "[OK] Connected"
    except Exception as e:
        diagnostics["rabbitmq"] = f"[ERROR] {str(e)}"

    # Check Redis
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        r = redis.from_url(redis_url, decode_responses=True)
        r.ping()
        diagnostics["redis"] = "[OK] Connected"
    except Exception as e:
        diagnostics["redis"] = f"[ERROR] {str(e)}"

    # Check PostgreSQL
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        diagnostics["postgresql"] = "[OK] Connected"
    except Exception as e:
        diagnostics["postgresql"] = f"[ERROR] {str(e)}"

    return diagnostics


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


app.lifespan = lifespan
