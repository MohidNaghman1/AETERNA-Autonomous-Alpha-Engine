"""
Agent B Polling Consumer - The Profiler (Wallet Profiling via DB Polling)
===========================================================================

Polls ProcessedEvent table for unprocessed events (without agent_b field)
Profiles wallets using Agent B logic
Updates ProcessedEvent.event_data with agent_b profiling data
No RabbitMQ queue dependency - uses PostgreSQL polling
"""

import os
import time
import logging
from datetime import datetime
from sqlalchemy import and_
from app.config.db import SessionLocal
from app.modules.intelligence.application.agent_b import (
    profile_wallet_from_event,
    ProfilerConfig,
)
from app.modules.intelligence.infrastructure.models import ProcessedEvent

logger = logging.getLogger("agent-b-polling")

# Configuration
POLL_INTERVAL = int(os.environ.get("AGENT_B_POLL_INTERVAL", 5))  # Poll every 5 seconds
BATCH_SIZE = int(
    os.environ.get("AGENT_B_BATCH_SIZE", 50)
)  # Process 50 events at a time
PRIORITY_FILTER = os.environ.get("AGENT_B_PRIORITY_FILTER", "HIGH,MEDIUM").split(",")


def needs_agent_b_profiling(event_data: dict) -> bool:
    """Check if event needs Agent B profiling."""
    if not event_data:
        return False
    return "agent_b" not in event_data


def add_agent_b_to_event(processed_event: ProcessedEvent, db) -> bool:
    """
    Add Agent B profiling to a ProcessedEvent.

    Args:
        processed_event: ProcessedEvent ORM instance
        db: Database session

    Returns:
        True if successful, False if failed
    """
    try:
        event_data = processed_event.event_data or {}
        wallet_addr = event_data.get("wallet_address") or event_data.get("address")

        if not wallet_addr:
            logger.debug(f"Event {processed_event.id}: No wallet address - skipping")
            return True  # Skip (no wallet) but don't count as failure

        # Profile the wallet
        config = ProfilerConfig()
        profiling_output = profile_wallet_from_event(
            wallet_address=wallet_addr,
            event_id=str(processed_event.id),
            event_data=event_data,
            db=db,
            config=config,
        )

        # Add profiling data to event_data
        event_data["agent_b"] = profiling_output.model_dump(mode="json")

        # Update database
        processed_event.event_data = event_data
        processed_event.updated_at = datetime.utcnow()
        db.add(processed_event)
        db.commit()

        logger.info(
            f"[AGENT B] ✓ Profiled event {processed_event.id}: "
            f"{profiling_output.profiling_signal} "
            f"(boost={profiling_output.should_boost_priority})"
        )
        return True

    except Exception as e:
        logger.error(f"[AGENT B] ✗ Error profiling event {processed_event.id}: {e}")
        try:
            db.rollback()
        except:
            pass
        return False


def process_batch():
    """
    Process a batch of unprocessed events.

    Returns:
        int: Number of successfully profiled events
    """
    db = SessionLocal()
    try:
        # Find events that need profiling
        # ✅ Only HIGH and MEDIUM priority events
        unprocessed = (
            db.query(ProcessedEvent)
            .filter(ProcessedEvent.priority.in_(PRIORITY_FILTER))
            .limit(BATCH_SIZE)
            .all()
        )

        if not unprocessed:
            return 0

        # Filter to only those needing profiling
        needs_profiling = [
            e for e in unprocessed if needs_agent_b_profiling(e.event_data)
        ]

        if not needs_profiling:
            logger.debug(f"[AGENT B] No events need profiling in this batch")
            return 0

        logger.info(f"[AGENT B] Processing {len(needs_profiling)} events...")

        processed_count = 0
        for event in needs_profiling:
            if add_agent_b_to_event(event, db):
                processed_count += 1

        logger.info(
            f"[AGENT B] ✓ Batch complete: {processed_count}/{len(needs_profiling)} processed"
        )
        return processed_count

    except Exception as e:
        logger.error(f"[AGENT B] ✗ Batch error: {e}", exc_info=True)
        return 0
    finally:
        db.close()


def start_polling():
    """Start the continuous polling loop."""
    logger.info("[AGENT B POLLING] Starting...")
    logger.info(f"  Poll interval: {POLL_INTERVAL}s")
    logger.info(f"  Batch size: {BATCH_SIZE}")
    logger.info(f"  Priority filter: {','.join(PRIORITY_FILTER)}")
    logger.info(
        "[AGENT B POLLING] Polling ProcessedEvent table for unprofile events..."
    )

    stats = {
        "total_processed": 0,
        "batches": 0,
        "errors": 0,
    }

    try:
        while True:
            try:
                count = process_batch()
                if count > 0:
                    stats["total_processed"] += count
                    stats["batches"] += 1

                time.sleep(POLL_INTERVAL)
            except Exception as e:
                logger.error(f"[AGENT B] Error in polling loop: {e}", exc_info=True)
                stats["errors"] += 1
                time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        logger.info("[AGENT B POLLING] Shutting down...")
        logger.info(f"  Total processed: {stats['total_processed']} events")
        logger.info(f"  Total batches: {stats['batches']}")
        logger.info(f"  Errors: {stats['errors']}")
    except Exception as e:
        logger.error(f"[AGENT B POLLING] Fatal error: {e}", exc_info=True)
        raise


if __name__ == "__main__":

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
    )
    logger.info("Starting Agent B Polling Consumer...")
    start_polling()
