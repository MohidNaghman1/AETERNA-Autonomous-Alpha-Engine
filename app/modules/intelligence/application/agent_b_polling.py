"""
Agent B Polling Consumer - The Profiler (BACKFILL MODE)
=========================================================

NOTE: This module is now a BACKFILL utility only.
      The PRIMARY path for profile persistence is in consumer.py's enrich_event_with_agent_b()

Purpose:
- Catches events that somehow bypassed the consumer enrichment
- Re-profiles events missing agent_b data (for recovery)
- Useful for backfilling old events before this logic was implemented

Flow for NEW events: consumer.py → enrich_event_with_agent_b() → Profile + DB Persist ✓ (PRIMARY)
Flow for OLD events: agent_b_polling.py → process_batch() → Update Event JSON only (BACKFILL)

The polling approach is kept as a safety net but is no longer the primary ingestion path.
"""

import argparse
import os
import time
import logging
from copy import deepcopy
from datetime import datetime
from sqlalchemy import and_, desc
from sqlalchemy.orm.attributes import flag_modified
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
SCAN_SIZE = int(
    os.environ.get("AGENT_B_SCAN_SIZE", max(BATCH_SIZE * 5, 250))
)  # Scan a wider recent window to avoid starvation
PRIORITY_FILTER = os.environ.get("AGENT_B_PRIORITY_FILTER", "HIGH,MEDIUM").split(",")


def needs_agent_b_profiling(event_data: dict) -> bool:
    """Check if event needs Agent B profiling."""
    if not event_data:
        return False
    return "agent_b" not in event_data


def add_agent_b_to_event(processed_event: ProcessedEvent, db) -> bool:
    """
    Add Agent B profiling to a ProcessedEvent (BACKFILL MODE).

    For on-chain transfers: profiles BOTH from_address and to_address  
    For other events: profiles available wallet address
    For news/price events: marks as processed without profiling

    NOTE: This function only updates the event JSON, not the database.
          Wallet profile persistence happens in consumer.py's enrich_event_with_agent_b()

    Args:
        processed_event: ProcessedEvent ORM instance
        db: Database session

    Returns:
        True if successful, False if failed
    """

    try:
        # Copy JSON payload before mutation so SQLAlchemy can persist the change.
        event_data = deepcopy(processed_event.event_data or {})
        event_source = event_data.get("source", "").lower()  # ethereum, or other
        content = event_data.get("content", {}) if isinstance(event_data.get("content"), dict) else {}

        # Extract all unique wallet addresses
        addresses_to_profile = []
        
        # Top-level addresses (for non-transfer events)
        wallet_addr = event_data.get("wallet_address") or event_data.get("address")
        if wallet_addr:
            addresses_to_profile.append(wallet_addr.lower())

        # On-chain transfer addresses (from_address and to_address for full profiling)
        from_address = content.get("from_address")
        to_address = content.get("to_address")
        
        if from_address and from_address.lower() not in addresses_to_profile:
            addresses_to_profile.append(from_address.lower())
        if to_address and to_address.lower() not in addresses_to_profile:
            addresses_to_profile.append(to_address.lower())

        profiling_results = {}
        
        # Profile all addresses
        if addresses_to_profile:
            config = ProfilerConfig()
            
            for idx, addr in enumerate(addresses_to_profile):
                try:
                    profiling_output = profile_wallet_from_event(
                        wallet_address=addr,
                        event_id=str(processed_event.id),
                        event_data=event_data,
                        db=db,
                        config=config,
                    )
                    
                    profiling_dict = profiling_output.model_dump(mode="json")

                    # Store under specific keys for transfers
                    if len(addresses_to_profile) == 1:
                        # Single address - store as agent_b
                        profiling_results["agent_b"] = profiling_dict
                    elif from_address and from_address.lower() == addr:
                        # Sender address - prioritize this for agent_b
                        profiling_results["agent_b_sender"] = profiling_dict
                        profiling_results["agent_b"] = profiling_dict
                    elif to_address and to_address.lower() == addr:
                        # Receiver address
                        profiling_results["agent_b_receiver"] = profiling_dict
                        # Use as fallback if no sender profiling exists
                        if "agent_b" not in profiling_results:
                            profiling_results["agent_b"] = profiling_dict
                    else:
                        profiling_results[f"agent_b_addr_{idx}"] = profiling_dict

                    logger.info(
                        f"[AGENT B BACKFILL] ✓ Profiled wallet #{idx + 1}/{len(addresses_to_profile)}: {addr[:8]}... "
                        f"({profiling_output.profiling_signal}, boost={profiling_output.should_boost_priority})"
                    )
                except Exception as e:
                    logger.error(f"[AGENT B BACKFILL] Failed to profile wallet {addr}: {e}")
                    continue

            # Merge profiling results
            event_data.update(profiling_results)
            logger.info(
                f"[AGENT B BACKFILL] ✓ Event {processed_event.id}: Profiled {len(profiling_results)} wallet(s)"
            )
        else:
            # Non-wallet event (RSS, Price, etc.) - mark as processed without profiling
            event_data["agent_b"] = {
                "profiling_signal": "N/A - non-wallet event",
                "should_boost_priority": False,
                "wallet_tier": "N/A",
                "confidence_score": 0.0,
            }
            logger.debug(
                f"[AGENT B BACKFILL] Marked event {processed_event.id} (non-wallet source={event_source})"
            )

        # Update database
        processed_event.event_data = event_data
        flag_modified(processed_event, "event_data")
        processed_event.updated_at = datetime.utcnow()
        db.add(processed_event)
        db.flush()
        return True

    except Exception as e:
        logger.error(f"[AGENT B BACKFILL] ✗ Error processing event {processed_event.id}: {e}", exc_info=True)
        try:
            db.rollback()
        except:
            pass
        return False


