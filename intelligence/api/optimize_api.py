"""
Intelligence Layer - Optimization API
======================================

Flask blueprint for power curtailment optimization endpoints.

Endpoints:
- POST /api/intelligence/optimize/curtailment - Submit curtailment optimization request
- GET /api/intelligence/optimize/<user_id>/<date> - Get optimization schedule
"""

import logging
from datetime import datetime, date as date_type
from flask import Blueprint, request, jsonify
from sqlalchemy.exc import SQLAlchemyError

from db import db
from models import OpsSchedule, UserAccess
from api_auth_middleware import require_api_auth
from intelligence.optimizer import optimize_curtailment, calculate_curtailment_savings
from common.rbac import requires_module_access, Module

logger = logging.getLogger(__name__)

optimize_bp = Blueprint('optimize_api', __name__, url_prefix='/api/intelligence/optimize')


@optimize_bp.route('/curtailment', methods=['POST'])
@require_api_auth(required_permissions=['write'], allow_session_auth=True)
@requires_module_access(Module.CURTAILMENT_AI_PREDICT, require_full=True)
def submit_curtailment_optimization():
    """
    Submit curtailment optimization request
    
    Request Body:
    - user_id: User ID (required)
    - schedule_date: Schedule date in YYYY-MM-DD format (required)
    - electricity_prices: List of 24 hourly prices in $/kWh (required)
    - target_uptime: Target uptime percentage (default: 0.85)
    - min_uptime: Minimum uptime percentage (default: 0.70)
    
    Returns:
        JSON with optimization schedule and savings
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Request body is required'
            }), 400
        
        user_id = data.get('user_id')
        schedule_date_str = data.get('schedule_date')
        electricity_prices = data.get('electricity_prices')
        target_uptime = data.get('target_uptime', 0.85)
        min_uptime = data.get('min_uptime', 0.70)
        
        if not user_id:
            return jsonify({'status': 'error', 'message': 'user_id is required'}), 400
        
        if not schedule_date_str:
            return jsonify({'status': 'error', 'message': 'schedule_date is required'}), 400
        
        if not electricity_prices or len(electricity_prices) != 24:
            return jsonify({
                'status': 'error',
                'message': 'electricity_prices must contain exactly 24 hourly prices'
            }), 400
        
        try:
            schedule_date = datetime.strptime(schedule_date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'status': 'error',
                'message': 'Invalid date format. Use YYYY-MM-DD'
            }), 400
        
        if target_uptime < min_uptime or target_uptime > 1.0 or min_uptime < 0:
            return jsonify({
                'status': 'error',
                'message': 'Invalid uptime parameters. Must have 0 <= min_uptime <= target_uptime <= 1.0'
            }), 400
        
        user = UserAccess.query.get(user_id)
        if not user:
            return jsonify({
                'status': 'error',
                'message': f'User {user_id} not found'
            }), 404
        
        logger.info(f"Starting curtailment optimization for user {user_id}, date {schedule_date}")
        
        result = optimize_curtailment(
            user_id=user_id,
            schedule_date=schedule_date,
            electricity_prices=electricity_prices,
            target_uptime=target_uptime,
            min_uptime=min_uptime
        )
        
        if result['optimization_status'] == 'infeasible':
            return jsonify({
                'status': 'warning',
                'message': 'Optimization infeasible with given constraints. Returning baseline schedule.',
                'result': result
            }), 200
        
        OpsSchedule.query.filter_by(
            user_id=user_id,
            schedule_date=schedule_date
        ).delete()
        
        for hour_data in result['schedule']:
            ops_record = OpsSchedule(
                user_id=user_id,
                schedule_date=schedule_date,
                hour_of_day=hour_data['hour'],
                electricity_price=hour_data['electricity_price'],
                is_peak_hour=(hour_data['electricity_price'] > sum(electricity_prices) / len(electricity_prices)),
                miners_online=hour_data['miners_online'],
                miners_offline=hour_data['miners_offline'],
                total_power_consumption_kw=hour_data['power_kw'],
                optimization_status=result['optimization_status'],
                created_at=datetime.utcnow()
            )
            db.session.add(ops_record)
        
        db.session.commit()
        
        savings = calculate_curtailment_savings(
            schedule=result['schedule'],
            electricity_prices=electricity_prices
        )
        
        logger.info(f"Optimization complete for user {user_id}. Status: {result['optimization_status']}, Savings: ${savings['cost_saved_usd']:.2f}")
        
        return jsonify({
            'status': 'success',
            'user_id': user_id,
            'schedule_date': schedule_date_str,
            'optimization': result,
            'savings': savings,
            'created_at': datetime.utcnow().isoformat()
        }), 201
        
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error in curtailment optimization: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Database error occurred',
            'error': str(e)
        }), 500
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in curtailment optimization: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Internal server error',
            'error': str(e)
        }), 500


@optimize_bp.route('/<int:user_id>/<date_str>', methods=['GET'])
@require_api_auth(required_permissions=['read'], allow_session_auth=True)
@requires_module_access(Module.CURTAILMENT_HISTORY)
def get_optimization_schedule(user_id, date_str):
    """
    Get optimization schedule for a specific date
    
    Path Parameters:
    - user_id: User ID
    - date_str: Date in YYYY-MM-DD format
    
    Returns:
        JSON with hourly optimization schedule
    """
    try:
        try:
            schedule_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'status': 'error',
                'message': 'Invalid date format. Use YYYY-MM-DD'
            }), 400
        
        user = UserAccess.query.get(user_id)
        if not user:
            return jsonify({
                'status': 'error',
                'message': f'User {user_id} not found'
            }), 404
        
        schedules = OpsSchedule.query.filter_by(
            user_id=user_id,
            schedule_date=schedule_date
        ).order_by(OpsSchedule.hour_of_day.asc()).all()
        
        if not schedules:
            return jsonify({
                'status': 'error',
                'message': f'No optimization schedule found for user {user_id} on {date_str}'
            }), 404
        
        schedule_data = []
        total_cost = 0
        total_power = 0
        
        for sched in schedules:
            hourly_cost = float(sched.total_power_consumption_kw) * float(sched.electricity_price)
            schedule_data.append({
                'hour': sched.hour_of_day,
                'electricity_price': float(sched.electricity_price),
                'is_peak_hour': sched.is_peak_hour,
                'miners_online': sched.miners_online,
                'miners_offline': sched.miners_offline,
                'power_kw': float(sched.total_power_consumption_kw),
                'hourly_cost': hourly_cost
            })
            total_cost += hourly_cost
            total_power += float(sched.total_power_consumption_kw)
        
        total_miners = schedules[0].miners_online + schedules[0].miners_offline if schedules else 0
        miners_hours_online = sum(s.miners_online for s in schedules)
        uptime_achieved = miners_hours_online / (total_miners * 24) if total_miners > 0 else 0
        
        logger.info(f"Retrieved optimization schedule for user {user_id}, date {date_str}")
        
        return jsonify({
            'status': 'success',
            'user_id': user_id,
            'schedule_date': date_str,
            'schedule': schedule_data,
            'summary': {
                'total_cost': total_cost,
                'total_power_kwh': total_power,
                'uptime_achieved': uptime_achieved,
                'optimization_status': schedules[0].optimization_status if schedules else None
            },
            'created_at': schedules[0].created_at.isoformat() if schedules and schedules[0].created_at else None
        }), 200
        
    except SQLAlchemyError as e:
        logger.error(f"Database error retrieving schedule for user {user_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Database error occurred',
            'error': str(e)
        }), 500
        
    except Exception as e:
        logger.error(f"Error retrieving schedule for user {user_id}: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Internal server error',
            'error': str(e)
        }), 500
