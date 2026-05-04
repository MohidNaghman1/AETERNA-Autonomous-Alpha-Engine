from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import pika
import redis
import os
import logging
import traceback
import time
import threading
from dotenv import load_dotenv
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import socketio
from socketio import ASGIApp
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from sqlalchemy import text
from app.shared.utils.auth_utils import decode_token
from app.modules.alerting.infrastructure.alert_consumer import AlertConsumer
from app.modules.identity.infrastructure.models import User, UserPreference
from app.config.db import SessionLocal, sync_engine
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
from app.modules.admin.presentation.security import RateLimitMiddleware

load_dotenv()


def env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


RSS_COLLECTOR_INTERVAL_SECONDS = int(os.getenv("RSS_COLLECTOR_INTERVAL_SECONDS", "60"))
PRICE_COLLECTOR_INTERVAL_SECONDS = int(
    os.getenv("PRICE_COLLECTOR_INTERVAL_SECONDS", "120")
)
SERVICE_TYPE = os.getenv("SERVICE_TYPE", "api").strip().lower()
# Enable background workers by default (RSS, Price, RabbitMQ consumer, Alert consumer)
# Disable via ENABLE_BACKGROUND_TASKS=false if running on platform with separate worker processes
ENABLE_BACKGROUND_TASKS = env_flag(
    "ENABLE_BACKGROUND_TASKS", default=True
)

# Granular toggles so collectors and consumers can be split into dedicated processes.
ENABLE_ALERT_CONSUMER = env_flag("ENABLE_ALERT_CONSUMER", default=True)
ENABLE_EVENT_CONSUMER = env_flag("ENABLE_EVENT_CONSUMER", default=True)
ENABLE_SCHEDULED_COLLECTORS = env_flag("ENABLE_SCHEDULED_COLLECTORS", default=True)

# Global scheduler and alert consumer
background_scheduler = None
alert_consumer = None
consumer_thread = None

# Create Socket.IO instance BEFORE lifespan (so lifespan can use it)
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")


