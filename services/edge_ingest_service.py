"""
Edge Ingest Service - Shared telemetry ingestion logic
Extracted from collector_api.py for reuse by Edge v1 and legacy endpoints
"""

import os
import logging
from datetime import datetime

from api.collector_api import (
    MinerTelemetryLive, MinerTelemetryHistory, CollectorUploadLog,
    find_or_create_hosting_miner, sync_hosting_miner_telemetry
)
from services.telemetry_storage import TelemetryRaw24h
from models import db, MinerBoardTelemetry

logger = logging.getLogger(__name__)


def ingest_miner_records(site_id: int, records: list, received_at: datetime, source: str = 'legacy', edge_meta: dict = None) -> dict:
    """
    Core ingest logic for miner telemetry records.

    Args:
        site_id: The hosting site ID
        records: List of miner record dicts
        received_at: Timestamp when data was received
        source: Source identifier ('legacy', 'v1', etc.)
        edge_meta: Optional dict with device_id, zone_id, sent_at, source_seq_start, source_seq_end

    Returns:
        dict with processed_count, online_count, offline_count, inserted, updated, errors
    """
    if edge_meta is None:
        edge_meta = {}

    scrub_ip = os.environ.get('EDGE_SCRUB_IP', '').lower() == 'true'

    now = received_at
    online_count = 0
    offline_count = 0
    errors = []

    miner_ids = [m.get('miner_id') for m in records if m.get('miner_id')]

    existing_records = MinerTelemetryLive.query.filter(
        MinerTelemetryLive.site_id == site_id,
        MinerTelemetryLive.miner_id.in_(miner_ids)
    ).all() if miner_ids else []
    existing_map = {r.miner_id: r for r in existing_records}

    updates = []
    inserts = []
    history_inserts = []
    raw_24h_inserts = []
    board_telemetry_inserts = []

    for miner_data in records:
        try:
            miner_id = miner_data.get('miner_id')
            if not miner_id:
                continue

            is_online = miner_data.get('online', False)
            if is_online:
                online_count += 1
            else:
                offline_count += 1

            if scrub_ip:
                miner_data['ip_address'] = None

            existing_record = existing_map.get(miner_id)

            record_data = {
                'site_id': site_id,
                'miner_id': miner_id,
                'ip_address': miner_data.get('ip_address'),
                'online': is_online,
                'last_seen': now if is_online else (existing_record.last_seen if existing_record else None),
                'hashrate_ghs': miner_data.get('hashrate_ghs', 0),
                'hashrate_5s_ghs': miner_data.get('hashrate_5s_ghs', 0),
                'hashrate_expected_ghs': miner_data.get('hashrate_expected_ghs', 0),
                'temperature_avg': miner_data.get('temperature_avg', 0),
                'temperature_min': miner_data.get('temperature_min', miner_data.get('temperature_avg', 0)),
                'temperature_max': miner_data.get('temperature_max', 0),
                'temperature_chips': miner_data.get('temperature_chips', []),
                'fan_speeds': miner_data.get('fan_speeds', []),
                'frequency_avg': miner_data.get('frequency_avg', 0),
                'accepted_shares': miner_data.get('accepted_shares', 0),
                'rejected_shares': miner_data.get('rejected_shares', 0),
                'hardware_errors': miner_data.get('hardware_errors', 0),
                'uptime_seconds': miner_data.get('uptime_seconds', 0),
                'power_consumption': miner_data.get('power_consumption', 0),
                'efficiency': miner_data.get('efficiency', 0),
                'pool_url': miner_data.get('pool_url', ''),
                'worker_name': miner_data.get('worker_name', ''),
                'pool_latency_ms': miner_data.get('pool_latency_ms', 0),
                'boards_data': miner_data.get('boards', miner_data.get('boards_data', [])),
                'boards_total': miner_data.get('boards_total', len(miner_data.get('boards', miner_data.get('boards_data', [])))),
                'boards_healthy': miner_data.get('boards_healthy', 0),
                'overall_health': miner_data.get('overall_health', 'offline' if not is_online else 'healthy'),
                'model': miner_data.get('model', ''),
                'firmware_version': miner_data.get('firmware_version', ''),
                'error_message': miner_data.get('error_message', ''),
                'latency_ms': miner_data.get('latency_ms', 0),
                'updated_at': now,
            }

            if existing_record:
                record_data['id'] = existing_record.id
                updates.append(record_data)
            else:
                inserts.append(record_data)

            fan_speeds = miner_data.get('fan_speeds', [])
            fan_speed_avg = sum(fan_speeds) // max(len(fan_speeds), 1) if fan_speeds else 0
            hashrate_ghs = miner_data.get('hashrate_ghs', 0) or 0
            accepted = miner_data.get('accepted_shares', 0) or 0
            rejected = miner_data.get('rejected_shares', 0) or 0
            reject_rate = (rejected / (accepted + rejected) * 100) if (accepted + rejected) > 0 else 0

            raw_24h_inserts.append({
                'ts': now,
                'site_id': site_id,
                'miner_id': miner_id,
                'status': 'online' if is_online else 'offline',
                'hashrate_ths': hashrate_ghs / 1000 if is_online else 0,
                'temperature_c': miner_data.get('temperature_avg', 0) or 0,
                'power_w': miner_data.get('power_consumption', 0) or 0 if is_online else 0,
                'fan_rpm': fan_speed_avg if is_online else 0,
                'reject_rate': reject_rate if is_online else 0,
                'pool_url': (miner_data.get('pool_url', '') or '')[:200] or None,
            })

            if is_online:
                history_inserts.append({
                    'miner_id': miner_id,
                    'site_id': site_id,
                    'timestamp': now,
                    'hashrate_ghs': miner_data.get('hashrate_ghs', 0),
                    'temperature_avg': miner_data.get('temperature_avg', 0),
                    'temperature_min': miner_data.get('temperature_min', miner_data.get('temperature_avg', 0)),
                    'temperature_max': miner_data.get('temperature_max', 0),
                    'fan_speed_avg': fan_speed_avg,
                    'power_consumption': miner_data.get('power_consumption', 0),
                    'accepted_shares': miner_data.get('accepted_shares', 0),
                    'rejected_shares': miner_data.get('rejected_shares', 0),
                    'online': True,
                    'boards_healthy': miner_data.get('boards_healthy', 0),
                    'boards_total': miner_data.get('boards_total', 0),
                    'overall_health': miner_data.get('overall_health', 'healthy'),
                    'net_profit_usd': 0.0,
                    'revenue_usd': 0.0,
                })

            try:
                hosting_miner = find_or_create_hosting_miner(site_id, miner_data)
                sync_hosting_miner_telemetry(hosting_miner, miner_data, now)

                boards = miner_data.get('boards', miner_data.get('boards_data', []))
                if boards and is_online:
                    for board in boards:
                        if isinstance(board, dict):
                            board_telemetry_inserts.append({
                                'miner_id': hosting_miner.id,
                                'site_id': site_id,
                                'board_index': board.get('board_index', board.get('index', 0)),
                                'hashrate_ths': board.get('hashrate_ths', 0),
                                'temperature_c': board.get('temperature_c', 0),
                                'chips_total': board.get('chips_total', 0),
                                'chips_ok': board.get('chips_ok', 0),
                                'chips_failed': board.get('chips_failed', 0),
                                'chip_status': (board.get('chip_status', '') or '')[:200] or None,
                                'frequency_mhz': board.get('frequency_mhz', 0),
                                'voltage_mv': board.get('voltage_mv', 0),
                                'health': board.get('health', 'offline'),
                                'recorded_at': now,
                            })
            except Exception as sync_err:
                logger.warning(f"Failed to sync hosting miner {miner_id}: {sync_err}")

        except Exception as e:
            logger.error(f"Error processing miner {miner_data.get('miner_id')}: {e}")
            errors.append(f"miner {miner_data.get('miner_id')}: {e}")
            continue

    if updates:
        db.session.bulk_update_mappings(MinerTelemetryLive, updates)
    if inserts:
        db.session.bulk_insert_mappings(MinerTelemetryLive, inserts)
    if history_inserts:
        db.session.bulk_insert_mappings(MinerTelemetryHistory, history_inserts)

    if raw_24h_inserts:
        try:
            db.session.bulk_insert_mappings(TelemetryRaw24h, raw_24h_inserts)
        except Exception as raw_err:
            logger.warning(f"Raw telemetry insert failed (non-critical): {raw_err}")

    if board_telemetry_inserts:
        try:
            db.session.bulk_insert_mappings(MinerBoardTelemetry, board_telemetry_inserts)
        except Exception as board_err:
            logger.warning(f"Board telemetry insert failed (non-critical): {board_err}")

    db.session.commit()

    processed_count = online_count + offline_count

    logger.info(f"Ingest [{source}]: site={site_id}, processed={processed_count}, inserted={len(inserts)}, updated={len(updates)}, online={online_count}")

    return {
        'processed_count': processed_count,
        'online_count': online_count,
        'offline_count': offline_count,
        'inserted': len(inserts),
        'updated': len(updates),
        'errors': errors,
    }