def process_batch(
    batch_size: int = BATCH_SIZE,
    scan_size: int = SCAN_SIZE,
    priority_filter=None,
):
    """
    Process a batch of unprocessed events (BACKFILL MODE).
    
    This is now a safety net that handles events that somehow didn't get
    enriched by the consumer.py enrich_event_with_agent_b() function.

    Returns:
        int: Number of successfully profiled events
    """
    db = SessionLocal()
    try:
        if priority_filter is None:
            priority_filter = PRIORITY_FILTER

        # Find events that need profiling
        # ✅ Only HIGH and MEDIUM priority events
        candidate_events = (
            db.query(ProcessedEvent)
            .filter(ProcessedEvent.priority.in_(priority_filter))
            .order_by(desc(ProcessedEvent.timestamp))
            .limit(scan_size)
            .all()
        )

        if not candidate_events:
            return 0

        # Filter to only those needing profiling, then process the newest batch.
        needs_profiling = [
            e for e in candidate_events if needs_agent_b_profiling(e.event_data)
        ][:batch_size]

        if not needs_profiling:
            logger.debug(
                f"[AGENT B BACKFILL] No events need profiling in the latest {len(candidate_events)} candidates"
            )
            return 0

        logger.info(f"[AGENT B BACKFILL] Processing {len(needs_profiling)} events...")

        processed_count = 0
        for event in needs_profiling:
            if add_agent_b_to_event(event, db):
                processed_count += 1

        # Commit ONCE after all events processed (not inside the loop)
        try:
            db.commit()
            logger.info(
                f"[AGENT B BACKFILL] ✓ Batch complete: {processed_count}/{len(needs_profiling)} processed"
            )
        except Exception as e:
            db.rollback()
            logger.error(f"[AGENT B BACKFILL] ✗ Batch commit failed: {e}", exc_info=True)
            return 0
        
        return processed_count

    except Exception as e:
        logger.error(f"[AGENT B BACKFILL] ✗ Batch error: {e}", exc_info=True)
        return 0
    finally:
        db.close()


def backfill_missing_agent_b(
    batch_size: int = BATCH_SIZE,
    scan_size: int = SCAN_SIZE,
    max_batches: int | None = None,
    priority_filter=None,
) -> int:
    """Backfill Agent B data for processed events that are still missing it."""
    total_processed = 0
    batches_run = 0

    if priority_filter is None:
        priority_filter = PRIORITY_FILTER

    logger.info("[AGENT B BACKFILL] Starting one-off backfill run...")
    logger.info(f"  Batch size: {batch_size}")
    logger.info(f"  Scan size: {scan_size}")
    logger.info(f"  Priority filter: {','.join(priority_filter)}")
    if max_batches is not None:
        logger.info(f"  Max batches: {max_batches}")

    while True:
        if max_batches is not None and batches_run >= max_batches:
            logger.info("[AGENT B BACKFILL] Reached max batch limit, stopping")
            break

        processed = process_batch(
            batch_size=batch_size,
            scan_size=scan_size,
            priority_filter=priority_filter,
        )
        if processed <= 0:
            break

        total_processed += processed
        batches_run += 1

    logger.info(
        f"[AGENT B BACKFILL] Complete: {total_processed} events enriched across {batches_run} batches"
    )
    return total_processed


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
    parser = argparse.ArgumentParser(description="Agent B polling and backfill runner")
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Run a one-off backfill for processed events missing agent_b",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE,
        help="Maximum events to process per batch",
    )
    parser.add_argument(
        "--scan-size",
        type=int,
        default=SCAN_SIZE,
        help="How many recent candidate events to inspect per batch",
    )
    parser.add_argument(
        "--max-batches",
        type=int,
        default=None,
        help="Optional cap on backfill batches",
    )
    args = parser.parse_args()

    if args.backfill:
        logger.info("Starting Agent B one-off backfill...")
        backfill_missing_agent_b(
            batch_size=args.batch_size,
            scan_size=args.scan_size,
            max_batches=args.max_batches,
        )
    else:
        logger.info("Starting Agent B Polling Consumer...")
        start_polling()
