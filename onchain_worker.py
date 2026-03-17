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
from typing import Optional
import traceback

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("[WORKER]")

# Import the async collector
from app.modules.ingestion.application.onchain_collector import main as onchain_main


class OnChainWorker:
    """Standalone worker for blockchain monitoring with production controls."""
    
    def __init__(self, cycle_interval: int = 180, timeout: int = 120):
        """
        Initialize worker.
        
        Args:
            cycle_interval: Seconds between collector cycles (default 180s/3min)
            timeout: Max seconds per cycle before forced timeout (default 120s)
        """
        self.cycle_interval = cycle_interval
        self.timeout = timeout
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
                await asyncio.wait_for(onchain_main(), timeout=self.timeout)
            except asyncio.TimeoutError:
                logger.error(f"[TIMEOUT] Collector exceeded {self.timeout}s timeout - force killed")
                self.error_count += 1
                return False
            
            elapsed = time.time() - start_time
            logger.info(f"[CYCLE] Completed in {elapsed:.2f}s")
            self.cycle_count += 1
            self.error_count = 0  # Reset on success
            return True
            
        except Exception as e:
            logger.error(f"[ERROR] Collector failed: {type(e).__name__}: {str(e)[:100]}")
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
                        logger.info(f"[WAIT] Retrying in 60s...")
                        await asyncio.sleep(60)
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
    
    def shutdown(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"[SHUTDOWN] Received signal {signum}")
        self.running = False
        
        # Cancel current task if running
        if self.current_task and not self.current_task.done():
            logger.info("[SHUTDOWN] Cancelling current collector task...")
            self.current_task.cancel()
    
    async def start(self):
        """Start the worker with signal handling."""
        # Register signal handlers
        loop = asyncio.get_event_loop()
        
        for sig in [signal.SIGTERM, signal.SIGINT]:
            loop.add_signal_handler(sig, self.shutdown, sig, None)
        
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
        # Create worker (180s interval, 120s timeout per cycle)
        worker = OnChainWorker(
            cycle_interval=int(time.time() % 1 or 180),  # Default 180s between cycles
            timeout=120  # Max 120s per cycle
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
