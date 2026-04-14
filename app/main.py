from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import pika
import redis
import os
import asyncio
import traceback
import time
import threading
from dotenv import load_dotenv
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import socketio
from socketio import ASGIApp
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from app.shared.utils.auth_utils import decode_token
from app.modules.alerting.infrastructure.alert_consumer import AlertConsumer
from app.modules.identity.infrastructure.models import User, UserPreference
from app.config.db import AsyncSessionLocal, SessionLocal, sync_engine
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
from app.modules.intelligence.presentation.agent_b_debug import (
    router as agent_b_debug_router,
)
from app.modules.ingestion.application.consumer import run_consumer
from app.modules.intelligence.application.consumer import run_intelligence_poll
from app.modules.intelligence.application.agent_b_polling import (
    process_batch as process_agent_b_batch,
)
from app.modules.admin.presentation.security import RateLimitMiddleware
from app.modules.ingestion.application.price_collector import run_collector as price_run
from app.modules.ingestion.application.rss_collector import run_collector

load_dotenv()

RSS_COLLECTOR_INTERVAL_SECONDS = int(os.getenv("RSS_COLLECTOR_INTERVAL_SECONDS", "60"))
PRICE_COLLECTOR_INTERVAL_SECONDS = int(
    os.getenv("PRICE_COLLECTOR_INTERVAL_SECONDS", "120")
)
INTELLIGENCE_SCORER_INTERVAL_SECONDS = int(
    os.getenv("INTELLIGENCE_SCORER_INTERVAL_SECONDS", "10")
)
AGENT_B_PROFILER_INTERVAL_SECONDS = int(
    os.getenv("AGENT_B_PROFILER_INTERVAL_SECONDS", "10")
)


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

    import logging

    logger = logging.getLogger("startup")

    # Start Alert Consumer with detailed error logging
    try:
        if not alert_consumer:
            logger.info("[STARTUP] Starting AlertConsumer...")
            logger.info(
                f"RabbitMQ env: RABBITMQ_URL={os.getenv('RABBITMQ_URL')}, RABBITMQ_HOST={os.getenv('RABBITMQ_HOST')}, RABBITMQ_USER={os.getenv('RABBITMQ_USER')}, RABBITMQ_VHOST={os.getenv('RABBITMQ_VHOST')}"
            )
            alert_consumer = AlertConsumer(sio, user_prefs_func=get_user_prefs)
            alert_consumer.start()
            print("[STARTUP] Alert consumer started")
    except Exception as e:
        logger.error(f"[STARTUP] Failed to start AlertConsumer: {e}")
        traceback.print_exc()

    # Start RabbitMQ Event Consumer in background thread (blocking consumer is FAST!)
    try:
        if not consumer_thread:

            def blocking_consumer_loop():
                """Run blocking consumer with restart logic on crash."""
                while True:
                    try:
                        print(
                            "[CONSUMER-THREAD] Starting blocking RabbitMQ consumer..."
                        )
                        logger.info(
                            f"RabbitMQ env: RABBITMQ_URL={os.getenv('RABBITMQ_URL')}, RABBITMQ_HOST={os.getenv('RABBITMQ_HOST')}, RABBITMQ_USER={os.getenv('RABBITMQ_USER')}, RABBITMQ_VHOST={os.getenv('RABBITMQ_VHOST')}"
                        )
                        run_consumer()  # This blocks forever until error
                    except Exception as e:
                        print(
                            f"[CONSUMER-THREAD] ❌ Consumer crashed: {type(e).__name__}: {str(e)[:100]}"
                        )
                        logger.error(f"[CONSUMER-THREAD] RabbitMQ consumer error: {e}")
                        traceback.print_exc()
                        print(f"[CONSUMER-THREAD] Restarting in 5 seconds...")
                        time.sleep(5)
                        # Restart consumer on crash

            consumer_thread = threading.Thread(
                target=blocking_consumer_loop, daemon=True
            )
            consumer_thread.start()
            print(
                "[STARTUP] ✅ RabbitMQ blocking consumer started in background thread with auto-restart"
            )
    except Exception as e:
        logger.error(f"[STARTUP] Failed to start RabbitMQ consumer thread: {e}")
        traceback.print_exc()

    # Start Scheduled Collectors
    print("[STARTUP] Starting automatic collectors...")
    try:
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

        def run_price_collector():
            try:
                print(f"[PRICE] Running at {time.strftime('%H:%M:%S')}")
                price_run()
            except Exception as e:
                print(f"[PRICE] Error: {e}")

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
        # NOTE: Event consumer runs in separate thread using blocking consumer (run_consumer)
        # This is MUCH faster than polling and avoids dual-consumer contention
        # The blocking consumer uses prefetch_count=500 for efficient queue draining
        # 
        # DISABLED: Scheduling polling for intelligence_scoring and agent_b_profiling
        # These caused race conditions with the RabbitMQ consumer writing to processed_events
        # The RabbitMQ consumer now handles BOTH scoring and wallet profile DB persistence
        # via enrich_event_with_agent_b() inside process_event()
        #
        # background_scheduler.add_job(
        #     run_intelligence_scoring,
        #     "interval",
        #     seconds=INTELLIGENCE_SCORER_INTERVAL_SECONDS,
        #     id="intelligence_scorer",
        # )
        # background_scheduler.add_job(
        #     run_agent_b_profiling,
        #     "interval",
        #     seconds=AGENT_B_PROFILER_INTERVAL_SECONDS,
        #     id="agent_b_profiler",
        # )
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
    except Exception as e:
        print(f"[STARTUP] Scheduler failed: {e}")

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
app.include_router(agent_b_debug_router)


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
        connection = pika.BlockingConnection(
            pika.URLParameters(rabbitmq_url), connection_attempts=2, retry_delay=1
        )
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
            connection.execute("SELECT 1")
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