# Startup and Shutdown Events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager: starts scheduler and alert consumer on startup."""
    global alert_consumer, background_scheduler, consumer_thread

    # Helper function to get user preferences (used by alert consumer)
    def get_user_prefs(user_id):
        """Get user preferences from database (SYNC context)."""
        db = None
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
            if db:
                try:
                    db.close()
                except Exception:
                    pass

    logger = logging.getLogger("startup")

    if not ENABLE_BACKGROUND_TASKS:
        logger.info(
            "[STARTUP] SERVICE_TYPE=api: background workers disabled in this process"
        )
        print("[STARTUP] SERVICE_TYPE=api: skipping consumer and collectors")
        yield
        return

    # Import worker modules only when this process is allowed to run them.
    from app.modules.ingestion.application.consumer import run_consumer
    from app.modules.ingestion.application.price_collector import (
        run_collector as price_run,
    )
    from app.modules.ingestion.application.rss_collector import run_collector

    # Start Alert Consumer with detailed error logging
    try:
        if ENABLE_ALERT_CONSUMER and not alert_consumer:
            logger.info("[STARTUP] Starting AlertConsumer...")
            logger.info(
                f"RabbitMQ env: RABBITMQ_URL={os.getenv('RABBITMQ_URL')}, RABBITMQ_HOST={os.getenv('RABBITMQ_HOST')}, RABBITMQ_USER={os.getenv('RABBITMQ_USER')}, RABBITMQ_VHOST={os.getenv('RABBITMQ_VHOST')}"
            )
            alert_consumer = AlertConsumer(sio, user_prefs_func=get_user_prefs)
            alert_consumer.start()
            print("[STARTUP] Alert consumer started")
        elif not ENABLE_ALERT_CONSUMER:
            logger.info("[STARTUP] AlertConsumer disabled by ENABLE_ALERT_CONSUMER=false")
    except Exception as e:
        logger.error(f"[STARTUP] Failed to start AlertConsumer: {e}")
        print(f"[STARTUP] ⚠️ Alert consumer failed to start: {e}")
        # Don't crash the app if alert consumer fails

    # Start RabbitMQ Event Consumer in background thread (blocking consumer is FAST!)
    try:
        if ENABLE_EVENT_CONSUMER and not consumer_thread:

            def blocking_consumer_loop():
                """Run blocking consumer with restart logic on crash."""
                retry_count = 0
                max_initial_retries = 5
                
                while True:
                    try:
                        print(
                            "[CONSUMER-THREAD] Starting blocking RabbitMQ consumer..."
                        )
                        logger.info(
                            f"RabbitMQ env: RABBITMQ_URL={os.getenv('RABBITMQ_URL')}, RABBITMQ_HOST={os.getenv('RABBITMQ_HOST')}, RABBITMQ_USER={os.getenv('RABBITMQ_USER')}, RABBITMQ_VHOST={os.getenv('RABBITMQ_VHOST')}"
                        )
                        run_consumer()  # This blocks forever until error
                        retry_count = 0  # Reset on successful run
                    except Exception as e:
                        retry_count += 1
                        print(
                            f"[CONSUMER-THREAD] ❌ Consumer crashed (attempt {retry_count}): {type(e).__name__}: {str(e)[:100]}"
                        )
                        logger.error(f"[CONSUMER-THREAD] RabbitMQ consumer error: {e}")
                        
                        # Only print full trace on first few retries to avoid spam
                        if retry_count <= 2:
                            traceback.print_exc()
                        
                        # Exponential backoff: 5s, 10s, 20s... up to 60s
                        wait_time = min(5 * (2 ** (retry_count - 1)), 60)
                        print(f"[CONSUMER-THREAD] Retrying in {wait_time}s...")
                        time.sleep(wait_time)

            consumer_thread = threading.Thread(
                target=blocking_consumer_loop, daemon=True
            )
            consumer_thread.start()
            print(
                "[STARTUP] ✅ RabbitMQ blocking consumer started in background thread with auto-restart"
            )
        elif not ENABLE_EVENT_CONSUMER:
            logger.info("[STARTUP] RabbitMQ event consumer disabled by ENABLE_EVENT_CONSUMER=false")
    except Exception as e:
        logger.error(f"[STARTUP] Failed to start RabbitMQ consumer thread: {e}")
        print(f"[STARTUP] ⚠️ Consumer thread failed to initialize, app will continue without it")
        # Don't crash the app if thread creation fails

    # Start Scheduled Collectors
    print("[STARTUP] Starting automatic collectors...")
    try:
        if ENABLE_SCHEDULED_COLLECTORS:
            executors = {
                "default": ThreadPoolExecutor(max_workers=20)  # Allow 20 concurrent jobs
            }
            job_defaults = {
                "coalesce": True,
                "max_instances": 1,
                "misfire_grace_time": 30,
            }
            background_scheduler = BackgroundScheduler(
                executors=executors, job_defaults=job_defaults
            )

            def run_rss_collector():
                try:
                    print(f"[RSS] Running at {time.strftime('%H:%M:%S')}")
                    run_collector()
                except Exception as e:
                    print(f"[RSS] Error: {e}")
                    logger.error(f"[RSS] Collector error: {e}")

            def run_price_collector():
                try:
                    print(f"[PRICE] Running at {time.strftime('%H:%M:%S')}")
                    price_run()
                except Exception as e:
                    print(f"[PRICE] Error: {e}")
                    logger.error(f"[PRICE] Collector error: {e}")

            background_scheduler.add_job(
                run_rss_collector,
                "interval",
                seconds=RSS_COLLECTOR_INTERVAL_SECONDS,
                id="rss_collector",
            )
            background_scheduler.add_job(
                run_price_collector,
                "interval",
                seconds=PRICE_COLLECTOR_INTERVAL_SECONDS,
                id="price_collector",
            )
            background_scheduler.start()
            print(
                "[STARTUP] Scheduler started: "
                f"RSS({RSS_COLLECTOR_INTERVAL_SECONDS}s), "
                f"Price({PRICE_COLLECTOR_INTERVAL_SECONDS}s)"
            )
            print(
                "[STARTUP] ✅ PRIMARY: Using blocking RabbitMQ consumer (run_consumer) in background thread"
            )
            print(
                "[STARTUP] ✅ WALLET PROFILE PERSISTENCE: Enabled via enrich_event_with_agent_b() in consumer"
            )
        else:
            logger.info("[STARTUP] Scheduled collectors disabled by ENABLE_SCHEDULED_COLLECTORS=false")
    except Exception as e:
        logger.error(f"[STARTUP] Scheduler initialization failed: {e}")
        print(f"[STARTUP] ⚠️ Scheduler failed to initialize: {e}")
        traceback.print_exc()
        # Don't crash - API can still run without collectors

    yield

    # Cleanup on shutdown
    if background_scheduler and background_scheduler.running:
        background_scheduler.shutdown()


# Create FastAPI app with lifespan
app = FastAPI(title="AETERNA Autonomous Alpha Engine", lifespan=lifespan)

# Wrap app with Socket.IO
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

try:
    from app.modules.intelligence.presentation.agent_b_debug import (
        router as agent_b_debug_router,
    )

    app.include_router(agent_b_debug_router)
except Exception as e:
    logging.getLogger("startup").exception(
        "[STARTUP] agent_b_debug router failed to load: %s", e
    )


@app.api_route("/", methods=["GET", "HEAD"], operation_id="root_endpoint")
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
        params = pika.URLParameters(rabbitmq_url)
        # pika.BlockingConnection accepts only a single parameters argument.
        # Retry options belong on the connection parameters object itself.
        params.connection_attempts = 2
        params.retry_delay = 1
        connection = pika.BlockingConnection(params)
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
        with sync_engine.connect() as connection:
            connection.execute(text("SELECT 1"))
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
