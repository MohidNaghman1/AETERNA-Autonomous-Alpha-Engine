"""
AETERNA On-Chain Worker
Separate process for blockchain monitoring (DOES NOT block FastAPI)

Architecture:
  FastAPI (web)  ← responsive, handles API requests
  Worker (this)  ← runs blockchain monitoring in separate process
  RabbitMQ       ← event broker between them

Run:
  python onchain_worker.py

Deployment:
  docker-compose.yml:
    - api: FastAPI service
    - worker: separate container running this script
"""

import asyncio
import signal
import sys
import time
import logging
import os
from typing import Optional
import traceback

# Import the async collector
from app.modules.ingestion.application.onchain_collector import main as onchain_main

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("[WORKER]")


class OnChainWorker:
    """Standalone worker for blockchain monitoring with production controls."""

    def __init__(
        self,
        cycle_interval: int = 180,
        timeout: int = 120,
        failure_retry_interval: int = 60,
    ):
        """
        Initialize worker.

        Args:
            cycle_interval: Seconds between collector cycles (default 180s/3min)
            timeout: Max seconds per cycle before forced timeout (default 120s)
            failure_retry_interval: Seconds to wait after failed cycles
        """
        self.cycle_interval = max(1, int(cycle_interval))
        self.timeout = timeout
        self.failure_retry_interval = max(1, int(failure_retry_interval))
        self.running = False
        self.current_task: Optional[asyncio.Task] = None
        self.cycle_count = 0
        self.error_count = 0

    async def run_with_timeout(self):
        """Run collector with timeout protection and error isolation."""
        try:
            logger.info(f"[CYCLE] Starting cycle {self.cycle_count + 1}...")
            start_time = time.time()

            # Run with timeout (kills if takes too long)
            try:
                cycle_ok = await asyncio.wait_for(onchain_main(), timeout=self.timeout)
            except asyncio.TimeoutError:
                logger.error(
                    f"[TIMEOUT] Collector exceeded {self.timeout}s timeout - force killed"
                )
                self.error_count += 1
                return False

            # FIX: use `not cycle_ok` instead of `cycle_ok is False`.
            # onchain_main() returns None (falsy) on Web3/init failure, not
            # the literal False — so `is False` silently treated every failure
            # as a success, reset error_count, and used the long cycle_interval
            # instead of the shorter failure_retry_interval.
            if not cycle_ok:
                elapsed = time.time() - start_time
                logger.error(
                    f"[CYCLE] Collector reported failed run in {elapsed:.2f}s"
                )
                self.error_count += 1
                return False

            elapsed = time.time() - start_time
            logger.info(f"[CYCLE] Completed in {elapsed:.2f}s")
            self.cycle_count += 1
            self.error_count = 0  # Reset on success
            return True

        except Exception as e:
            logger.error(
                f"[ERROR] Collector failed: {type(e).__name__}: {str(e)[:100]}"
            )
            traceback.print_exc()
            self.error_count += 1

            # Fail-fast if too many errors
            if self.error_count >= 5:
                logger.critical("[CRITICAL] 5+ consecutive errors - exiting worker")
                sys.exit(1)

            return False

    async def main_loop(self):
        """Main worker loop with proper state management."""
        self.running = True
        logger.info("=" * 60)
        logger.info("AETERNA On-Chain Worker Started")
        logger.info(f"Cycle interval: {self.cycle_interval}s")
        logger.info(f"Max timeout per cycle: {self.timeout}s")
        logger.info("=" * 60)

        try:
            while self.running:
                try:
                    # Run collector with timeout
                    success = await self.run_with_timeout()

                    if not success:
                        # On error, retry sooner
                        logger.info(
                            f"[WAIT] Retrying in {self.failure_retry_interval}s..."
                        )
                        await asyncio.sleep(self.failure_retry_interval)
                    else:
                        # On success, wait normal interval
                        logger.info(f"[WAIT] Next cycle in {self.cycle_interval}s...")
                        await asyncio.sleep(self.cycle_interval)

                except asyncio.CancelledError:
                    logger.info("[SHUTDOWN] Worker cancelled by signal")
                    break
                except Exception as e:
                    logger.error(f"[ERROR] Unexpected error in main loop: {e}")
                    traceback.print_exc()
                    await asyncio.sleep(60)

        finally:
            self.running = False
            logger.info("[SHUTDOWN] Worker cleanup complete")

    async def _async_shutdown(self, signum: int):
        """Async shutdown handler — safe to call from the event loop."""
        # FIX: The original shutdown() was a sync method with (signum, frame)
        # parameters registered via loop.add_signal_handler(sig, self.shutdown, sig, None).
        # add_signal_handler() only accepts a zero-argument callable, so the extra
        # arguments caused a TypeError and the handler never actually fired.
        # SIGTERM therefore never cleanly cancelled the running task, leaving the
        # collector mid-cycle when Fly.io killed the VM.
        logger.info(f"[SHUTDOWN] Received signal {signum}")
        self.running = False
        if self.current_task and not self.current_task.done():
            logger.info("[SHUTDOWN] Cancelling current collector task...")
            self.current_task.cancel()

    async def start(self):
        """Start the worker with signal handling."""
        # FIX: register a zero-argument lambda that schedules the async shutdown
        # coroutine on the running event loop — the only safe pattern for
        # loop.add_signal_handler() with async cleanup work.
        loop = asyncio.get_event_loop()
        for sig in [signal.SIGTERM, signal.SIGINT]:
            loop.add_signal_handler(
                sig,
                lambda s=sig: asyncio.ensure_future(self._async_shutdown(s)),
            )

        # Run main loop
        try:
            self.current_task = asyncio.create_task(self.main_loop())
            await self.current_task
        except KeyboardInterrupt:
            logger.info("[SHUTDOWN] Keyboard interrupt")
            self.running = False


def main():
    """Entry point for worker."""
    logger.info("Starting AETERNA On-Chain Worker...")

    try:
        cycle_interval = int(os.getenv("ONCHAIN_WORKER_CYCLE_INTERVAL", "180"))
        timeout = int(os.getenv("ONCHAIN_WORKER_TIMEOUT", "120"))
        failure_retry_interval = int(
            os.getenv("ONCHAIN_WORKER_FAILURE_RETRY_INTERVAL", "60")
        )

        # Create worker (180s interval, 120s timeout per cycle)
        worker = OnChainWorker(
            cycle_interval=cycle_interval,
            timeout=timeout,
            failure_retry_interval=failure_retry_interval,
        )

        logger.info(
            f"Worker config: cycle_interval={worker.cycle_interval}s, "
            f"timeout={worker.timeout}s, failure_retry_interval={worker.failure_retry_interval}s"
        )

        # Run worker
        asyncio.run(worker.start())

    except KeyboardInterrupt:
        logger.info("[SHUTDOWN] Worker terminated by user")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"[CRITICAL] Worker crashed: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()