# -*- coding: utf-8 -*-
"""
kb_routes.py

Flask Blueprint for Miner Knowledge Base API:
- GET /api/kb/version
- POST /api/kb/diagnose
- POST /api/kb/ticket-draft
- GET /api/kb/error-explain
"""
from __future__ import annotations

import logging
from pathlib import Path
from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

kb_bp = Blueprint('kb', __name__, url_prefix='/api/kb')

# Lazy-load KB service to avoid startup delay
_kb_service = None

def get_kb_service():
    """Lazy-load MinerKnowledgeBaseService singleton"""
    global _kb_service
    if _kb_service is None:
        try:
            from services.miner_kb_service import MinerKnowledgeBaseService
            kb_zip = Path(__file__).resolve().parents[1] / "kb" / "miner_kb.zip"
            cache_dir = Path(__file__).resolve().parents[1] / "kb" / "cache"
            _kb_service = MinerKnowledgeBaseService.from_zip(kb_zip, cache_dir)
            logger.info(f"MinerKB loaded: {len(_kb_service.signatures)} signatures, {len(_kb_service.playbooks)} playbooks")
        except Exception as e:
            logger.error(f"Failed to load MinerKB: {e}")
            raise
    return _kb_service


@kb_bp.route('/version', methods=['GET'])
def kb_version():
    """Get KB version and statistics"""
    try:
        kb = get_kb_service()
        return jsonify({
            "success": True,
            "kb_version": kb.schema.get("version"),
            "description": kb.schema.get("description"),
            "signatures": len(kb.signatures),
            "playbooks": len(kb.playbooks),
            "preventions": len(kb.preventions),
            "tunings": len(kb.tunings),
            "brands_with_error_dict": list(kb.error_code_map.keys()),
        })
    except Exception as e:
        logger.error(f"KB version error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@kb_bp.route('/diagnose', methods=['POST'])
def kb_diagnose():
    """
    Diagnose miner issues based on telemetry/logs
    
    Request body:
    {
        "miner_id": "MINER-0001",
        "model_id": "bitmain_antminer_generic",
        "brand": "Bitmain",
        "timestamp": "2026-02-04T12:34:56Z",
        "logs": ["ERROR_POWER_LOST: power voltage read failed"],
        "metrics": {"uptime_sec": 120, "reboot_count_1h": 3}
    }
    """
    try:
        kb = get_kb_service()
        data = request.get_json() or {}
        
        lang = data.get("lang", "zh")
        
        snapshot = {
            "miner_id": data.get("miner_id", "unknown"),
            "model_id": data.get("model_id", "generic_asic_miner"),
            "brand": data.get("brand", "Unknown"),
            "timestamp": data.get("timestamp", ""),
            "logs": data.get("logs", []),
            "metrics": data.get("metrics", {}),
        }
        
        diag = kb.diagnose(snapshot)
        diag = kb.localize_result(diag, lang)
        
        return jsonify({
            "success": True,
            "miner_id": diag.miner_id,
            "model_id": diag.model_id,
            "brand": diag.brand,
            "timestamp": diag.timestamp,
            "confidence": diag.confidence,
            "selected": diag.selected.__dict__ if diag.selected else None,
            "top_hits": [h.__dict__ for h in diag.top_hits],
            "playbook": diag.playbook,
            "prevention": diag.prevention,
            "tuning": diag.tuning,
            "error_code_explanations": diag.error_code_explanations,
            "notes": diag.notes,
        })
    except Exception as e:
        logger.error(f"KB diagnose error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@kb_bp.route('/error-explain', methods=['GET', 'POST'])
def kb_error_explain():
    """
    Explain error code(s)
    
    GET Query params:
    - brand: Bitmain, WhatsMiner, Avalon
    - code: ERROR_POWER_LOST, 206, etc.
    
    POST JSON body:
    - brand: Bitmain, WhatsMiner, Avalon
    - codes: ["ERROR_POWER_LOST", "206", ...]
    """
    try:
        kb = get_kb_service()
        
        if request.method == 'POST':
            # Handle POST with JSON body (multiple codes)
            data = request.get_json() or {}
            brand = data.get("brand", "")
            codes = data.get("codes", [])
            
            if not brand or not codes:
                return jsonify({"success": False, "error": "Missing brand or codes parameter"}), 400
            
            explanations = []
            for code in codes:
                explanation = kb.explain_error_code(brand, code)
                if explanation:
                    explanations.append(explanation)
            
            return jsonify({
                "success": True,
                "brand": brand,
                "explanations": explanations
            })
        else:
            # Handle GET with query params (single code)
            brand = request.args.get("brand", "")
            code = request.args.get("code", "")
            
            if not brand or not code:
                return jsonify({"success": False, "error": "Missing brand or code parameter"}), 400
            
            explanation = kb.explain_error_code(brand, code)
            
            if not explanation:
                return jsonify({"success": False, "error": f"Unknown code: {brand}/{code}"}), 404
            
            return jsonify({
                "success": True,
                "brand": brand,
                "code": code,
                "explanation": explanation
            })
    except Exception as e:
        logger.error(f"KB error-explain error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@kb_bp.route('/ticket-draft', methods=['POST'])
def kb_ticket_draft():
    """
    Generate a ticket draft based on diagnosis
    
    Request body: Same as /diagnose
    """
    try:
        kb = get_kb_service()
        data = request.get_json() or {}
        
        lang = data.get("lang", "zh")
        
        snapshot = {
            "miner_id": data.get("miner_id", "unknown"),
            "model_id": data.get("model_id", "generic_asic_miner"),
            "brand": data.get("brand", "Unknown"),
            "timestamp": data.get("timestamp", ""),
            "logs": data.get("logs", []),
            "metrics": data.get("metrics", {}),
        }
        
        diag = kb.diagnose(snapshot)
        diag = kb.localize_result(diag, lang)
        draft = kb.build_ticket_draft(diag)
        
        return jsonify({
            "success": True,
            **draft
        })
    except Exception as e:
        logger.error(f"KB ticket-draft error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@kb_bp.route('/signatures', methods=['GET'])
def kb_signatures():
    """List all available fault signatures"""
    try:
        kb = get_kb_service()
        return jsonify({
            "success": True,
            "count": len(kb.signatures),
            "signatures": [
                {
                    "signature_id": s.get("signature_id"),
                    "title": s.get("title"),
                    "category": s.get("category"),
                    "severity": s.get("severity"),
                    "priority": s.get("priority"),
                }
                for s in kb.signatures
            ]
        })
    except Exception as e:
        logger.error(f"KB signatures error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@kb_bp.route('/playbooks', methods=['GET'])
def kb_playbooks():
    """List all available playbooks"""
    try:
        kb = get_kb_service()
        return jsonify({
            "success": True,
            "count": len(kb.playbooks),
            "playbooks": [
                {
                    "playbook_id": p.get("playbook_id"),
                    "title": p.get("title"),
                    "goal": p.get("goal"),
                }
                for p in kb.playbooks
            ]
        })
    except Exception as e:
        logger.error(f"KB playbooks error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
